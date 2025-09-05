import os
import sys

# Add the parent directory to the path to allow imports from the backend root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import requests
import io
from database import upsert_stocks, init_db_pool, get_stocks_from_db


def fetch_and_store_tw_stocks():
    """Fetches the stock list from TWSE and stores it in the database."""
    print("Fetching new stock list from TWSE...")
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    try:
        response = requests.get(url, timeout=30, headers=headers)
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

        print(f"Found {len(all_stocks)} stocks. Storing in database...")
        upsert_stocks(all_stocks)
        print("Database update complete.")

    except Exception as e:
        print(f"Error fetching Taiwan stock list: {e}")


def verify_data():
    """Verifies that the data has been stored in the database."""
    print("Verifying data in the database...")
    stocks = get_stocks_from_db()
    if stocks:
        print(f"Successfully retrieved {len(stocks)} stocks from the database.")
    else:
        print("Could not retrieve any stocks from the database.")


if __name__ == "__main__":
    init_db_pool()
    fetch_and_store_tw_stocks()
    verify_data()
