import pandas as pd
import numpy as np
from data_fetcher import fetch_data, get_ticker_info, fetch_tw_stock_list
from strategy import add_indicators
from datetime import datetime, timedelta


def find_candidates(tickers):
    """
    Finds day trading candidates from a list of tickers based on a set of rules.
    Rules:
    1. High volume: Volume > 1.5 * 20-day average volume
    2. High volatility: ATR(14) > 2% of the closing price
    3. Recent price movement: Price change in last 5 days > 3%
    """
    candidates = []
    print(f"正在分析 {len(tickers)} 支股票...")

    try:
        data = fetch_data(
            tickers,
            start_date=(datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'),
            interval="1d"
        )

        for ticker in tickers:
            if ticker not in data:
                print(f"⚠️  {ticker}: 無法獲取數據")
                continue

            df = data[ticker]
            if df is None or df.empty or len(df) < 25:
                print(f"⚠️  {ticker}: 數據不足或為空 ({len(df) if df is not None else 0} 天)")
                continue

            try:
                df = add_indicators(df)

                if df[['Close', 'Volume', 'High', 'Low']].isnull().values.any():
                    print(f"⚠️  {ticker}: 數據包含缺失值")
                    continue

                score = 0
                criteria = []

                # Rule 1: 成交量異常
                try:
                    if len(df) >= 20:
                        avg_volume_20d = df['Volume'].tail(20).mean()
                        current_volume = df['Volume'].iloc[-1]
                        if pd.notna(current_volume) and pd.notna(avg_volume_20d) and avg_volume_20d > 0:
                            volume_ratio = float(current_volume) / float(avg_volume_20d)
                            if volume_ratio > 1.5:
                                score += 1
                                criteria.append(f"成交量異常 ({volume_ratio:.1f}x)")
                except Exception as e:
                    print(f"⚠️  {ticker}: 成交量分析錯誤 - {e}")

                # Rule 2: 波動率
                try:
                    if 'ATR' in df.columns and pd.notna(df['ATR'].iloc[-1]):
                        atr = float(df['ATR'].iloc[-1])
                        close_price = float(df['Close'].iloc[-1])
                        if close_price > 0:
                            volatility_ratio = atr / close_price
                            if volatility_ratio > 0.02:
                                score += 1
                                criteria.append(f"高波動率 ({volatility_ratio:.1%})")
                except Exception as e:
                    print(f"⚠️  {ticker}: 波動率分析錯誤 - {e}")

                # Rule 3: 價格變動
                try:
                    if len(df) >= 6:
                        price_5_days_ago = float(df['Close'].iloc[-6])
                        current_price = float(df['Close'].iloc[-1])
                        if price_5_days_ago > 0:
                            price_change_pct = abs((current_price - price_5_days_ago) / price_5_days_ago)
                            if price_change_pct > 0.03:
                                score += 1
                                criteria.append(f"價格大幅變動 ({price_change_pct:.1%})")
                except Exception as e:
                    print(f"⚠️  {ticker}: 價格變動分析錯誤 - {e}")

                # Rule 4: RSI 檢查
                try:
                    if 'RSI' in df.columns and pd.notna(df['RSI'].iloc[-1]):
                        rsi = float(df['RSI'].iloc[-1])
                        if 30 < rsi < 70:
                            score += 0.5
                            criteria.append(f"RSI健康 ({rsi:.1f})")
                except Exception as e:
                    print(f"⚠️  {ticker}: RSI分析錯誤 - {e}")

                print(f"📊 {ticker}: 得分 {score:.1f}/3.5 - {criteria}")

                if score >= 1.0:
                    candidates.append(ticker)
                    print(f"✅ {ticker}: 入選候選名單")
                else:
                    print(f"❌ {ticker}: 不符合條件 (得分不足)")

            except Exception as e:
                print(f"❌ {ticker}: 整體分析錯誤 - {str(e)}")
                import traceback; traceback.print_exc()
                continue

    except Exception as e:
        print(f"整體分析錯誤: {str(e)}")
        import traceback; traceback.print_exc()

    print(f"找到 {len(candidates)} 支候選股票: {candidates}")
    return candidates

def generate_recommendations(candidates):
    """
    Generates entry and exit recommendations for a list of candidate stocks.
    """
    if not candidates:
        print("沒有候選股票，直接返回空推薦")
        return []

    all_stocks_with_names = fetch_tw_stock_list()
    name_map = {stock['ticker']: stock['name'] for stock in all_stocks_with_names}

    recommendations = []
    print(f"正在生成 {len(candidates)} 支股票的推薦...")

    try:
        data = fetch_data(candidates, period="10d", interval="1d")

        for ticker in candidates:
            if ticker not in data:
                print(f"⚠️  {ticker}: 無法獲取詳細數據")
                continue

            df = data[ticker]
            if df is None or df.empty:
                print(f"⚠️  {ticker}: 詳細數據為空")
                continue

            try:
                latest_price = float(df['Close'].iloc[-1])

                recent_data = df.tail(min(10, len(df)))

                support = float(recent_data['Low'].min())
                resistance = float(recent_data['High'].max())

                price_range = resistance - support

                if price_range <= 0:
                    print(f"⚠️  {ticker}: 價格區間無效")
                    continue

                entry_low = support
                entry_high = support + (price_range * 0.4)

                target_price = resistance - (price_range * 0.1)

                stop_loss = support - (price_range * 0.15)

                if stop_loss < latest_price * 0.85:
                    stop_loss = latest_price * 0.95

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

                stock_name = name_map.get(ticker, ticker)

                recommendation = {
                    "ticker": ticker,
                    "name": stock_name,
                    "current_price": f"{latest_price:.2f}",
                    "entry_price_range": f"{entry_low:.2f} - {entry_high:.2f}",
                    "target_profit": f"{target_price:.2f}",
                    "stop_loss": f"{stop_loss:.2f}",
                    "risk_reward_ratio": f"{risk_reward_ratio:.2f}",
                    "support": f"{support:.2f}",
                    "resistance": f"{resistance:.2f}",
                    "rating": rating,
                    "potential_return": f"{((target_price - entry_high) / entry_high * 100):.1f}%"
                }

                recommendations.append(recommendation)
                print(f"✅ {ticker}: 推薦已生成 ({rating})")

            except Exception as e:
                print(f"❌ {ticker}: 推薦生成錯誤 - {str(e)}")
                import traceback
                traceback.print_exc()
                continue

    except Exception as e:
        print(f"推薦生成整體錯誤: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # 測試用例
    test_tickers = ["2330.TW", "2317.TW", "0050.TW"]  # 台積電、鴻海、0050
    print("開始測試推薦系統...")

    candidates = find_candidates(test_tickers)

    if candidates:
        recommendations = generate_recommendations(candidates)

        print("\n" + "=" * 50)
        print("📈 日內交易推薦")
        print("=" * 50)

        for r in recommendations:
            print(f"\n🏷️  股票代碼: {r['ticker']}")
            print(f"💰 目前價格: {r['current_price']}")
            print(f"📥 建議進場區間: {r['entry_price_range']}")
            print(f"🎯 目標價位: {r['target_profit']}")
            print(f"⛔ 停損點: {r['stop_loss']}")
            print(f"⚖️  風險收益比: {r['risk_reward_ratio']}")
            print(f"📊 支撐位: {r['support']}")
            print(f"📈 阻力位: {r['resistance']}")
            print(f"⭐ 推薦等級: {r['rating']}")
            print(f"💹 潛在報酬: {r['potential_return']}")
    else:
        print("❌ 沒有找到符合條件的候選股票")
