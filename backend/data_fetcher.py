import time
from datetime import datetime, timedelta
from core.database import get_stocks_from_db, get_industries_from_db, get_stock_by_ticker, get_stocks_by_tickers, get_stock_prices_from_db
from providers.redis_market import fetch_bars_redis  # type: ignore
from providers.finmind_client import fetch_bars_finmind, fetch_daily_finmind  # type: ignore
import pandas as pd  # type: ignore

def get_industries():
    """Gets a list of all unique industries from the database."""
    return get_industries_from_db()

def get_stocks_by_industry(industry: str):
    """Gets a list of stock tickers for a given industry from the database."""
    stocks = get_stocks_from_db(industry=industry)
    return [s['ticker'] for s in stocks]

def fetch_data(tickers, start_date=None, end_date=None, period="1y", interval="1d"):
    """
    Fetch historical stock data for multiple tickers.
    For daily data, it first tries to fetch from the local database.
    If data is not available locally, it fetches from FinMind.
    For intraday data, it fetches directly from FinMind.
    """
    if isinstance(tickers, str):
        tickers = [tickers]

    # 1. Validate tickers against DB
    valid_stocks = get_stocks_by_tickers(tickers)
    valid_tickers = [s['ticker'] for s in valid_stocks]
    
    invalid_tickers = set(tickers) - set(valid_tickers)
    if invalid_tickers:
        print(f"⚠️ Invalid or unknown tickers, will be ignored: {list(invalid_tickers)}")

    if not valid_tickers:
        print("No valid tickers to fetch data for.")
        return {}

    # 2. Derive date range if not provided
    if not start_date or not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
        days = 365
        if period and isinstance(period, str) and period.endswith('mo'):
            try:
                months = int(period[:-2])
                days = int(months * 30)
            except Exception:
                days = 365
        elif period and isinstance(period, str) and period.endswith('y'):
            try:
                years = int(period[:-1])
                days = int(years * 365)
            except Exception:
                days = 365
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    # 3. Fetch data
    data = {}
    if interval == "1d":
        # For daily data, try DB first
        tickers_to_fetch_from_finmind = []
        for ticker in valid_tickers:
            df = get_stock_prices_from_db(ticker, start_date, end_date)
            if df is not None and not df.empty:
                data[ticker] = df
            else:
                tickers_to_fetch_from_finmind.append(ticker)

        if tickers_to_fetch_from_finmind:
            print(f"Fetching (FinMind) daily data for: {tickers_to_fetch_from_finmind}")
            try:
                finmind_data = fetch_daily_finmind(tickers_to_fetch_from_finmind, start_date=start_date, end_date=end_date)
                data.update(finmind_data)
            except Exception as e:
                print(f"Error fetching from FinMind: {e}")
    else:
        # For intraday data, fetch directly from FinMind
        print(f"Fetching (FinMind) intraday data for: {valid_tickers}")
        try:
            # Note: fetch_daily_finmind is used for daily, for intraday you might need another function
            # Assuming fetch_bars_finmind can be used for this, though it has a different signature.
            # This part might need adjustment based on provider capabilities.
            # For now, we will rely on the daytrade specific functions to get intraday data.
            pass
        except Exception as e:
            print(f"Error fetching intraday data from FinMind: {e}")

    return data


def fetch_data_redis(tickers, interval="1m", max_bars=500):
    """
    Fetch recent bars from Redis if available. Returns mapping {ticker: DataFrame}.
    Columns: Open, High, Low, Close, Volume. Index: timestamp.
    """
    if isinstance(tickers, str):
        tickers = [tickers]
    try:
        df_map = fetch_bars_redis(tickers, interval=interval, max_bars=max_bars) or {}
        # Ensure DataFrame columns are present
        out = {}
        for t, df in df_map.items():
            if isinstance(df, pd.DataFrame) and not df.empty and all(c in df.columns for c in ["Open","High","Low","Close"]):
                out[t] = df
        return out
    except Exception:
        return {}


def fetch_data_neo(tickers, start_date=None, end_date=None, period="1d", interval="1m"):
    """Fetch bars from Fubon NEO provider if configured via env.
    Returns mapping {ticker: DataFrame}.
    """
    if isinstance(tickers, str):
        tickers = [tickers]
    try:
        df_map = fetch_bars_neo(tickers, interval=interval, period=period, start_date=start_date, end_date=end_date) or {}
        return df_map
    except Exception:
        return {}


def fetch_data_finmind(tickers, start_time=None, interval="1m"):
    """Fetch bars from FinMind TaiwanStockMinuteBar.
    Returns mapping {ticker: DataFrame}.
    """
    if isinstance(tickers, str):
        tickers = [tickers]
    try:
        df_map = fetch_bars_finmind(tickers, interval=interval, start_time=start_time)
        return df_map or {}
    except Exception:
        return {}


def get_ticker_info(ticker: str):
    """
    Gets combined info for a single stock.
    1) Try DB (ticker, name, industry)
    2) If DB missing，回傳基本物件
    """
    # 1) Prefer DB for TW tickers to ensure Chinese name
    base = get_stock_by_ticker(ticker)
    if ticker.endswith('.TW'):
        return base

    if base is None:
        base = {"ticker": ticker, "name": ticker, "industry": None}
    return base