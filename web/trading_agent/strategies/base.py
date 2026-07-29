"""Strategy interface: a Strategy turns an OHLCV DataFrame into a trading signal."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional

import pandas as pd


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class StrategyResult:
    signal: Signal
    reason: str
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None


class Strategy(ABC):
    """Base class for all technical-indicator strategies.

    `generate_signal` receives an OHLCV DataFrame (columns: timestamp, open,
    high, low, close, volume) up to and including the latest closed bar, and
    must return a StrategyResult. Implementations should be stateless across
    calls (all context comes from the passed-in DataFrame) so they work
    identically in live polling and in the backtest engine's rolling window.
    """

    name: str = "base"

    def __init__(self, params: dict | None = None):
        self.params = params or {}

    @abstractmethod
    def generate_signal(self, ohlcv: pd.DataFrame) -> StrategyResult:
        ...

    @abstractmethod
    def required_lookback(self) -> int:
        """Minimum number of bars needed before this strategy can produce a signal."""
        ...
