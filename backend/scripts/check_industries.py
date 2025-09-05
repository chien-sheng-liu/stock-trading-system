import os
import sys

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_fetcher import get_industries, get_stocks_by_industry
from database import init_db_pool

def check_industry_data():
    """
    Checks the database for a list of all industries and the
    number of stocks in each.
    """
    print("Initializing DB connection...")
    init_db_pool() # Ensure the pool is initialized

    print("\nFetching all unique industries from the database...")
    try:
        industries = get_industries()
        if not industries:
            print("Could not find any industries in the database.")
            return

        print(f"Found {len(industries)} industries. Checking stock count for each...")
        
        industry_counts = {}
        for industry in industries:
            # The industry name might be in a tuple
            industry_name = industry[0] if isinstance(industry, tuple) else industry
            tickers = get_stocks_by_industry(industry_name)
            industry_counts[industry_name] = len(tickers)

        print("\n--- Stock Counts per Industry ---")
        for industry, count in sorted(industry_counts.items(), key=lambda item: item[1], reverse=True):
            print(f"- {industry}: {count} stocks")
        print("---------------------------------")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_industry_data()
