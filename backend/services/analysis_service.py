import pandas as pd
from typing import Any, Dict
import json
import os

from data_fetcher import fetch_data
from services.strategies.strategy_stock import add_indicators
from .openai_service import completion_client

def _to_float(x: Any) -> float | None:
    try:
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None

def compute_quant_insights(ticker: str) -> Dict[str, Any]:
    """基於技術指標產生結構化洞察，不依賴 AI。

    包含趨勢、動能、波動、量能、支撐/壓力與近/中期表現。
    """
    try:
        df_map = fetch_data([ticker], period="6mo", interval="1d")
        df = df_map.get(ticker)
        if df is None or df.empty:
            return {"error": "no_data"}
        df = add_indicators(df)
        last = df.iloc[-1]

        close = _to_float(last.get("Close"))
        # Gather available MAs (supports both short-term and long-term sets)
        ma5 = _to_float(last.get("MA5")) if "MA5" in df.columns else None
        ma20 = _to_float(last.get("MA20")) if "MA20" in df.columns else None
        ma50 = _to_float(last.get("MA50")) if "MA50" in df.columns else None
        ma60 = _to_float(last.get("MA60")) if "MA60" in df.columns else None
        ma200 = _to_float(last.get("MA200")) if "MA200" in df.columns else None
        rsi = _to_float(last.get("RSI"))
        atr = _to_float(last.get("ATR"))
        macd = _to_float(last.get("MACD"))
        macd_signal = _to_float(last.get("MACD_SIGNAL"))
        macd_hist = _to_float(last.get("MACD_HIST"))
        vol = _to_float(last.get("Volume"))
        avg20 = _to_float(df["Volume"].tail(20).mean()) if len(df) >= 20 else None

        # 趨勢（均線排列）：優先使用 MA20/MA50/MA200，否則退回 MA5/MA20/MA60
        trend = None
        if all(v is not None for v in [ma20, ma50, ma200]):
            if ma20 > ma50 > ma200:
                trend = "多頭排列"
            elif ma20 < ma50 < ma200:
                trend = "空頭排列"
            else:
                trend = "盤整/糾結"
        elif all(v is not None for v in [ma5, ma20, ma60]):
            if ma5 > ma20 > ma60:
                trend = "多頭排列"
            elif ma5 < ma20 < ma60:
                trend = "空頭排列"
            else:
                trend = "盤整/糾結"

        # RSI 區間
        rsi_state = None
        if rsi is not None:
            if rsi >= 70:
                rsi_state = "超買"
            elif rsi <= 30:
                rsi_state = "超賣"
            elif 45 <= rsi <= 55:
                rsi_state = "平衡"
            else:
                rsi_state = "中性"

        # MACD 動能
        macd_state = None
        if macd is not None and macd_signal is not None:
            macd_state = "黃金交叉" if macd > macd_signal else "死亡交叉"

        # 波動率（ATR%）
        atr_pct = None
        vol_label = None
        if close and atr:
            atr_pct = atr / close
            if atr_pct >= 0.03:
                vol_label = "高波動"
            elif atr_pct >= 0.01:
                vol_label = "中等波動"
            else:
                vol_label = "低波動"

        # 量能（對比 20 日均量）
        vol_ratio = None
        vol_state = None
        if vol and avg20 and avg20 > 0:
            vol_ratio = vol / avg20
            if vol_ratio >= 1.5:
                vol_state = "放量"
            elif vol_ratio <= 0.7:
                vol_state = "量縮"
            else:
                vol_state = "正常"

        # 支撐/壓力（近 20 日）
        recent = df.tail(min(20, len(df)))
        support = _to_float(recent["Low"].min()) if not recent.empty else None
        resistance = _to_float(recent["High"].max()) if not recent.empty else None
        dist_s = None
        dist_r = None
        if close and support and resistance and resistance > support:
            dist_s = (close - support) / support if support > 0 else None
            dist_r = (resistance - close) / close if close > 0 else None

        # 表現：近 5/20/60 日報酬
        def _ret(n: int) -> float | None:
            if len(df) > n:
                past = _to_float(df["Close"].iloc[-(n+1)])
                if past and past > 0 and close:
                    return (close / past) - 1.0
            return None

        perf_5d = _ret(5)
        perf_20d = _ret(20)
        perf_60d = _ret(60)

        # 區間位置：相對近 6 個月高低
        lookback = df["Close"].tail(min(len(df), 126))
        pos_high = pos_low = None
        if not lookback.empty and close:
            high = _to_float(lookback.max())
            low = _to_float(lookback.min())
            if high and low and high > low:
                pos_high = (high - close) / high
                pos_low = (close - low) / low

        trend_obj: Dict[str, Any] = {"state": trend}
        # include discovered MA values without forcing a fixed set
        if ma5 is not None:
            trend_obj["ma5"] = ma5
        if ma20 is not None:
            trend_obj["ma20"] = ma20
        if ma50 is not None:
            trend_obj["ma50"] = ma50
        if ma60 is not None:
            trend_obj["ma60"] = ma60
        if ma200 is not None:
            trend_obj["ma200"] = ma200

        return {
            "price": close,
            "trend": trend_obj,
            "momentum": {
                "rsi": rsi,
                "rsi_state": rsi_state,
                "macd": macd,
                "macd_signal": macd_signal,
                "macd_hist": macd_hist,
                "macd_state": macd_state,
            },
            "volatility": {"atr": atr, "atr_pct": atr_pct, "label": vol_label},
            "volume": {"current": vol, "avg20": avg20, "ratio": vol_ratio, "state": vol_state},
            "levels": {
                "support": support,
                "resistance": resistance,
                "distance_to_support_pct": (dist_s * 100) if dist_s is not None else None,
                "distance_to_resistance_pct": (dist_r * 100) if dist_r is not None else None,
            },
            "performance": {
                "ret_5d_pct": (perf_5d * 100) if perf_5d is not None else None,
                "ret_20d_pct": (perf_20d * 100) if perf_20d is not None else None,
                "ret_60d_pct": (perf_60d * 100) if perf_60d is not None else None,
            },
            "range_position": {
                "from_high_pct": (pos_high * 100) if pos_high is not None else None,
                "from_low_pct": (pos_low * 100) if pos_low is not None else None,
            },
        }
    except Exception as e:
        return {"error": str(e)}

def analyze_with_ai(ticker: str):
    df = fetch_data([ticker], period="3mo", interval="1d").get(ticker)
    if df is None or df.empty:
        return {"error": "No data available"}

    df = add_indicators(df)
    last_rows = df.tail(10).to_dict(orient="records")

    sys_text = (
        "你是一位專業的 FinTech 投資分析師。嚴禁自行計算，僅可根據提供的數據做文字解讀。\n"
        "請只輸出一段不超過 3 句的繁體中文建議，"
        "不要輸出 JSON、條列或程式碼區塊。"
    )
    user_text = (
        f"股票 {ticker} 最近 10 天的數據:\n{last_rows}\n\n"
        "請根據上述資料產出自然語句建議（非 JSON）。"
    )
    prompt = sys_text + "\n\n" + user_text

    try:
        if not completion_client:
            return {"error": "OPENAI_API_KEY not set or OpenAI SDK unavailable"}
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-instruct")
        response = completion_client(prompt=prompt, model=model, temperature=0.4)
        
        # Handle both new (object) and legacy (dict) response formats
        try:
            content = response.choices[0].text
        except (TypeError, AttributeError):
            content = response["choices"][0]["text"]

        text = str(content).strip()
        if "```" in text:
            try:
                inner = text.split("```", 2)[1]
                inner = "\n".join(inner.splitlines()[1:]) if "\n" in inner else inner
                text = inner.strip()
            except Exception:
                pass
        if text.startswith("{") and text.endswith("}"):
            try:
                obj = json.loads(text)
                action = obj.get("action")
                timeframe = obj.get("timeframe")
                reasoning = obj.get("reasoning")
                parts = []
                if action:
                    parts.append(f"建議：{action}{'（' + timeframe + '）' if timeframe else ''}。")
                if reasoning:
                    parts.append(str(reasoning).strip())
                text = " ".join(parts) or text
            except Exception:
                pass

        return {"model": model, "summary": text}
    except Exception as e:
        return {"error": str(e)}
