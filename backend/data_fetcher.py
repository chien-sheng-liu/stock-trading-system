import time
from datetime import datetime, timedelta
from core.database import (
    get_stocks_from_db,
    get_industries_from_db,
    get_stock_by_ticker,
    get_stocks_by_tickers,
    get_stock_prices_from_db,
    get_stock_prices_intraday_from_db,
)
from providers.redis_market import fetch_bars_redis  # type: ignore
from providers.yahoo_finance_client import fetch_bars_yahoo  # type: ignore
import pandas as pd  # type: ignore
import os

def get_industries():
    """Gets a list of all unique industries from the database."""
    return get_industries_from_db()

def get_stocks_by_industry(industry: str):
    """Gets a list of stock tickers for a given industry from the database."""
    stocks = get_stocks_from_db(industry=industry)
    return [s['ticker'] for s in stocks]

def _normalize_ticker(t: str) -> str:
    try:
        s = str(t).strip().upper()
        # If pure 4+ digits and no suffix, assume Taiwan .TW
        if s.isdigit() and not s.endswith('.TW'):
            return f"{s}.TW"
        return s
    except Exception:
        return t


def fetch_data(tickers, start_date=None, end_date=None, period="1y", interval="1d"):
    """
    Fetch historical stock data for multiple tickers.
    - Daily (1d): try DB first; if missing, fetch from Yahoo Finance and upsert into DB.
    - Intraday (e.g., 1m/5m/15m): fetch from Yahoo Finance (Redis if enabled) and optionally upsert to intraday table.
    """
    if isinstance(tickers, str):
        tickers = [tickers]
    # Normalize tickers for providers (e.g., 2330 -> 2330.TW)
    tickers = [_normalize_ticker(t) for t in tickers]

    # 1. Validate tickers against DB (best-effort). If DB is unavailable or
    #    no records found, proceed with provided tickers to allow direct Yahoo fetch.
    try:
        valid_stocks = get_stocks_by_tickers(tickers)
        valid_tickers = [s['ticker'] for s in (valid_stocks or [])]
        if not valid_tickers:
            # Fallback: assume provided tickers are valid (e.g., when DB not configured)
            valid_tickers = [str(t).strip() for t in tickers if str(t).strip()]
    except Exception:
        # On any DB error, use provided list
        valid_tickers = [str(t).strip() for t in tickers if str(t).strip()]

    # Informative warning only when we have both sources
    try:
        invalid_tickers = set(tickers) - set(valid_tickers)
        if invalid_tickers:
            print(f"⚠️ Unknown in DB, fetching directly: {list(invalid_tickers)}")
    except Exception:
        pass

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
        # For daily data, try DB first; if coverage is insufficient, backfill via Yahoo
        tickers_to_fetch_from_yahoo = []
        for ticker in valid_tickers:
            df = get_stock_prices_from_db(ticker, start_date, end_date)
            need_backfill = False
            if df is None or df.empty:
                need_backfill = True
            else:
                # Ensure at least a minimal history length and up-to-date tail
                min_rows = 60  # enough for MA20/50 and RSI14
                try:
                    last_idx = df.index[-1]
                    if hasattr(last_idx, 'to_pydatetime'):
                        last_dt = last_idx.to_pydatetime()
                    else:
                        last_dt = datetime.fromisoformat(str(last_idx))
                    target_end = datetime.fromisoformat(end_date)
                    if (len(df) < min_rows) or (last_dt.date() < target_end.date() and (target_end.date() - last_dt.date()).days > 3):
                        need_backfill = True
                except Exception:
                    # If any parsing error, attempt to backfill
                    need_backfill = True
            if not need_backfill:
                data[ticker] = df
            else:
                tickers_to_fetch_from_yahoo.append(ticker)

        if tickers_to_fetch_from_yahoo:
            print(f"Fetching (Yahoo) daily data for: {tickers_to_fetch_from_yahoo}")
            try:
                yahoo_data = fetch_bars_yahoo(tickers_to_fetch_from_yahoo, interval="1d", start_time=start_date, end_time=end_date)
                # Upsert into DB
                from core.database import upsert_stock_prices
                for t, df in (yahoo_data or {}).items():
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        try:
                            upsert_stock_prices(t, df)
                        except Exception:
                            pass
                data.update(yahoo_data or {})
            except Exception as e:
                print(f"Error fetching daily from Yahoo Finance: {e}")

        remaining_tickers = [t for t in tickers_to_fetch_from_yahoo if t not in data]
        if remaining_tickers:
            print(f"No daily data for: {remaining_tickers} (DB/Yahoo) — skipping")
    else:
        # For intraday data, fetch from Yahoo Finance (optionally Redis used elsewhere)
        print(f"Fetching (Yahoo) intraday data for: {valid_tickers} with interval {interval}")
        try:
            # Use appropriate period for intraday per Yahoo limits
            itv = (interval or '5m').lower()
            per = '7d' if itv == '1m' else '30d'
            yahoo_data = fetch_bars_yahoo(valid_tickers, interval=interval, period=per)
            # Optional: upsert into intraday table
            try:
                from core.database import upsert_stock_prices_intraday
                for t, df in (yahoo_data or {}).items():
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        upsert_stock_prices_intraday(t, df, interval)
            except Exception:
                pass
            data.update(yahoo_data or {})
        except Exception as e:
            print(f"Error fetching intraday data from Yahoo Finance: {e}")

        # No further fallback
        remaining_tickers = [t for t in valid_tickers if t not in data]
        if remaining_tickers:
            print(f"No intraday data for: {remaining_tickers} (Yahoo) — skipping")

    return data


def fetch_data_redis(tickers, interval="1m", max_bars=500):
    """
    Fetch recent bars from Redis if available. Returns mapping {ticker: DataFrame}.
    Columns: Open, High, Low, Close, Volume. Index: timestamp.
    """
    if not _redis_enabled():
        return {}
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

def fetch_data_db_intraday(tickers, interval="1m", max_bars=500):
    """Fetch recent intraday bars from DB table stock_prices_intraday.
    Returns mapping {ticker: DataFrame} with columns Open,High,Low,Close,Volume.
    """
    if isinstance(tickers, str):
        tickers = [tickers]
    out = {}
    try:
        for t in tickers:
            df = get_stock_prices_intraday_from_db(t, interval=interval, max_bars=max_bars)
            if df is not None and not df.empty and all(c in df.columns for c in ["Open","High","Low","Close"]):
                out[t] = df
        return out
    except Exception:
        return {}


def fetch_data_yahoo_intraday(tickers, start_time=None, interval="1m"):
    """Fetch bars from Yahoo Finance. Returns mapping {ticker: DataFrame}."""
    if isinstance(tickers, str):
        tickers = [tickers]
    try:
        return fetch_bars_yahoo(tickers, interval=interval, start_time=start_time) or {}
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

def _redis_enabled() -> bool:
    v = os.getenv("REDIS_ENABLED")
    if v is None:
        return False  # default: disabled per current setup
    return str(v).strip().lower() in ("1", "true", "yes", "on")
