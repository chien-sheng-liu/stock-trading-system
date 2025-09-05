import os
import sys

# Add the parent directory to the path to allow imports from the backend root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db_pool, db_pool

def verify_database_connection_and_tables():
    """
    Connects to the database, checks for the 'stocks' table,
    and retrieves a few rows to verify data existence.
    """
    if not db_pool:
        print("Database pool is not initialized. Could not connect to the database.")
        return

    conn = None
    try:
        print("Attempting to get a connection from the pool...")
        conn = db_pool.getconn()
        print("Database connection successful.")
        
        with conn.cursor() as cur:
            print("\nVerifying 'stocks' table existence...")
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'stocks'
                );
            """)
            table_exists = cur.fetchone()[0]
            if table_exists:
                print("'stocks' table found.")
            else:
                print("'stocks' table not found.")
                return

            print("\nFetching a few rows from the 'stocks' table...")
            cur.execute("SELECT ticker, name, industry FROM stocks LIMIT 5;")
            rows = cur.fetchall()
            
            if rows:
                print(f"Found {len(rows)} rows. Sample data:")
                for row in rows:
                    print(f"  - Ticker: {row[0]}, Name: {row[1]}, Industry: {row[2]}")
            else:
                print("The 'stocks' table is empty.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)
            print("\nConnection returned to the pool.")

if __name__ == "__main__":
    # The database pool is initialized when database.py is imported.
    # We call it here just to be sure and to see the init messages.
    init_db_pool()
    verify_database_connection_and_tables()
