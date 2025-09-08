from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
import os
import numpy as np

from data_fetcher import fetch_data
from services.strategies.strategy_stock import add_indicators
from services.openai_service import completion_client

router = APIRouter()


class StockAnalyzeRequest(BaseModel):
    ticker: str


def _to_float(x: Any) -> float | None:
    try:
        if x is None or (hasattr(x, "__float__") is False):
            x = float(x)
        return float(x)
    except Exception:
        try:
            import pandas as pd  # lazy
            if pd.isna(x):
                return None
        except Exception:
            pass
        return None


@router.post("/stock/analyze")
def analyze_stock(req: StockAnalyzeRequest):
    try:
        ticker = req.ticker.strip().upper()
        data_map = fetch_data([ticker], period="1y", interval="1d")
        df = data_map.get(ticker)
        if df is None or df.empty or "Close" not in df.columns:
            raise HTTPException(status_code=404, detail="No data available")

        df = add_indicators(df)
        last = df.iloc[-1]

        close = _to_float(last.get("Close"))
        atr = _to_float(last.get("ATR"))
        atr_pct = (atr / close) if (atr and close) else None

        ma5 = _to_float(last.get("MA5"))
        ma20 = _to_float(last.get("MA20"))
        ma60 = _to_float(last.get("MA60"))
        trend_state = None
        if all(v is not None for v in [ma5, ma20, ma60]):
            if ma5 > ma20 > ma60:
                trend_state = "多頭排列"
            elif ma5 < ma20 < ma60:
                trend_state = "空頭排列"
            else:
                trend_state = "盤整/糾結"

        # 52週高/低（以資料長度近似）
        lookback = df["Close"].tail(min(len(df), 252))
        hi_52w = _to_float(lookback.max()) if len(lookback) else None
        lo_52w = _to_float(lookback.min()) if len(lookback) else None
        from_high = ((hi_52w - close) / hi_52w) if (hi_52w and close) else None
        from_low = ((close - lo_52w) / lo_52w) if (lo_52w and close) else None

        # 報酬：1m(~21d)/3m(~63d)/6m(~126d)
        def ret(n):
            if len(df) > n:
                prev = _to_float(df["Close"].iloc[-(n + 1)])
                if prev and prev > 0 and close:
                    return (close / prev) - 1.0
            return None

        r_1m = ret(21)
        r_3m = ret(63)
        r_6m = ret(126)

        # 小圖資料（近 30 日）+ 加值資訊：%變化、MA20、布林通道、回撤
        spark = []
        tail = df.tail(min(30, len(df))).copy()
        try:
            # 基準為第一天收盤
            s0 = float(tail["Close"].iloc[0]) if len(tail) else None
            # 近 30 日的布林通道已有（若前面 add_indicators 有 BBANDS）
            # 若沒有，避免 KeyError
            has_bb = all(k in tail.columns for k in ["BB_UPPER", "BB_LOWER", "BB_MID"]) if len(tail.columns) else False

            # 計算 20 日均線在子視窗的值（不足期會是 NaN）
            tail["_MA20"] = tail["Close"].rolling(window=20, min_periods=1).mean()
            # 計算子視窗回撤（相對該視窗內前高）
            running_max = tail["Close"].cummax()
            tail["_DRAWDOWN_PCT"] = ((tail["Close"] - running_max) / running_max) * 100.0

            # 轉成前端可用的 spark 序列
            for idx, row in tail.iterrows():
                try:
                    c = float(row["Close"])
                    pct = ((c - s0) / s0 * 100.0) if (s0 and s0 != 0) else None
                    entry = {
                        "date": idx.strftime("%Y-%m-%d"),
                        "close": c,
                        "pct": pct,
                        "ma20": float(row["_MA20"]) if row.get("_MA20") == row.get("_MA20") else None,  # not NaN
                        "dd_pct": float(row["_DRAWDOWN_PCT"]) if row.get("_DRAWDOWN_PCT") == row.get("_DRAWDOWN_PCT") else None,
                    }
                    if has_bb:
                        entry.update({
                            "bb_upper": _to_float(row.get("BB_UPPER")),
                            "bb_lower": _to_float(row.get("BB_LOWER")),
                            "bb_mid": _to_float(row.get("BB_MID")),
                        })
                    spark.append(entry)
                except Exception:
                    continue
        except Exception:
            # 儘量容錯，至少提供基本 close 資料
            spark = []
            for idx, val in tail["Close"].items():
                try:
                    spark.append({
                        "date": idx.strftime("%Y-%m-%d"),
                        "close": float(val)
                    })
                except Exception:
                    pass

        # Spark 綜合統計：區間變化、範圍、極值與簡單趨勢斜率（%/天）
        spark_stats: Dict[str, Any] = {}
        try:
            if spark:
                closes = [s.get("close") for s in spark if s.get("close") is not None]
                pcts = [s.get("pct") for s in spark if s.get("pct") is not None]
                if closes:
                    cmin, cmax = min(closes), max(closes)
                    spark_stats["range_min"] = cmin
                    spark_stats["range_max"] = cmax
                if pcts:
                    spark_stats["change_pct"] = pcts[-1]
                    # 線性趨勢（最小平方法擬合）以 % 為單位/天
                    try:
                        import numpy as _np
                        y = _np.array(pcts, dtype=float)
                        x = _np.arange(len(y), dtype=float)
                        A = _np.vstack([x, _np.ones(len(x))]).T
                        slope, _ = _np.linalg.lstsq(A, y, rcond=None)[0]
                        spark_stats["trend_slope_pct_per_day"] = float(slope)
                    except Exception:
                        pass
        except Exception:
            pass

        metrics = {
            "price": close,
            "atr_pct": (atr_pct * 100) if atr_pct is not None else None,
            "trend": trend_state,
            "from_52w_high_pct": (from_high * 100) if from_high is not None else None,
            "from_52w_low_pct": (from_low * 100) if from_low is not None else None,
            "ret_1m_pct": (r_1m * 100) if r_1m is not None else None,
            "ret_3m_pct": (r_3m * 100) if r_3m is not None else None,
            "ret_6m_pct": (r_6m * 100) if r_6m is not None else None,
        }

        # AI 總結（可選）
        ai_text = None
        try:
            if completion_client:
                model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-instruct")
                ctx = {k: (None if (v is None or (isinstance(v, float) and not np.isfinite(v))) else (round(v, 2) if isinstance(v, float) else v)) for k, v in metrics.items()}
                sys_prompt = (
                    "你是專業投資分析師。僅依據提供的指標做文字解讀，"
                    "禁止自行計算新數據或給出保證。請輸出 2 句繁體中文：1) 走勢與風險概況 2) 操作建議/留意事項。"
                )
                user_prompt = (
                    f"股票 {ticker} 指標：\n"
                    f"現價: {ctx['price']}\n"
                    f"ATR%: {ctx['atr_pct']}\n"
                    f"趨勢: {ctx['trend']}\n"
                    f"距52週高%: {ctx['from_52w_high_pct']}；距52週低%: {ctx['from_52w_low_pct']}\n"
                    f"報酬%: 1m {ctx['ret_1m_pct']}｜3m {ctx['ret_3m_pct']}｜6m {ctx['ret_6m_pct']}\n"
                )
                prompt = sys_prompt + "\n\n" + user_prompt
                resp = completion_client(prompt=prompt, model=model, temperature=0.2, max_tokens=280)
                try:
                    ai_text = resp.choices[0].text
                except Exception:
                    ai_text = resp["choices"][0]["text"]
                if ai_text:
                    ai_text = str(ai_text).strip()
        except Exception:
            ai_text = None

        return {
            "type": "stock_analysis",
            "ticker": ticker,
            "metrics": metrics,
            "spark": spark,
            "spark_stats": spark_stats,
            "ai_summary": ai_text,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
