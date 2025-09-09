from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Tuple
import os
import math

from data_fetcher import fetch_data, get_stocks_by_industry
from core.database import get_stock_by_ticker, get_stocks_by_tickers
from services.strategies.strategy_stock import add_indicators
from services.openai_service import completion_client

router = APIRouter()


class StockAnalyzeRequest(BaseModel):
    ticker: str
    # Optional tuning params (buyer-side)
    lookback_days: int | None = 20  # recent window for support/resistance
    entry_frac: float | None = 0.4  # entry_high = support + range * entry_frac
    target_frac: float | None = 0.1  # target = resistance - range * target_frac
    stop_atr_mult: float | None = 1.0  # stop below support by ATR * mult
    stop_floor_pct: float | None = 5.0  # fallback floor: 5% below current price
    # Sizing
    account_size: float | None = None  # total capital
    risk_pct: float | None = None      # risk per trade (%) of account size


class StockAnalyzeByIndustryRequest(BaseModel):
    industry: str
    limit: int | None = None
    lookback_days: int | None = 20
    entry_frac: float | None = 0.4
    target_frac: float | None = 0.1
    stop_atr_mult: float | None = 1.0
    stop_floor_pct: float | None = 5.0
    account_size: float | None = None
    risk_pct: float | None = None


def _to_float(x: Any) -> Optional[float]:
    """Best-effort float conversion with NaN/inf guarding."""
    try:
        if x is None:
            return None
        v = float(x)
        if not math.isfinite(v):
            return None
        return v
    except Exception:
        return None


def _fetch_df(ticker: str):
    data_map = fetch_data([ticker], period="1y", interval="1d")
    df = data_map.get(ticker)
    if df is None or df.empty or "Close" not in df.columns:
        raise HTTPException(status_code=404, detail="No data available")
    return add_indicators(df)


def _compute_metrics(df) -> Dict[str, Any]:
    last = df.iloc[-1]
    close = _to_float(last.get("Close"))
    atr = _to_float(last.get("ATR"))
    atr_pct = (atr / close) if (atr and close) else None

    # Determine trend using stock-analysis MAs first (MA20/MA50/MA200), fallback to MA5/20/60
    ma20 = _to_float(last.get("MA20")) if "MA20" in df.columns else None
    ma50 = _to_float(last.get("MA50")) if "MA50" in df.columns else None
    ma200 = _to_float(last.get("MA200")) if "MA200" in df.columns else None
    ma5 = _to_float(last.get("MA5")) if "MA5" in df.columns else None
    ma60 = _to_float(last.get("MA60")) if "MA60" in df.columns else None
    trend_state = None
    if all(v is not None for v in [ma20, ma50, ma200]):
        if ma20 > ma50 > ma200:
            trend_state = "多頭排列"
        elif ma20 < ma50 < ma200:
            trend_state = "空頭排列"
        else:
            trend_state = "盤整/糾結"
    elif all(v is not None for v in [ma5, ma20, ma60]):
        if ma5 > ma20 > ma60:
            trend_state = "多頭排列"
        elif ma5 < ma20 < ma60:
            trend_state = "空頭排列"
        else:
            trend_state = "盤整/糾結"

    lookback = df["Close"].tail(min(len(df), 252))
    hi_52w = _to_float(lookback.max()) if len(lookback) else None
    lo_52w = _to_float(lookback.min()) if len(lookback) else None
    from_high = ((hi_52w - close) / hi_52w) if (hi_52w and close) else None
    from_low = ((close - lo_52w) / lo_52w) if (lo_52w and close) else None

    def _ret(n: int) -> Optional[float]:
        if len(df) > n:
            prev = _to_float(df["Close"].iloc[-(n + 1)])
            if prev and prev > 0 and close:
                return (close / prev) - 1.0
        return None

    r_1m = _ret(21)
    r_3m = _ret(63)
    r_6m = _ret(126)

    return {
        "price": close,
        "atr_pct": (atr_pct * 100) if atr_pct is not None else None,
        "trend": trend_state,
        "from_52w_high_pct": (from_high * 100) if from_high is not None else None,
        "from_52w_low_pct": (from_low * 100) if from_low is not None else None,
        "ret_1m_pct": (r_1m * 100) if r_1m is not None else None,
        "ret_3m_pct": (r_3m * 100) if r_3m is not None else None,
        "ret_6m_pct": (r_6m * 100) if r_6m is not None else None,
    }


def _build_spark(df) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    spark: List[Dict[str, Any]] = []
    spark_stats: Dict[str, Any] = {}

    tail = df.tail(min(30, len(df))).copy()
    if tail.empty:
        return spark, spark_stats

    s0 = _to_float(tail["Close"].iloc[0])
    has_bb = all(k in tail.columns for k in ("BB_UPPER", "BB_LOWER", "BB_MID"))

    tail["_MA20"] = tail["Close"].rolling(window=20, min_periods=1).mean()
    running_max = tail["Close"].cummax()
    tail["_DRAWDOWN_PCT"] = ((tail["Close"] - running_max) / running_max) * 100.0

    for idx, row in tail.iterrows():
        c = _to_float(row.get("Close"))
        if c is None:
            continue
        pct = ((c - s0) / s0 * 100.0) if (s0 and s0 != 0) else None
        entry = {
            "date": idx.strftime("%Y-%m-%d"),
            "close": c,
            "pct": pct,
            "ma20": _to_float(row.get("_MA20")),
            "dd_pct": _to_float(row.get("_DRAWDOWN_PCT")),
        }
        if has_bb:
            entry.update({
                "bb_upper": _to_float(row.get("BB_UPPER")),
                "bb_lower": _to_float(row.get("BB_LOWER")),
                "bb_mid": _to_float(row.get("BB_MID")),
            })
        spark.append(entry)

    # stats
    closes = [s["close"] for s in spark if s.get("close") is not None]
    pcts = [s.get("pct") for s in spark if s.get("pct") is not None]
    if closes:
        spark_stats["range_min"] = min(closes)
        spark_stats["range_max"] = max(closes)
    if pcts:
        spark_stats["change_pct"] = pcts[-1]
        # linear trend slope via least squares (pct per day)
        try:
            import numpy as _np
            y = _np.array(pcts, dtype=float)
            x = _np.arange(len(y), dtype=float)
            A = _np.vstack([x, _np.ones(len(x))]).T
            slope, _ = _np.linalg.lstsq(A, y, rcond=None)[0]
            spark_stats["trend_slope_pct_per_day"] = float(slope)
        except Exception:
            pass

    return spark, spark_stats


def _build_suggestion(df, metrics: Dict[str, Any], req: StockAnalyzeRequest) -> Optional[Dict[str, Any]]:
    try:
        close = metrics.get("price")
        atr_pct = metrics.get("atr_pct")
        trend_state = metrics.get("trend")

        lb = req.lookback_days or 20
        recent = df.tail(min(lb, len(df)))
        support = _to_float(recent["Low"].min()) if not recent.empty else None
        resistance = _to_float(recent["High"].max()) if not recent.empty else None

        entry_low = support
        entry_high = None
        target = None
        stop = None
        rr = None
        if support is not None and resistance is not None and close:
            rng = resistance - support
            if rng > 0:
                ef = req.entry_frac if req.entry_frac is not None else 0.4
                tf = req.target_frac if req.target_frac is not None else 0.1
                saf = req.stop_atr_mult if req.stop_atr_mult is not None else 1.0
                sfp = req.stop_floor_pct if req.stop_floor_pct is not None else 5.0
                entry_high = support + rng * max(0.0, min(1.0, ef))
                target = resistance - rng * max(0.0, min(1.0, tf))
                atr = None
                try:
                    # recover ATR from atr_pct if possible
                    atr = (atr_pct / 100.0) * close if atr_pct is not None else None
                except Exception:
                    atr = None
                stop_atr = (atr or 0.0) * max(0.0, saf)
                stop_floor = close * (1.0 - max(0.0, sfp) / 100.0)
                stop = max(support - stop_atr, stop_floor)
                potential_gain = (target - entry_high) if (target and entry_high) else None
                potential_loss = (entry_high - stop) if (entry_high and stop) else None
                if potential_gain is not None and potential_loss and potential_loss > 0:
                    rr = float(potential_gain / potential_loss)

        # Short summary rationale using simple signals
        spark, spark_stats = _build_spark(df)
        slope = spark_stats.get("trend_slope_pct_per_day")
        chg = spark_stats.get("change_pct")

        decision = "觀望"
        rationale: List[str] = []
        if trend_state == "多頭排列":
            rationale.append("趨勢偏多")
        elif trend_state == "空頭排列":
            rationale.append("趨勢偏空")
        if slope is not None:
            rationale.append(f"短期斜率 {slope:.2f}%/日")
        if chg is not None:
            rationale.append(f"區間變化 {chg:.2f}%")

        from_high_pct = metrics.get("from_52w_high_pct")
        if trend_state == "空頭排列" or (slope is not None and slope < -0.05):
            decision = "回避"
        elif (
            trend_state == "多頭排列" and
            (slope is None or slope >= 0) and
            (from_high_pct is None or from_high_pct <= 15.0) and
            (rr is None or rr >= 1.5)
        ):
            decision = "買進"
        else:
            decision = "觀望"

        position = None
        try:
            if req.account_size and req.risk_pct and entry_high and stop:
                entry_px = float(entry_high)
                per_share_risk = entry_px - float(stop)
                # Also ensure ATR-based minimal risk (if available)
                atr_abs = (atr_pct / 100.0) * close if (atr_pct is not None and close) else None
                if atr_abs and req.stop_atr_mult and (atr_abs * req.stop_atr_mult) > per_share_risk:
                    per_share_risk = float(atr_abs * req.stop_atr_mult)
                if per_share_risk > 0:
                    risk_amount = float(req.account_size) * (float(req.risk_pct) / 100.0)
                    shares = int(max(0, math.floor(risk_amount / per_share_risk)))
                    position = {
                        "shares": shares,
                        "entry_price": entry_px,
                        "capital_used": shares * entry_px,
                        "per_share_risk": per_share_risk,
                        "risk_amount": risk_amount,
                    }
        except Exception:
            position = None

        # Simple human-readable advice
        simple_advice = None
        try:
            ma20_last = _to_float(df["Close"].rolling(window=20, min_periods=1).mean().iloc[-1])
            entry_str = (f"{entry_low:.2f} ~ {entry_high:.2f}" if (entry_low is not None and entry_high is not None) else None)
            buy_when: List[str] = []
            sell_when: List[str] = []
            if entry_str:
                buy_when.append(f"靠近買進區間（{entry_str}）時分批進場，不追高")
            if ma20_last:
                buy_when.append("回測月線（MA20）後站回，可考慮少量佈局")
            if target:
                sell_when.append(f"靠近目標價（{target:.2f}）時分批了結")
            if stop:
                sell_when.append(f"跌破停損（{stop:.2f}）立刻出場")
            if ma20_last:
                sell_when.append("連續兩天收在月線下方，適度減碼")
            simple_advice = {
                "entry_range": entry_str,
                "buy_when": buy_when,
                "sell_when": sell_when,
                "tip": "量縮回檔不急，量增突破再加碼；控制單筆風險於資金的 1%~2%。",
            }
        except Exception:
            simple_advice = None

        suggestion = {
            "decision": decision,
            "entry_low": entry_low,
            "entry_high": entry_high,
            "target": target,
            "stop": stop,
            "risk_reward": rr,
            "position": position,
            "rationale": ", ".join(rationale),
            "simple": simple_advice,
        }

        # also return spark data computed above without recomputing
        suggestion["_spark"] = spark
        suggestion["_spark_stats"] = spark_stats
        return suggestion
    except Exception:
        return None


def _build_ai_summary(ticker: str, metrics: Dict[str, Any], suggestion: Optional[Dict[str, Any]]) -> Optional[str]:
    try:
        if not completion_client:
            return None
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-instruct")
        # round floats and remove non-finite
        ctx: Dict[str, Any] = {}
        for k, v in metrics.items():
            if isinstance(v, float):
                if math.isfinite(v):
                    ctx[k] = round(v, 2)
                else:
                    ctx[k] = None
            else:
                ctx[k] = v

        sys_prompt = (
            "你是專業投資分析師。僅依據提供的指標做文字解讀，"
            "禁止自行計算新數據或提供保證。請用買方視角輸出 2 句繁體中文："
            "第 1 句請優先輸出『核心操作建議』（買點/賣點/風控，簡潔）；第 2 句補充觀察重點。"
        )

        ops_text = None
        try:
            if suggestion:
                e_low = suggestion.get("entry_low")
                e_high = suggestion.get("entry_high")
                t = suggestion.get("target")
                s = suggestion.get("stop")
                entry_range_str = (f"{e_low:.2f}~{e_high:.2f}" if (e_low is not None and e_high is not None) else "—")
                target_str = (f"{t:.2f}" if t is not None else "—")
                stop_str = (f"{s:.2f}" if s is not None else "—")
                simple = suggestion.get("simple") or {}
                buy_when = simple.get("buy_when") or []
                sell_when = simple.get("sell_when") or []
                top_buy = buy_when[0] if buy_when else ""
                top_sell = sell_when[0] if sell_when else ""
                ops_text = (
                    f"買點：{entry_range_str}；賣點：{target_str}／停損：{stop_str}。"
                    f"{top_buy} {top_sell} 風控：單筆風險 1%~2%。"
                ).strip()
        except Exception:
            ops_text = None

        user_prompt = (
            f"股票 {ticker} 指標：\n"
            f"現價: {ctx['price']}\n"
            f"ATR%: {ctx['atr_pct']}\n"
            f"趨勢: {ctx['trend']}\n"
            f"距52週高%: {ctx['from_52w_high_pct']}；距52週低%: {ctx['from_52w_low_pct']}\n"
            f"報酬%: 1m {ctx['ret_1m_pct']}｜3m {ctx['ret_3m_pct']}｜6m {ctx['ret_6m_pct']}\n"
            + (f"建議（機械計算）: {suggestion}\n" if suggestion else "")
            + (f"核心操作建議（請先輸出）：{ops_text}\n" if ops_text else "")
        )

        prompt = sys_prompt + "\n\n" + user_prompt
        resp = completion_client(prompt=prompt, model=model, temperature=0.2, max_tokens=280)
        try:
            ai_text = resp.choices[0].text
        except Exception:
            ai_text = resp["choices"][0]["text"]
        return str(ai_text).strip() if ai_text else None
    except Exception:
        return None


@router.post("/stock/analyze")
def analyze_stock(req: StockAnalyzeRequest):
    try:
        ticker = req.ticker.strip().upper()
        df = _fetch_df(ticker)

        metrics = _compute_metrics(df)
        suggestion = _build_suggestion(df, metrics, req)

        # Reuse spark computed in suggestion to avoid recompute
        spark: List[Dict[str, Any]] = []
        spark_stats: Dict[str, Any] = {}
        if suggestion and suggestion.get("_spark") is not None:
            spark = suggestion.pop("_spark", [])  # remove internal fields
            spark_stats = suggestion.pop("_spark_stats", {})
        else:
            spark, spark_stats = _build_spark(df)

        ai_text = _build_ai_summary(ticker, metrics, suggestion)

        return {
            "type": "stock_analysis",
            "ticker": ticker,
            "name": (get_stock_by_ticker(ticker) or {}).get("name"),
            "metrics": metrics,
            "spark": spark,
            "spark_stats": spark_stats,
            "suggestion": suggestion,
            "ai_summary": ai_text,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stock/analyze_by_industry")
def analyze_by_industry(req: StockAnalyzeByIndustryRequest):
    try:
        ind = req.industry.strip()
        if not ind:
            raise HTTPException(status_code=400, detail="industry required")
        tickers = get_stocks_by_industry(ind)
        if not tickers:
            return {"type": "stock_analysis_by_industry", "industry": ind, "items": []}
        if req.limit and req.limit > 0:
            tickers = tickers[: int(req.limit)]

        # Build a light-weight analysis per ticker (no AI by default)
        items: List[Dict[str, Any]] = []
        base_req = StockAnalyzeRequest(
            ticker="DUMMY",
            lookback_days=req.lookback_days,
            entry_frac=req.entry_frac,
            target_frac=req.target_frac,
            stop_atr_mult=req.stop_atr_mult,
            stop_floor_pct=req.stop_floor_pct,
            account_size=req.account_size,
            risk_pct=req.risk_pct,
        )
        # Fetch names for all tickers in one query
        try:
            meta = get_stocks_by_tickers(tickers)
            name_map = {m["ticker"]: m["name"] for m in meta}
        except Exception:
            name_map = {}

        for t in tickers:
            try:
                df = _fetch_df(t)
                metrics = _compute_metrics(df)
                # reuse suggestion builder with buyer params
                base_req.ticker = t
                suggestion = _build_suggestion(df, metrics, base_req)
                items.append({
                    "ticker": t,
                    "name": name_map.get(t),
                    "metrics": metrics,
                    "suggestion": suggestion,
                })
            except Exception as _:
                continue

        # Optional sort: by risk_reward desc if available
        def _rr(x):
            try:
                rr = x.get("suggestion", {}).get("risk_reward")
                return rr if isinstance(rr, (int, float)) else -1
            except Exception:
                return -1
        items.sort(key=_rr, reverse=True)

        return {
            "type": "stock_analysis_by_industry",
            "industry": ind,
            "count": len(items),
            "items": items,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
