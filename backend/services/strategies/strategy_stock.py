"""Swing/position trading strategy utilities.

Use in: 股票分析（/api/stock/analyze）— 波段/投資視角。
Tuning focuses on medium/longer trend context (MA20/50/200) with core
momentum/volatility indicators intact.
"""

from typing import Iterable
from .strategy_common import add_indicators as _add_indicators


def add_indicators(
    data,
    indicators: Iterable[str] = (
        'MA20','MA50','MA200','RSI','ATR','BBANDS','MACD','VWAP','VolumeSpike'
    ),
    ma_short: int = 20,
    ma_mid: int = 50,
    ma_long: int = 200,
    rsi_window: int = 14,
    atr_window: int = 14,
    bb_window: int = 20,
    bb_std: float = 2.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    vol_window: int = 20,
    vol_factor: float = 1.5,
):
    return _add_indicators(
        data,
        indicators=indicators,
        ma_short=ma_short,
        ma_mid=ma_mid,
        ma_long=ma_long,
        rsi_window=rsi_window,
        atr_window=atr_window,
        bb_window=bb_window,
        bb_std=bb_std,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
        vol_window=vol_window,
        vol_factor=vol_factor,
    )
