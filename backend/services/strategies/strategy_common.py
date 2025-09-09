import pandas as pd
import numpy as np

"""Common indicator builders and baseline strategies.

This module is the single source of truth for technical indicators and
generic strategies used by both day and swing contexts.

Prefer importing tuned wrappers from:
- strategies.strategy_day — 當沖預設
- strategies.strategy_stock — 波段/投資預設
"""

# -----------------------------
# 基礎技術指標
# -----------------------------
def calculate_ma(data, window):
    return data['Close'].rolling(window=window, min_periods=window).mean()

def calculate_ema(data, span):
    return data['Close'].ewm(span=span, adjust=False, min_periods=span).mean()

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = delta.clip(lower=0).rolling(window=window, min_periods=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window=window, min_periods=window).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(data, window=14):
    # 需有 High/Low/Close
    hl = data['High'] - data['Low']
    h_pc = (data['High'] - data['Close'].shift(1)).abs()
    l_pc = (data['Low'] - data['Close'].shift(1)).abs()
    tr = pd.concat([hl, h_pc, l_pc], axis=1).max(axis=1)
    atr = tr.rolling(window=window, min_periods=window).mean()
    return atr

def calculate_bbands(data, window=20, num_std=2.0):
    mid = data['Close'].rolling(window=window, min_periods=window).mean()
    std = data['Close'].rolling(window=window, min_periods=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    width = (upper - lower) / mid
    return mid, upper, lower, width

def calculate_macd(data, fast=12, slow=26, signal=9):
    ema_fast = calculate_ema(data, span=fast)
    ema_slow = calculate_ema(data, span=slow)
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False, min_periods=signal).mean()
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist

def calculate_vwap(data):
    """
    對日內資料：以每個交易日重置的 VWAP；
    若為日線資料：相當於以當日 (H+L+C)/3 * Volume 累加 / Volume 累加。
    """
    if not isinstance(data.index, pd.DatetimeIndex):
        # 盡力而為：不重置
        tp = (data['High'] + data['Low'] + data['Close']) / 3.0
        vwap = (tp * data['Volume']).cumsum() / data['Volume'].replace(0, np.nan).cumsum()
        return vwap

    date_key = data.index.date
    tp = (data['High'] + data['Low'] + data['Close']) / 3.0
    grouped = pd.Series(tp.values * data['Volume'].values, index=data.index).groupby(date_key).cumsum() / \
              data['Volume'].replace(0, np.nan).groupby(date_key).cumsum()
    return grouped

def detect_volume_spike(data, window=20, factor=1.5):
    avg_volume = data['Volume'].rolling(window=window, min_periods=window).mean()
    return data['Volume'] > (avg_volume * factor)

# -----------------------------
# 指標彙整
# -----------------------------
def add_indicators(
    data,
    indicators=('MA5','MA20','MA60','RSI','ATR','BBANDS','MACD','VWAP','VolumeSpike'),
    ma_short=5, ma_mid=20, ma_long=60, rsi_window=14, atr_window=14,
    bb_window=20, bb_std=2.0, macd_fast=12, macd_slow=26, macd_signal=9,
    vol_window=20, vol_factor=1.5
):
    """
    確保必要欄位：Open/High/Low/Close/Volume
    會新增：MA5/20/60, RSI, ATR, BB_MID/UPPER/LOWER/WIDTH, MACD/MACD_SIGNAL/MACD_HIST, VWAP, VolumeSpike
    """
    df = data.copy()

    # yfinance 有時回傳 MultiIndex 欄位
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"數據缺少必要列: {col}")

    # Moving Averages: generate columns based on indicator names (e.g., MA5, MA20, MA50, MA200)
    ma_windows = []
    for ind in indicators:
        if isinstance(ind, str) and ind.upper().startswith('MA'):
            num = ind.upper()[2:]
            if num.isdigit():
                w = int(num)
                if w not in ma_windows:
                    ma_windows.append(w)
    # Backward-compat: if legacy params provided but no MA indicators specified,
    # generate the classic trio
    if not ma_windows and any(k in indicators for k in ('MA5','MA20','MA60')):
        ma_windows = [ma_short, ma_mid, ma_long]
    for w in sorted(set(ma_windows)):
        df[f'MA{w}'] = calculate_ma(df, w)

    if 'RSI' in indicators:
        df['RSI'] = calculate_rsi(df, window=rsi_window)

    if 'ATR' in indicators:
        df['ATR'] = calculate_atr(df, window=atr_window)

    if 'BBANDS' in indicators:
        mid, upper, lower, width = calculate_bbands(df, window=bb_window, num_std=bb_std)
        df['BB_MID'], df['BB_UPPER'], df['BB_LOWER'], df['BB_WIDTH'] = mid, upper, lower, width

    if 'MACD' in indicators:
        macd, macd_signal, macd_hist = calculate_macd(df, fast=macd_fast, slow=macd_slow, signal=macd_signal)
        df['MACD'], df['MACD_SIGNAL'], df['MACD_HIST'] = macd, macd_signal, macd_hist

    if 'VWAP' in indicators:
        df['VWAP'] = calculate_vwap(df)

    if 'VolumeSpike' in indicators:
        df['VolumeSpike'] = detect_volume_spike(df, window=vol_window, factor=vol_factor)

    return df

# -----------------------------
# 基礎策略（保留給回測用）
# -----------------------------
def ma_crossover_strategy(data, short_window=5, long_window=20):
    """
    與既有回測介面相容的均線交叉策略：Signal ∈ {1, -1}
    以指定視窗長度生成對應 MA 欄位並比較。
    """
    sw_col = f'MA{int(short_window)}'
    lw_col = f'MA{int(long_window)}'
    df = add_indicators(
        data,
        indicators=(sw_col, lw_col)
    ).copy()
    df['Signal'] = 0
    df.loc[df[sw_col] > df[lw_col], 'Signal'] = 1
    df.loc[df[sw_col] < df[lw_col], 'Signal'] = -1
    return df

# -----------------------------
# 進階：當沖用綜合策略（可供比較回測）
# -----------------------------
def daytrade_composite_strategy(
    data,
    weights=None,
    rsi_window=14, atr_window=14, bb_window=20, bb_std=2.0,
    ma_short=5, ma_mid=20, ma_long=60, vol_window=20, vol_factor=1.5
):
    """
    綜合多訊號評分，轉為多空 Signal：
    - 量能異常 + 突破（布林上軌） -> 多頭加分
    - MA 多頭排列 (MA5>MA20>MA60) -> 多頭加分
    - MACD 動能轉正 & 上升 -> 多頭加分
    - RSI 位於 50-70 並上行 -> 多頭加分
    - 反向條件對稱扣分
    """
    if weights is None:
        weights = {
            'vol_breakout': 1.0,
            'ma_alignment': 1.0,
            'macd_momentum': 0.75,
            'rsi_trend': 0.5,
            'bb_width_expand': 0.5
        }

    df = add_indicators(
        data,
        indicators=('MA5','MA20','MA60','RSI','ATR','BBANDS','MACD','VWAP','VolumeSpike'),
        ma_short=ma_short, ma_mid=ma_mid, ma_long=ma_long,
        rsi_window=rsi_window, atr_window=atr_window,
        bb_window=bb_window, bb_std=bb_std,
        vol_window=vol_window, vol_factor=vol_factor
    ).copy()

    df['Score'] = 0.0

    # 1) 量能 + 布林突破
    vol_breakout_long = (df['Close'] > df['BB_UPPER']) & (df['VolumeSpike'])
    vol_breakout_short = (df['Close'] < df['BB_LOWER']) & (df['VolumeSpike'])
    df.loc[vol_breakout_long, 'Score'] += weights['vol_breakout']
    df.loc[vol_breakout_short, 'Score'] -= weights['vol_breakout']

    # 2) MA 多頭/空頭排列
    ma_align_long = (df['MA5'] > df['MA20']) & (df['MA20'] > df['MA60'])
    ma_align_short = (df['MA5'] < df['MA20']) & (df['MA20'] < df['MA60'])
    df.loc[ma_align_long, 'Score'] += weights['ma_alignment']
    df.loc[ma_align_short, 'Score'] -= weights['ma_alignment']

    # 3) MACD 動能（柱體 >0 且上升）
    macd_up = (df['MACD_HIST'] > 0) & (df['MACD_HIST'] > df['MACD_HIST'].shift(1))
    macd_down = (df['MACD_HIST'] < 0) & (df['MACD_HIST'] < df['MACD_HIST'].shift(1))
    df.loc[macd_up, 'Score'] += weights['macd_momentum']
    df.loc[macd_down, 'Score'] -= weights['macd_momentum']

    # 4) RSI 動能（站上 50 且上行 / 跌破 50 且下行）
    rsi_up = (df['RSI'] > 50) & (df['RSI'] > df['RSI'].shift(1))
    rsi_down = (df['RSI'] < 50) & (df['RSI'] < df['RSI'].shift(1))
    df.loc[rsi_up, 'Score'] += weights['rsi_trend']
    df.loc[rsi_down, 'Score'] -= weights['rsi_trend']

    # 5) BB 寬度擴張（由盤整轉突破）
    bb_expand = df['BB_WIDTH'] > df['BB_WIDTH'].rolling(bb_window, min_periods=bb_window).mean()
    df.loc[bb_expand, 'Score'] += weights['bb_width_expand']

    # 將分數轉換為 Signal（可視需要調整門檻）
    df['Signal'] = 0
    df.loc[df['Score'] >= 0.5, 'Signal'] = 1
    df.loc[df['Score'] <= -0.5, 'Signal'] = -1

    return df
