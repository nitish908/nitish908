"""Portfolio: cash + open positions + realized trade history, all in Decimal.

Wraps a FIFOLedger to get accurate, fee-inclusive cost-basis accounting and
exposes the aggregate figures the risk manager and reporting need: equity,
realized/unrealized P&L, and net profit margin.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from trading_agent.utils.decimal_utils import D

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

    def to_dict(self) -> dict:
        """JSON-safe snapshot of the full portfolio state (cash, open lots,
        closed-trade history, last marks), for persisting across process
        restarts -- e.g. a Cloudflare Container that sleeps between polls."""
        return {
            "cash": str(self.cash),
            "ledger": self.ledger.to_dict(),
            "closed_trades": [
                {
                    "symbol": t.symbol,
                    "quantity": str(t.quantity),
                    "entry_price": str(t.entry_price),
                    "exit_price": str(t.exit_price),
                    "entry_fee_alloc": str(t.entry_fee_alloc),
                    "exit_fee_alloc": str(t.exit_fee_alloc),
                    "realized_pnl": str(t.realized_pnl),
                    "net_profit_margin_pct": str(t.net_profit_margin_pct),
                    "opened_at": t.opened_at.isoformat(),
                    "closed_at": t.closed_at.isoformat(),
                }
                for t in self.closed_trades_list
            ],
            "last_marks": {symbol: str(price) for symbol, price in self._last_marks.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Portfolio":
        portfolio = cls(starting_cash=D(data["cash"]))
        portfolio.ledger = FIFOLedger.from_dict(data.get("ledger", {}))
        portfolio.closed_trades_list = [
            RealizedTrade(
                symbol=t["symbol"],
                quantity=D(t["quantity"]),
                entry_price=D(t["entry_price"]),
                exit_price=D(t["exit_price"]),
                entry_fee_alloc=D(t["entry_fee_alloc"]),
                exit_fee_alloc=D(t["exit_fee_alloc"]),
                realized_pnl=D(t["realized_pnl"]),
                net_profit_margin_pct=D(t["net_profit_margin_pct"]),
                opened_at=datetime.fromisoformat(t["opened_at"]),
                closed_at=datetime.fromisoformat(t["closed_at"]),
            )
            for t in data.get("closed_trades", [])
        ]
        portfolio._last_marks = {symbol: D(price) for symbol, price in data.get("last_marks", {}).items()}
        return portfolio
