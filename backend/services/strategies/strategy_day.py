"""Day trading strategy utilities.

Use in: 當沖推薦流程（services.recommendation_service）與相關分析。
Endpoints relying on this: `/api/recommend/auto`（產業自動推薦）、
AI 單股推薦在量化洞察計算（services/analysis_service）也使用日內預設。

Tuning: intraday/short-term defaults (MA5/20/60, RSI, ATR, BBANDS, MACD, VWAP, VolumeSpike).
"""

from typing import Iterable
from .strategy_common import add_indicators as _add_indicators


def add_indicators(
    data,
    indicators: Iterable[str] = (
        'MA5','MA20','MA60','RSI','ATR','BBANDS','MACD','VWAP','VolumeSpike'
    ),
    ma_short: int = 5,
    ma_mid: int = 20,
    ma_long: int = 60,
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
