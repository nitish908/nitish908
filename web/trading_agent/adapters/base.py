"""Common interface all exchange/broker adapters implement, so the agent
loop, backtest engine, and execution layer can treat crypto (ccxt/Binance)
and stocks (Alpaca) identically."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Literal, Optional

import pandas as pd

from trading_agent.portfolio.models import Position

from .models import OrderResult


class ExchangeAdapter(ABC):
    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Return a DataFrame with columns: timestamp, open, high, low, close, volume."""

    @abstractmethod
    def get_balance(self) -> dict[str, Decimal]:
        """Return a mapping of asset/currency code -> available balance."""

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Return currently held open positions known to this adapter."""

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: Literal["BUY", "SELL"],
        quantity: Decimal,
        order_type: Literal["market", "limit"] = "market",
        price: Optional[Decimal] = None,
    ) -> OrderResult:
        ...

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        ...
