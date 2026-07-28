from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import uuid4

from trading_agent.portfolio.models import Fill


class AdapterError(Exception):
    """A non-retryable adapter error (e.g. invalid order, insufficient funds)."""


class AdapterTransientError(AdapterError):
    """A retryable adapter error (e.g. network timeout, rate limit, 5xx)."""


@dataclass
class Order:
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: Decimal
    order_type: Literal["market", "limit"] = "market"
    price: Optional[Decimal] = None


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: Decimal
    fill_price: Decimal
    fee: Decimal
    status: str
    timestamp: datetime

    def to_fill(self) -> Fill:
        return Fill(
            trade_id=self.order_id or str(uuid4()),
            symbol=self.symbol,
            side=self.side,
            quantity=self.quantity,
            price=self.fill_price,
            fee=self.fee,
            timestamp=self.timestamp,
        )
