"""PostgreSQL connection pool helpers.

DB configuration is sourced exclusively from environment variables loaded
via `.env` (see `backend/settings.py`). No in-code defaults are used.
"""

import psycopg2
import json
import numpy as np
from datetime import datetime, timezone
from psycopg2 import pool
try:
    from .settings import get_db_settings  # type: ignore
except Exception:  # Fallback for script-style imports
    from core.settings import get_db_settings  # type: ignore

db_pool = None


def init_db_pool():
    """Initialize the global connection pool if it hasn't been created yet."""
    global db_pool
    if db_pool is None:
        try:
            print("[DB] Initializing connection pool...")
            cfg = get_db_settings()
            db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, **cfg)
            print("[DB] Connection pool ready.")
        except ValueError as e:
            # Missing required env vars
            print(f"[DB] Configuration error: {e}")
            db_pool = None
        except psycopg2.OperationalError as e:
            print(f"[DB] Connection failed: {e}")
            db_pool = None


def execute_query(query, params=None, fetch=None):
    """Execute a SQL query.

    - params: tuple/list of parameters or None
    - fetch: "one" to return a single row, "all" for all rows, or None to commit only
    """
    conn = None
    pool_obj = db_pool
    if not pool_obj:
        return None

    try:
        conn = pool_obj.getconn()
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
            conn.commit()
    except Exception as e:
        print(f"[DB] Query failed: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            pool_obj.putconn(conn)


def create_tables():
    """Create the minimal schema if it does not exist."""
    if not db_pool:
        init_db_pool()
        if not db_pool:
            return

    create_table_query = """
    CREATE TABLE IF NOT EXISTS stocks (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        industry VARCHAR(255),
        last_price NUMERIC(10, 2),
        last_price_updated_at TIMESTAMPTZ,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS stock_prices (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR(20) NOT NULL,
        date DATE NOT NULL,
        open NUMERIC(10, 2),
        high NUMERIC(10, 2),
        low NUMERIC(10, 2),
        close NUMERIC(10, 2),
        volume BIGINT,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (ticker, date)
    );
    CREATE TABLE IF NOT EXISTS watchlist (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR(20) UNIQUE NOT NULL,
        note VARCHAR(255),
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS news (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR(20) NOT NULL,
        title TEXT NOT NULL,
        url TEXT,
        source VARCHAR(255),
        published_at TIMESTAMPTZ,
        sentiment NUMERIC,
        events JSONB,
        industry VARCHAR(255),
        ai_summary TEXT,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    -- uniqueness to avoid duplicates (ticker + url + published_at)
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE table_name = 'news' AND constraint_name = 'uniq_news_key'
        ) THEN
            ALTER TABLE news ADD CONSTRAINT uniq_news_key UNIQUE (ticker, url, published_at);
        END IF;
    END $$;
    """
    execute_query(create_table_query)
    # Ensure schema migrations for existing installations
    try:
        # Add missing columns on stocks table if it doesn't exist
        execute_query("ALTER TABLE stocks ADD COLUMN IF NOT EXISTS last_price NUMERIC(10, 2);")
        execute_query("ALTER TABLE stocks ADD COLUMN IF NOT EXISTS last_price_updated_at TIMESTAMPTZ;")
        # Add missing 'industry' column on news table if it doesn't exist
        execute_query("ALTER TABLE news ADD COLUMN IF NOT EXISTS industry VARCHAR(255);")
        execute_query("ALTER TABLE stock_prices ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;")
    except Exception as e:
        print(f"[DB] Migration (add industry column) failed or not needed: {e}")
    try:
        # Backfill industry for existing news rows using stocks table
        execute_query(
            """
            UPDATE news AS n
            SET industry = s.industry
            FROM stocks AS s
            WHERE n.ticker = s.ticker
              AND (n.industry IS NULL OR n.industry = '')
              AND s.industry IS NOT NULL;
            """
        )
    except Exception as e:
        print(f"[DB] Backfill industry on news failed: {e}")
    print("[DB] Ensured 'stocks' and 'watchlist' tables exist.")
    print("[DB] Ensured 'news' table and indexes exist.")


def upsert_stocks(stocks):
    """Insert or update the provided list of stock records."""
    if not stocks or not db_pool:
        return

    query = """
    INSERT INTO stocks (ticker, name, industry)
    VALUES (%s, %s, %s)
    ON CONFLICT (ticker) DO UPDATE SET
        name = EXCLUDED.name,
        industry = EXCLUDED.industry,
        updated_at = CURRENT_TIMESTAMP;
    """
    data_to_insert = [(s["ticker"], s["name"], s["industry"]) for s in stocks]

    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.executemany(query, data_to_insert)
            conn.commit()
        print(f"[DB] Upserted {len(stocks)} stocks.")
    except Exception as e:
        print(f"[DB] Upsert failed: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)

def update_stock_last_price(ticker: str, price: float, price_time: datetime):
    """Update the last known price for a single stock."""
    if not db_pool:
        return
    query = """
    UPDATE stocks
    SET last_price = %s, last_price_updated_at = %s
    WHERE ticker = %s;
    """
    execute_query(query, (price, price_time, ticker))

def upsert_stock_prices(ticker, prices_df):
    """Insert or update historical price data for a stock."""
    if prices_df.empty or not db_pool:
        return

    query = """
    INSERT INTO stock_prices (ticker, date, open, high, low, close, volume, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
    ON CONFLICT (ticker, date) DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume,
        updated_at = CURRENT_TIMESTAMP;
    """
    
    data_to_insert = []
    for index, row in prices_df.iterrows():
        data_to_insert.append((
            ticker,
            index.date(),
            float(row['Open']),
            float(row['High']),
            float(row['Low']),
            float(row['Close']),
            int(row['Volume'])
        ))

    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.executemany(query, data_to_insert)
            conn.commit()
        print(f"[DB] Upserted {len(data_to_insert)} price records for {ticker}.")
    except Exception as e:
        print(f"[DB] Upsert prices failed for {ticker}: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)

def get_stock_prices_from_db(ticker: str, start_date: str, end_date: str):
    """Fetch historical price data from the database."""
    query = """
    SELECT date, open, high, low, close, volume
    FROM stock_prices
    WHERE ticker = %s AND date >= %s AND date <= %s
    ORDER BY date;
    """
    results = execute_query(query, (ticker, start_date, end_date), fetch="all")
    if not results:
        return None
    
    import pandas as pd
    df = pd.DataFrame(results, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    # Normalize numeric dtypes to float/int from NUMERIC/DECIMAL to avoid type errors downstream
    try:
        for col in ['Open','High','Low','Close','Volume']:
            if col in df.columns:
                if col == 'Volume':
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                else:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
    except Exception:
        pass
    return df

def get_stock_by_ticker(ticker: str):
    """Return a single stock (ticker, name, industry) by ticker."""
    query = "SELECT ticker, name, industry FROM stocks WHERE ticker = %s;"
    result = execute_query(query, (ticker,), fetch="one")
    if result:
        return {"ticker": result[0], "name": result[1], "industry": result[2]}
    return None


def get_stocks_by_tickers(tickers: list[str]):
    """Return stock metadata for the given list of tickers."""
    if not tickers:
        return []
    query = "SELECT ticker, name, industry FROM stocks WHERE ticker = ANY(%s);"
    results = execute_query(query, (tickers,), fetch="all")
    if results:
        return [{"ticker": r[0], "name": r[1], "industry": r[2]} for r in results]
    return []


def get_stocks_from_db(industry: str = None):
    """List stocks; optionally filter by industry."""
    query = "SELECT ticker, name, industry FROM stocks"
    params = None
    if industry:
        query += " WHERE industry = %s"
        params = (industry,)

    results = execute_query(query, params, fetch="all")
    if results:
        return [{"ticker": r[0], "name": r[1], "industry": r[2]} for r in results]
    return []


def get_industries_from_db():
    """Return all distinct industries present in the table."""
    query = (
        "SELECT DISTINCT industry FROM stocks "
        "WHERE industry IS NOT NULL ORDER BY industry;"
    )
    results = execute_query(query, fetch="all")
    return [r[0] for r in results] if results else []


def upsert_news_items(items):
    """Upsert a list of news dicts: {ticker,title,url,source,published_at,sentiment,events,ai_summary}."""
    if not items or not db_pool:
        return 0
    query = (
        "INSERT INTO news (ticker, title, url, source, published_at, sentiment, events, industry, ai_summary) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s) "
        "ON CONFLICT ON CONSTRAINT uniq_news_key DO UPDATE SET "
        "sentiment = EXCLUDED.sentiment, events = EXCLUDED.events, industry = EXCLUDED.industry, ai_summary = EXCLUDED.ai_summary"
    )
    data = []
    for it in items:
        ev = it.get("events")
        if isinstance(ev, dict):
            ev = json.dumps(ev, ensure_ascii=False)
        src = it.get("source")
        if isinstance(src, dict):
            try:
                src = src.get("name") or json.dumps(src, ensure_ascii=False)
            except Exception:
                src = None
        # Normalize published_at to ISO string PostgreSQL can parse
        pub = it.get("published_at")
        if isinstance(pub, dict):
            pub = None
        elif isinstance(pub, (int, float)):
            try:
                pub = datetime.fromtimestamp(float(pub), tz=timezone.utc).isoformat()
            except Exception:
                pub = None
        data.append((
            it.get("ticker"),
            it.get("title"),
            it.get("url"),
            src,
            pub if pub else it.get("published_at"),
            it.get("sentiment"),
            ev,
            it.get("industry"),
            it.get("ai_summary"),
        ))
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.executemany(query, data)
            conn.commit()
        return len(items)
    except Exception as e:
        print(f"[DB] Upsert news failed: {e}")
        if conn:
            conn.rollback()
        return 0
    finally:
        if conn:
            db_pool.putconn(conn)


def get_news_from_db(ticker: str = None, limit: int = 50):
    """Fetch recent news; optionally filter by ticker."""
    if not db_pool:
        return []
    if ticker:
        q = "SELECT ticker, title, url, source, published_at, sentiment, events, ai_summary, industry FROM news WHERE ticker = %s ORDER BY published_at DESC NULLS LAST, id DESC LIMIT %s"
        rows = execute_query(q, (ticker, limit), fetch="all")
    else:
        q = "SELECT ticker, title, url, source, published_at, sentiment, events, ai_summary, industry FROM news ORDER BY published_at DESC NULLS LAST, id DESC LIMIT %s"
        rows = execute_query(q, (limit,), fetch="all")
    out = []
    if rows:
        for r in rows:
            out.append({
                "ticker": r[0],
                "title": r[1],
                "url": r[2],
                "source": r[3],
                "published_at": r[4].isoformat() if r[4] else None,
                "sentiment": float(r[5]) if r[5] is not None else None,
                "events": r[6],
                "ai_summary": r[7],
                "industry": r[8],
            })
    return out


def get_news_agg_for_ticker(ticker: str, lookback_min: int = 240):
    """Aggregate recent news sentiment and events for a ticker.
    Returns { sentiment: float|None, events: {..} }.
    """
    try:
        rows = get_news_from_db(ticker=ticker, limit=500)
        if not rows:
            return {"sentiment": None, "events": {}}
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone(timedelta(hours=8))) - timedelta(minutes=max(10, int(lookback_min)))
        def within(r):
            ts = r.get("published_at")
            if not ts:
                return True
            try:
                return datetime.fromisoformat(ts) >= cutoff
            except Exception:
                return True
        filtered = [r for r in rows if within(r)]
        if not filtered:
            return {"sentiment": None, "events": {}}
        ssum = 0.0; scnt = 0
        keys = ["earnings","breaking_news","halt","limit_up","limit_down","disposal"]
        ev = {k: False for k in keys}
        for r in filtered:
            s = r.get("sentiment")
            if isinstance(s, (int, float)):
                ssum += float(s); scnt += 1
            e = r.get("events") or {}
            # events could be string
            try:
                if isinstance(e, str):
                    import json as _json
                    e = _json.loads(e)
            except Exception:
                e = {}
            for k in keys:
                ev[k] = bool(ev[k] or (e.get(k) if isinstance(e, dict) else False))
        avg = (ssum / scnt) if scnt else None
        return {"sentiment": avg, "events": ev}
    except Exception:
        return {"sentiment": None, "events": {}}


def get_news_agg_for_industry(industry: str, lookback_min: int = 240):
    """Aggregate recent news sentiment and events for all tickers in an industry.
    Returns { sentiment: float|None, events: {..}, tickers: [..] }.
    """
    try:
        if not industry:
            return {"sentiment": None, "events": {}, "tickers": []}
        rows = execute_query("SELECT ticker FROM stocks WHERE industry = %s", (industry,), fetch="all")
        tickers = [r[0] for r in (rows or []) if r and r[0]]
        if not tickers:
            return {"sentiment": None, "events": {}, "tickers": []}
        # Collect news
        all_rows = []
        for t in tickers:
            all_rows.extend(get_news_from_db(ticker=t, limit=500))
        if not all_rows:
            return {"sentiment": None, "events": {}, "tickers": tickers}
        # Filter by time
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone(timedelta(hours=8))) - timedelta(minutes=max(10, int(lookback_min)))
        def within(r):
            ts = r.get('published_at')
            if not ts:
                return True
            try:
                return datetime.fromisoformat(ts) >= cutoff
            except Exception:
                return True
        rows_f = [r for r in all_rows if within(r)]
        ssum = 0.0; scnt = 0
        keys = ["earnings","breaking_news","halt","limit_up","limit_down","disposal"]
        ev = {k: False for k in keys}
        import json as _json
        for r in rows_f:
            s = r.get('sentiment')
            if isinstance(s, (int, float)):
                ssum += float(s); scnt += 1
            e = r.get('events') or {}
            if isinstance(e, str):
                try:
                    e = _json.loads(e)
                except Exception:
                    e = {}
            for k in keys:
                ev[k] = bool(ev[k] or (e.get(k) if isinstance(e, dict) else False))
        avg = (ssum / scnt) if scnt else None
        return {"sentiment": avg, "events": ev, "tickers": tickers}
    except Exception:
        return {"sentiment": None, "events": {}, "tickers": []}


# Initialize pool and ensure schema at import time
init_db_pool()
create_tables()
