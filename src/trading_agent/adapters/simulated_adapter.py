"""A zero-network adapter for offline paper-trading demos and agent-loop
tests. Wraps an in-memory Portfolio and a pre-loaded OHLCV price series;
`fetch_ohlcv` advances an internal cursor by one bar each call (simulating
time passing), and `place_order` fills immediately at the current bar's
close price plus a configurable slippage/fee. No real API keys or network
calls are involved.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional
from uuid import uuid4

import pandas as pd

from trading_agent.portfolio import Fill, Portfolio
from trading_agent.portfolio.models import Position
from trading_agent.utils.decimal_utils import D

from .base import ExchangeAdapter
from .models import AdapterError, OrderResult


class SimulatedAdapter(ExchangeAdapter):
    def __init__(
        self,
        price_data: pd.DataFrame,
        starting_cash: Decimal,
        fee_pct: Decimal = Decimal("0.001"),
        slippage_pct: Decimal = Decimal("0.0"),
        base_currency: str = "USD",
        start_index: Optional[int] = None,
    ):
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        if not required.issubset(price_data.columns):
            raise ValueError(f"price_data missing required columns: {required - set(price_data.columns)}")

        self.price_data = price_data.reset_index(drop=True)
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
        self.base_currency = base_currency
        self.portfolio = Portfolio(starting_cash=starting_cash)
        self.cursor = start_index if start_index is not None else min(50, len(self.price_data) - 1)

    def _current_bar(self):
        if self.cursor >= len(self.price_data):
            raise AdapterError("SimulatedAdapter has run out of price data")
        return self.price_data.iloc[self.cursor]

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        window = self.price_data.iloc[: self.cursor + 1].tail(limit).reset_index(drop=True)
        if self.cursor < len(self.price_data) - 1:
            self.cursor += 1
        return window

    def get_balance(self) -> dict[str, Decimal]:
        return {self.base_currency: self.portfolio.cash}

    def get_positions(self) -> list[Position]:
        return self.portfolio.open_positions()

    def place_order(
        self,
        symbol: str,
        side: Literal["BUY", "SELL"],
        quantity: Decimal,
        order_type: Literal["market", "limit"] = "market",
        price: Optional[Decimal] = None,
    ) -> OrderResult:
        bar = self._current_bar()
        close_price = D(bar["close"])
        slippage = close_price * self.slippage_pct
        fill_price = close_price + slippage if side == "BUY" else close_price - slippage
        fee = fill_price * quantity * self.fee_pct
        timestamp = bar["timestamp"]
        if not isinstance(timestamp, datetime):
            timestamp = pd.Timestamp(timestamp).to_pydatetime()

        order_id = str(uuid4())
        fill = Fill(
            trade_id=order_id, symbol=symbol, side=side,
            quantity=quantity, price=fill_price, fee=fee, timestamp=timestamp,
        )
        self.portfolio.process_fill(fill)
        self.portfolio.mark_to_market({symbol: close_price})

        return OrderResult(
            order_id=order_id, symbol=symbol, side=side, quantity=quantity,
            fill_price=fill_price, fee=fee, status="filled", timestamp=timestamp,
        )

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        # Orders fill synchronously and immediately in the simulator, so
        # there is never a pending order to cancel.
        return False
