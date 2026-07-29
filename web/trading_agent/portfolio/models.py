"""Data models for fills, cost-basis lots, closed trades, and open positions.

All monetary and quantity fields use Decimal to avoid binary floating-point
rounding errors when computing profit margins.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

Side = Literal["BUY", "SELL"]


@dataclass
class Fill:
    """A single executed order fill."""

    trade_id: str
    symbol: str
    side: Side
    quantity: Decimal
    price: Decimal
    fee: Decimal
    timestamp: datetime


@dataclass
class Lot:
    """An open (unmatched) buy lot, FIFO-ordered per symbol.

    `price_per_unit` and `fee_per_unit` are kept separate (rather than
    pre-combined into a single cost-basis-per-unit) so that entry fees can be
    prorated correctly when a lot is later matched in multiple partial sells.
    """

    quantity: Decimal
    price_per_unit: Decimal
    fee_per_unit: Decimal
    timestamp: datetime

    @property
    def cost_basis_per_unit(self) -> Decimal:
        return self.price_per_unit + self.fee_per_unit


@dataclass
class RealizedTrade:
    """The result of matching a SELL against one or more FIFO buy lots
    (or a BUY against short lots) -- a fully closed round-trip slice."""

    symbol: str
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal
    entry_fee_alloc: Decimal
    exit_fee_alloc: Decimal
    realized_pnl: Decimal
    net_profit_margin_pct: Decimal
    opened_at: datetime
    closed_at: datetime

    @property
    def cost_basis(self) -> Decimal:
        return self.entry_price * self.quantity + self.entry_fee_alloc


@dataclass
class Position:
    """A current open position in a symbol, aggregated across remaining lots."""

    symbol: str
    quantity: Decimal
    avg_cost_basis_per_unit: Decimal

    @property
    def cost_basis(self) -> Decimal:
        return self.quantity * self.avg_cost_basis_per_unit

    def market_value(self, mark_price: Decimal) -> Decimal:
        return self.quantity * mark_price

    def unrealized_pnl(self, mark_price: Decimal) -> Decimal:
        return self.market_value(mark_price) - self.cost_basis
