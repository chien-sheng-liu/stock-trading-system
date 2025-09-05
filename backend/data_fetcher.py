import yfinance as yf
import pandas as pd
import time
from datetime import datetime, timedelta
import requests
import io
import threading

_stock_data_cache = None
_cache_lock = threading.Lock()

def get_fallback_stocks():
    """Returns a hardcoded list of stocks as a fallback."""
    print("⚠️ Using fallback stock list.")
    return [
        {'ticker': '2330.TW', 'name': '台積電', 'industry': '半導體業'},
        {'ticker': '2317.TW', 'name': '鴻海', 'industry': '電腦及週邊設備業'},
        {'ticker': '2454.TW', 'name': '聯發科', 'industry': '半導體業'},
        {'ticker': '2881.TW', 'name': '富邦金', 'industry': '金融保險業'},
        {'ticker': '2882.TW', 'name': '國泰金', 'industry': '金融保險業'},
        {'ticker': '1301.TW', 'name': '台塑', 'industry': '塑膠工業'},
        {'ticker': '1303.TW', 'name': '南亞', 'industry': '塑膠工業'},
        {'ticker': '2002.TW', 'name': '中鋼', 'industry': '鋼鐵工業'},
        {'ticker': '2412.TW', 'name': '中華電', 'industry': '通信網路業'},
    ]

def _fetch_and_cache_tw_stock_list():
    """Internal function to fetch and cache the stock list."""
    global _stock_data_cache
    print("Fetching new stock list from TWSE...")
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        response.encoding = 'big5'
        html_df = pd.read_html(io.StringIO(response.text))

        df = html_df[0]
        df.columns = df.iloc[0]
        df = df[1:]

        df = df[df['市場別'] == '上市']
        df = df[df['有價證券代號及名稱'].str.match(r'^\d{4}\s+.*', na=False)]

        all_stocks = []
        for _, row in df.iterrows():
            try:
                ticker_name_str = row['有價證券代號及名稱']
                industry = row['產業別']

                if isinstance(ticker_name_str, str) and isinstance(industry, str):
                    parts = ticker_name_str.split()
                    if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) == 4:
                        ticker = parts[0]
                        name = parts[1]
                        all_stocks.append({
                            'ticker': f"{ticker}.TW",
                            'name': name,
                            'industry': industry
                        })
            except Exception:
                continue
        
        with _cache_lock:
            _stock_data_cache = all_stocks
        print(f"Successfully fetched and cached {len(all_stocks)} stocks.")

    except Exception as e:
        print(f"Error fetching Taiwan stock list: {e}")
        with _cache_lock:
            if _stock_data_cache is None: # Only use fallback if cache is empty
                _stock_data_cache = get_fallback_stocks()

def update_stock_list_periodically():
    """Calls the fetching function and schedules the next call."""
    _fetch_and_cache_tw_stock_list()
    threading.Timer(3600, update_stock_list_periodically).start()

def fetch_tw_stock_list():
    """Returns the cached list of stocks, fetching it if the cache is empty."""
    with _cache_lock:
        if _stock_data_cache is None:
            print("Cache is empty, performing initial fetch...")
            _fetch_and_cache_tw_stock_list()
        return _stock_data_cache

def get_industries():
    """整理所有股票的產業分類"""
    stocks = fetch_tw_stock_list()
    if not stocks:
        return []
    industries = sorted(list(set(stock['industry'] for stock in stocks if stock.get('industry'))))
    return industries

def get_stocks_by_industry(industry: str):
    """
    根據產業名稱從快取的台股清單中篩選股票
    """
    all_stocks = fetch_tw_stock_list()
    if not all_stocks:
        return []
    
    matched_stocks = [
        stock['ticker'] for stock in all_stocks 
        if stock.get('industry') == industry
    ]
    
    print(f"在「{industry}」產業中找到 {len(matched_stocks)} 支股票")
    return matched_stocks

def fetch_data(tickers, start_date=None, end_date=None, period="1y", interval="1d"):
    """
    Fetch historical stock data for multiple tickers with error handling and retry mechanism.
    """
    data = {}
    if isinstance(tickers, str):
        tickers = [tickers]

    if not start_date and not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    print(f"開始獲取數據: {tickers}")
    print(f"時間範圍: {start_date} 到 {end_date}")

    for ticker in tickers:
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                stock_data = yf.download(
                    ticker, start=start_date, end=end_date, interval=interval, progress=False, auto_adjust=True
                )
                if stock_data.empty:
                    print(f"⚠️  {ticker}: 獲取的數據為空")
                    break
                data[ticker] = stock_data
                break
            except Exception as e:
                print(f"❌ 獲取 {ticker} 數據時出錯: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(2)
                else:
                    print(f"❌ 無法獲取 {ticker} 的數據，已達到最大重試次數")
        if len(tickers) > 1:
            time.sleep(1)
    return data

def get_ticker_info(ticker: str):
    """抓取單一股票的 yfinance info"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "ticker": ticker,
            "name": info.get("longName", ticker),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", "")
        }
    except Exception as e:
        print(f"取得 {ticker} 資訊失敗: {e}")
        return None

# Start the background task to update the stock list cache
update_thread = threading.Thread(target=update_stock_list_periodically, daemon=True)
update_thread.start()