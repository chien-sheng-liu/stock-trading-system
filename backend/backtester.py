import pandas as pd
import numpy as np
from strategy import ma_crossover_strategy


def run_backtest(data, strategy, strategy_params, initial_capital=100000.0):
    """
    Runs a backtest on the provided data using the given strategy.
    """
    # 創建數據副本以避免修改原始數據
    data = data.copy()

    # 應用策略獲取交易信號
    data = strategy(data, **strategy_params)

    # 確保有信號列
    if 'Signal' not in data.columns:
        raise ValueError("策略沒有生成 'Signal' 列")

    # 計算倉位變化
    data['Position'] = data['Signal'].diff()

    # 填充第一個信號為初始倉位
    data['Position'].iloc[0] = data['Signal'].iloc[0]

    # 模擬交易
    positions = data['Position'].fillna(0)
    close_prices = data['Close']

    # 創建投資組合 DataFrame
    portfolio = pd.DataFrame(index=data.index)

    # 計算累積倉位
    portfolio['positions'] = data['Signal'].fillna(0)  # 使用信號作為倉位

    # 計算現金和持股價值
    cash = initial_capital
    cash_flow = []
    holdings_value = []

    for i, (idx, row) in enumerate(data.iterrows()):
        position_change = positions.iloc[i]
        current_price = close_prices.iloc[i]

        # 如果有倉位變化，更新現金
        if position_change != 0:
            cash -= position_change * current_price

        cash_flow.append(cash)
        holdings_value.append(portfolio['positions'].iloc[i] * current_price)

    portfolio['cash'] = cash_flow
    portfolio['holdings'] = holdings_value
    portfolio['total'] = portfolio['cash'] + portfolio['holdings']
    portfolio['returns'] = portfolio['total'].pct_change()

    # 計算績效指標
    # 1. 總交易次數（倉位變化的次數）
    trades = positions[positions != 0]
    total_trades = len(trades)

    # 2. 獲利交易次數（簡化計算：買入後價格上漲的次數）
    profitable_trades = 0
    if total_trades > 0:
        buy_signals = data[data['Position'] > 0]
        for idx in buy_signals.index:
            try:
                # 找到下一個賣出信號
                future_data = data.loc[idx:]
                sell_signal = future_data[future_data['Position'] < 0]
                if not sell_signal.empty:
                    sell_idx = sell_signal.index[0]
                    buy_price = data.loc[idx, 'Close']
                    sell_price = data.loc[sell_idx, 'Close']
                    if sell_price > buy_price:
                        profitable_trades += 1
                else:
                    # 如果沒有賣出信號，比較最後價格
                    buy_price = data.loc[idx, 'Close']
                    final_price = data['Close'].iloc[-1]
                    if final_price > buy_price:
                        profitable_trades += 1
            except:
                continue

    win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0

    # 3. 總收益率
    total_return = ((portfolio['total'].iloc[-1] / initial_capital) - 1) * 100

    # 4. 夏普比率
    if portfolio['returns'].std() != 0 and not portfolio['returns'].empty:
        sharpe_ratio = np.sqrt(252) * (portfolio['returns'].mean() / portfolio['returns'].std())
    else:
        sharpe_ratio = 0

    # 5. 最大回撤
    running_max = portfolio['total'].expanding().max()
    drawdown = (portfolio['total'] - running_max) / running_max
    max_drawdown = abs(drawdown.min() * 100) if not drawdown.empty else 0

    return {
        "trades": int(total_trades),
        "winRate": float(win_rate),
        "profitableTrades": int(profitable_trades),
        "totalReturn": float(total_return),
        "sharpeRatio": float(sharpe_ratio),
        "maxDrawdown": float(max_drawdown),
        "finalValue": float(portfolio['total'].iloc[-1]),
        "initialCapital": float(initial_capital)
    }


if __name__ == '__main__':
    # 測試用例
    dummy_data = {
        'Open': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 110, 112, 111, 113, 115, 114, 113, 112, 110, 108],
        'High': [103, 104, 103, 105, 106, 106, 108, 110, 109, 111, 112, 114, 113, 115, 117, 116, 115, 114, 112, 110],
        'Low': [99, 101, 100, 102, 104, 103, 105, 107, 106, 108, 109, 111, 110, 112, 114, 113, 112, 111, 109, 107],
        'Close': [102, 103, 102, 104, 105, 105, 107, 109, 108, 110, 111, 113, 112, 114, 116, 115, 114, 113, 111, 109],
        'Volume': [1000, 1200, 1100, 1300, 1400, 1350, 1500, 1600, 1550, 1650, 1700, 1800, 1750, 1850, 1900, 1800, 1700,
                   1600, 1500, 1400]
    }
    df = pd.DataFrame(dummy_data)

    try:
        results = run_backtest(df, ma_crossover_strategy, {"short_window": 5, "long_window": 10})
        print("回測結果:")
        for key, value in results.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f"回測錯誤: {e}")