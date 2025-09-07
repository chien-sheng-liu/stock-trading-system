"""PostgreSQL connection pool helpers.

DB configuration is sourced exclusively from environment variables loaded
via `.env` (see `backend/settings.py`). No in-code defaults are used.
"""

import psycopg2
from psycopg2 import pool
try:
    # When imported as a package: backend.database
    from .settings import get_db_settings  # type: ignore
except Exception:  # Fallback for script-style imports
    from settings import get_db_settings  # type: ignore

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
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    execute_query(create_table_query)
    print("[DB] Ensured 'stocks' table exists.")


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


# Initialize pool and ensure schema at import time
init_db_pool()
create_tables()
