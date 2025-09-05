import pandas as pd
import numpy as np


def calculate_ma(data, window):
    """Calculate the moving average."""
    return data['Close'].rolling(window=window).mean()


def calculate_rsi(data, window=14):
    """Calculate the Relative Strength Index (RSI)."""
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_atr(data, window=14):
    """Calculate the Average True Range (ATR)."""
    data['H-L'] = data['High'] - data['Low']
    data['H-PC'] = np.abs(data['High'] - data['Close'].shift(1))
    data['L-PC'] = np.abs(data['Low'] - data['Close'].shift(1))
    data['TR'] = data[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    return data['TR'].rolling(window=window).mean()


def detect_volume_spike(data, window=20, factor=1.5):
    """Detects a volume spike."""
    avg_volume = data['Volume'].rolling(window=window).mean()
    return data['Volume'] > (avg_volume * factor)


def add_indicators(data, indicators=['MA5', 'MA20', 'RSI', 'ATR', 'VolumeSpike'], short_window=5, long_window=20):
    """Add multiple indicators to the dataframe."""
    # 確保數據有正確的列名
    data = data.copy()

    # 檢查必要的列是否存在
    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_columns:
        if col not in data.columns:
            raise ValueError(f"數據缺少必要列: {col}")

    if 'MA5' in indicators:
        data['MA5'] = calculate_ma(data, short_window)
    if 'MA20' in indicators:
        data['MA20'] = calculate_ma(data, long_window)
    if 'RSI' in indicators:
        data['RSI'] = calculate_rsi(data)
    if 'ATR' in indicators:
        data['ATR'] = calculate_atr(data)
    if 'VolumeSpike' in indicators:
        data['VolumeSpike'] = detect_volume_spike(data)
    return data


def ma_crossover_strategy(data, short_window=5, long_window=20):
    """Generate signals based on a moving average crossover strategy."""
    data = add_indicators(data, indicators=['MA5', 'MA20'], short_window=short_window, long_window=long_window)
    data['Signal'] = 0
    data.loc[data['MA5'] > data['MA20'], 'Signal'] = 1
    data.loc[data['MA5'] < data['MA20'], 'Signal'] = -1
    return data


if __name__ == '__main__':
    # 測試數據獲取和指標計算
    try:
        import yfinance as yf

        # 獲取真實數據進行測試
        test_data = yf.download("2330.TW", period="1mo", progress=False)

        # 處理 MultiIndex 列名
        if isinstance(test_data.columns, pd.MultiIndex):
            test_data.columns = test_data.columns.get_level_values(0)

        print("原始數據:")
        print(test_data.head())

        # 添加指標
        df_with_indicators = add_indicators(test_data)
        print("\n數據與指標:")
        print(df_with_indicators.tail())

    except Exception as e:
        print(f"測試錯誤: {e}")
        import traceback

        traceback.print_exc()