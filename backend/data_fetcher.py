import yfinance as yf
import time
from datetime import datetime, timedelta
from core.database import get_stocks_from_db, get_industries_from_db, get_stock_by_ticker, get_stocks_by_tickers

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
    if not start_date and not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    print(f"Fetching price data for: {valid_tickers}")
    print(f"Time range: {start_date} to {end_date}")

    for ticker in valid_tickers:
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                stock_data = yf.download(
                    ticker, start=start_date, end=end_date, interval=interval, progress=False, auto_adjust=True
                )
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

def get_ticker_info(ticker: str):
    """
    Gets combined info for a single stock.
    1. Get static data from DB.
    2. Get info from yfinance.
    """
    static_info = get_stock_by_ticker(ticker)
    if not static_info:
        return None

    try:
        stock = yf.Ticker(ticker)
        yf_info = stock.info
        # Combine static info with yfinance info
        static_info.update({
            "sector": yf_info.get("sector", ""),
            "marketCap": yf_info.get("marketCap", ""),
        })
        return static_info
    except Exception as e:
        print(f"Failed to get yfinance info for {ticker}: {e}")
        return static_info # Return at least the static info
