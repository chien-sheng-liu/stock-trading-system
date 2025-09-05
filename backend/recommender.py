import pandas as pd
import numpy as np
from data_fetcher import fetch_data, get_ticker_info
from strategy import add_indicators
from datetime import datetime, timedelta

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
        """Rule 1: Check for abnormal volume."""
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
        """Rule 2: Check for high volatility."""
        if 'ATR' in df.columns and pd.notna(df['ATR'].iloc[-1]):
            atr = float(df['ATR'].iloc[-1])
            close_price = float(df['Close'].iloc[-1])
            if close_price > 0:
                volatility_ratio = atr / close_price
                if volatility_ratio > 0.02:
                    return 1, f"高波動率 ({volatility_ratio:.1%})"
        return 0, None

    def _check_price_movement(self, df):
        """Rule 3: Check for recent price movement."""
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
        """Rule 4: Check RSI."""
        if 'RSI' in df.columns and pd.notna(df['RSI'].iloc[-1]):
            rsi = float(df['RSI'].iloc[-1])
            if 30 < rsi < 70:
                return 0.5, f"RSI健康 ({rsi:.1f})"
        return 0, None

    def find_candidates(self):
        """
        Finds day trading candidates from a list of tickers based on a set of rules.
        """
        candidates = []
        print(f"Analyzing {len(self.tickers)} stocks...")

        for ticker in self.tickers:
            if ticker not in self.data:
                print(f"⚠️  {ticker}: Could not get data")
                continue

            df = self.data[ticker]
            if df is None or df.empty or len(df) < 25:
                print(f"⚠️  {ticker}: Not enough data ({len(df) if df is not None else 0} days)")
                continue

            try:
                df = add_indicators(df)

                if df[['Close', 'Volume', 'High', 'Low']].isnull().values.any():
                    print(f"⚠️  {ticker}: Data contains NaN values")
                    continue

                score = 0
                criteria = []

                rules = [
                    self._check_volume,
                    self._check_volatility,
                    self._check_price_movement,
                    self._check_rsi
                ]

                for rule in rules:
                    try:
                        rule_score, criterion = rule(df)
                        if criterion:
                            score += rule_score
                            criteria.append(criterion)
                    except Exception as e:
                        print(f"⚠️  {ticker}: Error in rule {rule.__name__} - {e}")

                print(f"📊 {ticker}: Score {score:.1f}/3.5 - {criteria}")

                if score >= 1.0:
                    candidates.append(ticker)
                    print(f"✅ {ticker}: Added to candidate list")
                else:
                    print(f"❌ {ticker}: Does not meet criteria (score too low)")

            except Exception as e:
                print(f"❌ {ticker}: Error during analysis - {str(e)}")
                import traceback; traceback.print_exc()
                continue
        
        print(f"Found {len(candidates)} candidates: {candidates}")
        return candidates

    def generate_recommendations(self, candidates):
        """
        Generates entry and exit recommendations for a list of candidate stocks.
        """
        if not candidates:
            print("No candidates, returning empty recommendations.")
            return []

        recommendations = []
        print(f"Generating recommendations for {len(candidates)} stocks...")

        # Fetch more detailed data if needed, or use existing data
        # For this example, we'll re-fetch 10 days of data for simplicity
        detailed_data = fetch_data(candidates, period="10d", interval="1d")

        for ticker in candidates:
            if ticker not in detailed_data:
                print(f"⚠️  {ticker}: Could not get detailed data")
                continue

            df = detailed_data[ticker]
            if df is None or df.empty:
                print(f"⚠️  {ticker}: Detailed data is empty")
                continue

            try:
                latest_price = float(df['Close'].iloc[-1])
                recent_data = df.tail(min(10, len(df)))
                support = float(recent_data['Low'].min())
                resistance = float(recent_data['High'].max())
                price_range = resistance - support

                if price_range <= 0:
                    print(f"⚠️  {ticker}: Invalid price range")
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

                info = get_ticker_info(ticker)
                stock_name = info.get('name', ticker) if info else ticker

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
                print(f"✅ {ticker}: Recommendation generated ({rating})")

            except Exception as e:
                print(f"❌ {ticker}: Error generating recommendation - {str(e)}")
                import traceback; traceback.print_exc()
                continue
        
        print(f"Successfully generated {len(recommendations)} recommendations.")
        return recommendations


def find_candidates(tickers):
    """Legacy function wrapper for compatibility."""
    recommender = Recommender(tickers)
    return recommender.find_candidates()

def generate_recommendations(candidates):
    """Legacy function wrapper for compatibility."""
    # This assumes the initial tickers for the recommender are not needed here.
    # A better approach would be to pass the recommender object or handle this differently.
    # For now, we create a dummy recommender.
    if not candidates:
        return []
    recommender = Recommender(candidates) # Re-initializes with candidates
    return recommender.generate_recommendations(candidates)


if __name__ == '__main__':
    # Test case
    test_tickers = ["2330.TW", "2317.TW", "0050.TW"]  # TSMC, Hon Hai, 0050
    print("Starting recommendation system test...")

    recommender = Recommender(test_tickers)
    candidates = recommender.find_candidates()

    if candidates:
        recommendations = recommender.generate_recommendations(candidates)

        print("" + "=" * 50)
        print("📈 Day Trading Recommendations")
        print("=" * 50)

        for r in recommendations:
            print(f"🏷️  Ticker: {r['ticker']}")
            print(f"💰 Current Price: {r['current_price']}")
            print(f"📥 Suggested Entry: {r['entry_price_range']}")
            print(f"🎯 Target Price: {r['target_profit']}")
            print(f"⛔ Stop Loss: {r['stop_loss']}")
            print(f"⚖️  Risk/Reward Ratio: {r['risk_reward_ratio']}")
            print(f"📊 Support: {r['support']}")
            print(f"📈 Resistance: {r['resistance']}")
            print(f"⭐ Rating: {r['rating']}")
            print(f"💹 Potential Return: {r['potential_return']}")
    else:
        print("❌ No suitable candidates found.")
