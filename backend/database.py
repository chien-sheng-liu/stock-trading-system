import os
import psycopg2
from psycopg2 import pool

db_pool = None

def init_db_pool():
    global db_pool
    if db_pool is None:
        try:
            print("Initializing database connection pool...")
            db_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                host=os.environ.get('DB_HOST', 'localhost'),
                port=os.environ.get('DB_PORT', '5432'),
                dbname=os.environ.get('DB_NAME', 'stock'),
                user=os.environ.get('DB_USER', 'postgres'),
                password=os.environ.get('DB_PASS', '12345678')
            )
            print("Database connection pool created successfully.")
        except psycopg2.OperationalError as e:
            print(f"Could not connect to the database: {e}")
            db_pool = None

def execute_query(query, params=None, fetch=None):
    """A generic function to execute queries."""
    conn = None
    pool = db_pool
    if not pool:
        return None
        
    try:
        conn = pool.getconn()
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
            conn.commit()
    except Exception as e:
        print(f"Database query failed: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            pool.putconn(conn)

def create_tables():
    """Create tables in the database if they do not exist."""
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
    print("'stocks' table created or already exists.")

def upsert_stocks(stocks):
    """Insert or update a list of stocks."""
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
    data_to_insert = [(s['ticker'], s['name'], s['industry']) for s in stocks]
    
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.executemany(query, data_to_insert)
            conn.commit()
        print(f"Upserted {len(stocks)} stocks into the database.")
    except Exception as e:
        print(f"Failed to upsert stocks: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)

def get_stock_by_ticker(ticker: str):
    """Retrieve a single stock's static info from the database by ticker."""
    query = "SELECT ticker, name, industry FROM stocks WHERE ticker = %s;"
    result = execute_query(query, (ticker,), fetch="one")
    if result:
        return {'ticker': result[0], 'name': result[1], 'industry': result[2]}
    return None

def get_stocks_by_tickers(tickers: list[str]):
    """Retrieve static info for a list of tickers."""
    if not tickers:
        return []
    query = "SELECT ticker, name, industry FROM stocks WHERE ticker = ANY(%s);"
    results = execute_query(query, (tickers,), fetch="all")
    if results:
        return [{'ticker': r[0], 'name': r[1], 'industry': r[2]} for r in results]
    return []

def get_stocks_from_db(industry: str = None):
    """Retrieve stocks from the database, optionally filtering by industry."""
    query = "SELECT ticker, name, industry FROM stocks"
    params = None
    if industry:
        query += " WHERE industry = %s"
        params = (industry,)
    
    results = execute_query(query, params, fetch="all")
    if results:
        return [{'ticker': r[0], 'name': r[1], 'industry': r[2]} for r in results]
    return []

def get_industries_from_db():
    """Retrieve all unique industries from the database."""
    query = "SELECT DISTINCT industry FROM stocks WHERE industry IS NOT NULL ORDER BY industry;"
    results = execute_query(query, fetch="all")
    return [r[0] for r in results] if results else []

# Initialize pool and create tables on module import
init_db_pool()
create_tables()
