import pandas as pd
import numpy as np
import os
import json
from typing import Any, Optional
from datetime import datetime, timedelta

from data_fetcher import fetch_data, get_ticker_info
from strategy import add_indicators
from .openai_service import completion_client

class Recommender:
    """
    A class to find trading candidates and generate recommendations.
    """

    def __init__(self, tickers):
        self.tickers = tickers
        self.data = self._fetch_market_data()

    def _fetch_market_data(self):
        """Fetches historical data for the given tickers."""
        print(f"Fetching data for {len(self.tickers)} tickers...")
        return fetch_data(
            self.tickers,
            start_date=(datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'),
            interval="1d"
        )

    def _check_volume(self, df):
        if len(df) < 20:
            return 0, None
        avg_volume_20d = df['Volume'].tail(20).mean()
        current_volume = df['Volume'].iloc[-1]
        if pd.notna(current_volume) and pd.notna(avg_volume_20d) and avg_volume_20d > 0:
            volume_ratio = float(current_volume) / float(avg_volume_20d)
            if volume_ratio > 1.5:
                return 1, f"成交量異常 ({volume_ratio:.1f}x)"
        return 0, None

    def _check_volatility(self, df):
        if 'ATR' in df.columns and pd.notna(df['ATR'].iloc[-1]):
            atr = float(df['ATR'].iloc[-1])
            close_price = float(df['Close'].iloc[-1])
            if close_price > 0:
                volatility_ratio = atr / close_price
                if volatility_ratio > 0.02:
                    return 1, f"高波動率 ({volatility_ratio:.1%})"
        return 0, None

    def _check_price_movement(self, df):
        if len(df) < 6:
            return 0, None
        price_5_days_ago = float(df['Close'].iloc[-6])
        current_price = float(df['Close'].iloc[-1])
        if price_5_days_ago > 0:
            price_change_pct = abs((current_price - price_5_days_ago) / price_5_days_ago)
            if price_change_pct > 0.03:
                return 1, f"價格大幅變動 ({price_change_pct:.1%})"
        return 0, None

    def _check_rsi(self, df):
        if 'RSI' in df.columns and pd.notna(df['RSI'].iloc[-1]):
            rsi = float(df['RSI'].iloc[-1])
            if 30 < rsi < 70:
                return 0.5, f"RSI健康 ({rsi:.1f})"
        return 0, None

    def _compute_quant_insights(self, df: pd.DataFrame) -> dict:
        """從帶指標的 DataFrame 萃取量化洞察（不使用 AI）。"""
        if df is None or df.empty:
            return {}

        last = df.iloc[-1]

        def _f(x: Any) -> Optional[float]:
            try:
                if pd.isna(x):
                    return None
                return float(x)
            except Exception:
                return None

        close = _f(last.get("Close"))
        ma5 = _f(last.get("MA5"))
        ma20 = _f(last.get("MA20"))
        ma60 = _f(last.get("MA60"))
        trend_state = None
        if all(v is not None for v in [ma5, ma20, ma60]):
            if ma5 > ma20 > ma60:
                trend_state = "多頭排列"
            elif ma5 < ma20 < ma60:
                trend_state = "空頭排列"
            else:
                trend_state = "盤整/糾結"

        rsi = _f(last.get("RSI"))
        if rsi is not None:
            if rsi >= 70:
                rsi_state = "超買"
            elif rsi <= 30:
                rsi_state = "超賣"
            elif 45 <= rsi <= 55:
                rsi_state = "平衡"
            else:
                rsi_state = "中性"
        else:
            rsi_state = None

        macd = _f(last.get("MACD"))
        macd_signal = _f(last.get("MACD_SIGNAL"))
        macd_hist = _f(last.get("MACD_HIST"))
        macd_state = None
        if macd is not None and macd_signal is not None:
            macd_state = "黃金交叉" if macd > macd_signal else "死亡交叉"

        atr = _f(last.get("ATR"))
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

        vol = _f(last.get("Volume"))
        avg20 = _f(df["Volume"].tail(20).mean()) if len(df) >= 20 else None
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

        recent = df.tail(min(20, len(df)))
        support = _f(recent.get("Low").min()) if not recent.empty else None
        resistance = _f(recent.get("High").max()) if not recent.empty else None
        dist_s = None
        dist_r = None
        if close and support and resistance and resistance > support:
            dist_s = (close - support) / support if support > 0 else None
            dist_r = (resistance - close) / close if close > 0 else None

        def _ret(n: int) -> Optional[float]:
            if len(df) > n:
                past = _f(df["Close"].iloc[-(n+1)])
                if past and past > 0 and close:
                    return (close / past) - 1.0
            return None

        perf_5d = _ret(5)
        perf_20d = _ret(20)
        perf_60d = _ret(60)

        lookback = df["Close"].tail(min(len(df), 126))
        pos_high = pos_low = None
        if not lookback.empty and close:
            high = _f(lookback.max())
            low = _f(lookback.min())
            if high and low and high > low:
                pos_high = (high - close) / high
                pos_low = (close - low) / low

        return {
            "price": close,
            "trend": {"ma5": ma5, "ma20": ma20, "ma60": ma60, "state": trend_state},
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

    def find_candidates(self):
        """選出候選股票"""
        candidates = []
        print(f"Analyzing {len(self.tickers)} stocks...")

        for ticker in self.tickers:
            if ticker not in self.data:
                continue

            df = self.data[ticker]
            if df is None or df.empty or len(df) < 25:
                continue

            try:
                df = add_indicators(df)

                score = 0
                criteria = []
                rules = [self._check_volume, self._check_volatility, self._check_price_movement, self._check_rsi]

                for rule in rules:
                    rule_score, criterion = rule(df)
                    if criterion:
                        score += rule_score
                        criteria.append(criterion)

                if score >= 0.5:
                    candidates.append(ticker)
                    print(f"✅ {ticker}: Added to candidate list (score: {score}, criteria: {criteria})")

            except Exception as e:
                print(f"❌ {ticker}: Error during analysis - {str(e)}")
                continue

        return candidates

    def generate_recommendations(self, candidates, enable_ai: bool = True):
        """產生交易建議"""
        if not candidates:
            return []

        recommendations = []
        detailed_data = fetch_data(candidates, period="30d", interval="1d")

        for ticker in candidates:
            df = detailed_data.get(ticker)
            if df is None or df.empty or "Close" not in df.columns:
                continue

            try:
                df = add_indicators(df)
                latest_price = float(df['Close'].iloc[-1])
                recent_data = df.tail(min(10, len(df)))

                support = float(recent_data['Low'].min())
                resistance = float(recent_data['High'].max())
                price_range = resistance - support
                if price_range <= 0:
                    continue

                entry_low = support
                entry_high = support + (price_range * 0.4)
                target_price = resistance - (price_range * 0.1)
                stop_loss = max(support - (price_range * 0.15), latest_price * 0.95)

                potential_gain = target_price - entry_high
                potential_loss = entry_high - stop_loss
                risk_reward_ratio = potential_gain / potential_loss if potential_loss > 0 else 0

                if risk_reward_ratio > 2:
                    rating = "強烈推薦"
                elif risk_reward_ratio > 1.5:
                    rating = "推薦"
                elif risk_reward_ratio > 1:
                    rating = "謹慎推薦"
                else:
                    rating = "不推薦"

                info = get_ticker_info(ticker)
                stock_name = info.get("name", ticker) if info else ticker
                stock_industry = info.get("industry", "其他") if info else "其他"

                chart_data = []
                for idx, val in df['Close'].tail(5).items():
                    if pd.notna(val):
                        close_val = float(np.array(val).astype(np.float64))
                        date_str = idx.strftime("%Y-%m-%d") if isinstance(idx, pd.Timestamp) else str(idx)
                        chart_data.append({"date": date_str, "close": close_val})

                signals = []
                if "RSI" in df.columns and pd.notna(df["RSI"].iloc[-1]):
                    rsi_val = float(df["RSI"].iloc[-1])
                    if rsi_val > 70:
                        signals.append("RSI超買，短線可能回調")
                    elif rsi_val < 30:
                        signals.append("RSI超賣，可能反彈")

                if "MACD" in df.columns and "MACD_SIGNAL" in df.columns:
                    if df["MACD"].iloc[-1] > df["MACD_SIGNAL"].iloc[-1]:
                        signals.append("MACD黃金交叉，動能轉強")
                    else:
                        signals.append("MACD死亡交叉，動能轉弱")

                quant_insights = self._compute_quant_insights(df)

                base_rec = {
                    "ticker": ticker,
                    "name": stock_name,
                    "industry": stock_industry,
                    "current_price": f"{latest_price:.2f}",
                    "entry_price_range": f"{entry_low:.2f} - {entry_high:.2f}",
                    "target_profit": f"{target_price:.2f}",
                    "stop_loss": f"{stop_loss:.2f}",
                    "risk_reward_ratio": f"{risk_reward_ratio:.2f}",
                    "support": f"{support:.2f}",
                    "resistance": f"{resistance:.2f}",
                    "rating": rating,
                    "potential_return": f"{((target_price - entry_high) / entry_high * 100):.1f}%",
                    "chart_data": chart_data,
                    "ta_signals": signals,
                    "insights": quant_insights,
                }

                ai_summary = None
                try:
                    if enable_ai and completion_client:
                        ai_summary = self._ai_enrich_recommendation(
                            ticker=ticker,
                            name=stock_name,
                            latest_price=latest_price,
                            entry_low=entry_low,
                            entry_high=entry_high,
                            target_price=target_price,
                            stop_loss=stop_loss,
                            risk_reward_ratio=risk_reward_ratio,
                            support=support,
                            resistance=resistance,
                            code_rating=rating,
                            ta_signals=signals,
                            closes=[c.get("close") for c in chart_data],
                            quant_insights=quant_insights,
                        )
                except Exception as _:
                    ai_summary = None

                if ai_summary:
                    base_rec["ai_summary"] = ai_summary

                recommendations.append(base_rec)

            except Exception as e:
                print(f"❌ {ticker}: Error generating recommendation - {str(e)}")
                continue

        return recommendations

    def _ai_enrich_recommendation(
            self,
            *,
            ticker: str,
            name: str,
            latest_price: float,
            entry_low: float,
            entry_high: float,
            target_price: float,
            stop_loss: float,
            risk_reward_ratio: float,
            support: float,
            resistance: float,
            code_rating: str,
            ta_signals: list[str],
            closes: list[float] | None = None,
            quant_insights: dict | None = None,
    ):
        sys_prompt = "你是一個專業的投資分析師，請根據以下數據提供完整的建議："
        qi_text = ""
        try:
            if quant_insights:
                qi_text = f"技術指標: {json.dumps(quant_insights, ensure_ascii=False)}"
        except Exception:
            qi_text = ""

        user_prompt = (
            f"股票: {ticker} ({name})\n"
            f"現價: {latest_price:.2f}\n"
            f"進場區間: {entry_low:.2f} - {entry_high:.2f}\n"
            f"目標價: {target_price:.2f}\n"
            f"停損點: {stop_loss:.2f}\n"
            f"風險報酬比: {risk_reward_ratio:.2f}\n"
            f"支撐: {support:.2f}, 壓力: {resistance:.2f}\n"
            f"系統評等: {code_rating}\n"
            f"技術指標訊號: {', '.join(ta_signals) if ta_signals else '無'}\n"
        )
        prompt = sys_prompt + "\n" + qi_text + "\n" + user_prompt

        try:
            if not completion_client:
                return {"error": "OpenAI client not available"}
            model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-instruct")
            resp = completion_client(
                prompt=prompt,
                model=model,
                temperature=0.2,
                max_tokens=800,
            )

            # Handle both new (object) and legacy (dict) response formats
            try:
                content = resp.choices[0].text
            except (TypeError, AttributeError):
                content = resp["choices"][0]["text"]
            
            text = str(content).strip()

            if "```" in text:
                try:
                    inner = text.split("```", 2)[1]
                    inner = "\n".join(inner.splitlines()[1:]) if "\n" in inner else inner
                    text = inner.strip()
                except Exception:
                    pass
            if text.startswith("{based on the context, this is a valid JSON string") and text.endswith("}"):
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

            result = {"ai_rating": code_rating}
            try:
                if isinstance(quant_insights, dict):
                    highlights = []
                    ts = quant_insights.get("trend", {}).get("state")
                    if ts:
                        highlights.append(f"趨勢：{ts}")
                    rs = quant_insights.get("momentum", {}).get("rsi_state")
                    if rs:
                        highlights.append(f"RSI：{rs}")
                    ms = quant_insights.get("momentum", {}).get("macd_state")
                    if ms:
                        highlights.append(f"MACD：{ms}")
                    vol_lab = quant_insights.get("volatility", {}).get("label")
                    if vol_lab:
                        highlights.append(f"波動：{vol_lab}")
                    vol_state = quant_insights.get("volume", {}).get("state")
                    if vol_state:
                        highlights.append(f"量能：{vol_state}")
                    result["highlights"] = highlights[:4]
                    result["quant"] = quant_insights
            except Exception:
                pass

            return {
                "model": model,
                "code_rating": code_rating,
                "summary": text,
                "result": result,
            }
        except Exception as e:
            return {"error": str(e)}

