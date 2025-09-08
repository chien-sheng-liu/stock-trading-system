"""Deprecated compatibility shim (use services/strategies instead).

This module only re-exports strategy utilities to avoid breaking older imports.
New code should import directly from:
- services.strategies.strategy_day — day trading tuned defaults
- services.strategies.strategy_stock — swing/position tuned defaults
- services.strategies.strategy_common — common indicators and base strategies
"""

import warnings as _warnings
_warnings.warn(
    "backend.strategy is deprecated; import from services.strategies.* instead",
    DeprecationWarning,
    stacklevel=1,
)

from services.strategies.strategy_common import (
    calculate_ma,
    calculate_ema,
    calculate_rsi,
    calculate_atr,
    calculate_bbands,
    calculate_macd,
    calculate_vwap,
    detect_volume_spike,
    add_indicators,
    ma_crossover_strategy,
    daytrade_composite_strategy,
)

__all__ = [
    'calculate_ma', 'calculate_ema', 'calculate_rsi', 'calculate_atr',
    'calculate_bbands', 'calculate_macd', 'calculate_vwap',
    'detect_volume_spike', 'add_indicators', 'ma_crossover_strategy',
    'daytrade_composite_strategy'
]
