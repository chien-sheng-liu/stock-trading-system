import yfinance as yf
import os
import json
import time
from datetime import datetime, timedelta
from core.database import get_stocks_from_db, get_industries_from_db, get_stock_by_ticker, get_stocks_by_tickers

# Optional local name overrides to ensure Chinese names without DB
_LOCAL_NAME_MAP = None

def _load_local_names():
    global _LOCAL_NAME_MAP
    if _LOCAL_NAME_MAP is not None:
        return _LOCAL_NAME_MAP
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, 'data', 'local_names.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                _LOCAL_NAME_MAP = json.load(f) or {}
        else:
            _LOCAL_NAME_MAP = {}
    except Exception:
        _LOCAL_NAME_MAP = {}
    return _LOCAL_NAME_MAP

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
    It first validates tickers against the database.
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

    # 2. Fetch from yfinance for valid tickers
    data = {}
    # Only derive start/end when period is not provided
    if not period and not start_date and not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    print(f"Fetching price data for: {valid_tickers}")
    print(f"Time range: {start_date} to {end_date}")

    for ticker in valid_tickers:
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                dl_kwargs = dict(interval=interval, progress=False, auto_adjust=True)
                if period:
                    dl_kwargs["period"] = period
                else:
                    dl_kwargs["start"] = start_date
                    dl_kwargs["end"] = end_date
                stock_data = yf.download(ticker, **dl_kwargs)
                if stock_data.empty:
                    print(f"⚠️  {ticker}: No data found from yfinance")
                    break
                data[ticker] = stock_data
                break
            except Exception as e:
                print(f"❌ Error fetching from yfinance for {ticker}: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(2)
                else:
                    print(f"❌ Max retries reached for {ticker}")
        if len(valid_tickers) > 1:
            time.sleep(1)
    return data


def fetch_data_direct(tickers, start_date=None, end_date=None, period="1y", interval="1d"):
    """
    Fetch historical stock data directly from yfinance without DB validation.

    Useful for intraday/adhoc lookups (e.g., 即時當沖) when DB may not yet contain the ticker.
    """
    if isinstance(tickers, str):
        tickers = [tickers]

    data = {}
    # Do not mix period with start/end in yfinance calls.
    # If no explicit range and period provided, rely on period only.

    for ticker in tickers:
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                dl_kwargs = dict(interval=interval, progress=False, auto_adjust=True)
                if period:
                    dl_kwargs["period"] = period
                else:
                    dl_kwargs["start"] = start_date
                    dl_kwargs["end"] = end_date
                stock_data = yf.download(ticker, **dl_kwargs)
                if stock_data is None or stock_data.empty:
                    print(f"⚠️  {ticker}: No data (direct) from yfinance")
                    break
                data[ticker] = stock_data
                break
            except Exception as e:
                print(f"❌ Error (direct) fetching from yfinance for {ticker}: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(2)
                else:
                    print(f"❌ Max retries reached for {ticker} (direct)")
        if len(tickers) > 1:
            time.sleep(1)
    return data

def get_ticker_info(ticker: str):
    """
    Gets combined info for a single stock.
    1) Try DB (ticker, name, industry)
    2) Merge with yfinance info if available
    3) If DB missing, still try yfinance to at least populate name/sector
    """
    # 1) Prefer DB for TW tickers to ensure Chinese name
    base = get_stock_by_ticker(ticker)
    if base is None and ticker.endswith('.TW'):
        # Try local overrides mapping first (no network)
        local = _load_local_names()
        local_name = local.get(ticker)
        if local_name:
            base = {"ticker": ticker, "name": local_name, "industry": None}
        else:
            # Do not fallback to yfinance for TW; enforce Chinese via DB/local file
            return None

    # 2) For non-TW, merge limited info from yfinance as a convenience
    yf_info = {}
    try:
        stock = yf.Ticker(ticker)
        yf_info = getattr(stock, 'info', {}) or {}
    except Exception as e:
        print(f"Failed to get yfinance info for {ticker}: {e}")

    if base is None:
        base = {"ticker": ticker, "name": yf_info.get("shortName") or yf_info.get("longName") or ticker, "industry": None}

    merged = dict(base)
    merged.update({
        "sector": yf_info.get("sector", ""),
        "marketCap": yf_info.get("marketCap", ""),
    })
    return merged
