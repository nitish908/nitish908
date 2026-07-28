"""Portfolio: cash + open positions + realized trade history, all in Decimal.

Wraps a FIFOLedger to get accurate, fee-inclusive cost-basis accounting and
exposes the aggregate figures the risk manager and reporting need: equity,
realized/unrealized P&L, and net profit margin.
"""

from __future__ import annotations

from decimal import Decimal

from .fifo_ledger import FIFOLedger
from .models import Fill, Position, RealizedTrade


class Portfolio:
    def __init__(self, starting_cash: Decimal):
        self.cash = starting_cash
        self.ledger = FIFOLedger()
        self.closed_trades_list: list[RealizedTrade] = []
        self._last_marks: dict[str, Decimal] = {}

    def process_fill(self, fill: Fill) -> list[RealizedTrade]:
        if fill.side == "BUY":
            self.cash -= fill.price * fill.quantity + fill.fee
        else:
            self.cash += fill.price * fill.quantity - fill.fee

        realized = self.ledger.apply_fill(fill)
        self.closed_trades_list.extend(realized)
        self._last_marks[fill.symbol] = fill.price
        return realized

    def mark_to_market(self, prices: dict[str, Decimal]) -> None:
        self._last_marks.update(prices)

    def open_positions(self) -> list[Position]:
        positions = []
        for symbol, lots in self.ledger._lots.items():
            total_qty = sum((lot.quantity for lot in lots), Decimal(0))
            if total_qty == 0:
                continue
            total_cost = sum((lot.quantity * lot.cost_basis_per_unit for lot in lots), Decimal(0))
            positions.append(
                Position(
                    symbol=symbol,
                    quantity=total_qty,
                    avg_cost_basis_per_unit=total_cost / total_qty,
                )
            )
        return positions

    def exposure_for_symbol(self, symbol: str) -> Decimal:
        for position in self.open_positions():
            if position.symbol == symbol:
                mark = self._last_marks.get(symbol, position.avg_cost_basis_per_unit)
                return position.market_value(mark)
        return Decimal(0)

    @property
    def equity(self) -> Decimal:
        market_value = Decimal(0)
        for position in self.open_positions():
            mark = self._last_marks.get(position.symbol, position.avg_cost_basis_per_unit)
            market_value += position.market_value(mark)
        return self.cash + market_value

    @property
    def realized_pnl(self) -> Decimal:
        return sum((t.realized_pnl for t in self.closed_trades_list), Decimal(0))

    @property
    def unrealized_pnl(self) -> Decimal:
        total = Decimal(0)
        for position in self.open_positions():
            mark = self._last_marks.get(position.symbol, position.avg_cost_basis_per_unit)
            total += position.unrealized_pnl(mark)
        return total

    def closed_trades(self) -> list[RealizedTrade]:
        return list(self.closed_trades_list)

    def aggregate_net_margin_pct(self) -> Decimal:
        total_cost_basis = sum((t.cost_basis for t in self.closed_trades_list), Decimal(0))
        if total_cost_basis == 0:
            return Decimal(0)
        return self.realized_pnl / total_cost_basis * Decimal(100)

    def win_rate(self) -> Decimal:
        if not self.closed_trades_list:
            return Decimal(0)
        wins = sum(1 for t in self.closed_trades_list if t.realized_pnl > 0)
        return Decimal(wins) / Decimal(len(self.closed_trades_list)) * Decimal(100)
