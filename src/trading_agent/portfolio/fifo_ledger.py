"""FIFO cost-basis matching engine.

Long-only model (spot crypto/stocks, no short selling): BUY fills push a new
Lot onto the back of that symbol's queue; SELL fills consume Lots from the
front of the queue (oldest first), possibly spanning multiple lots, emitting
one RealizedTrade per matched lot portion.
"""

from __future__ import annotations

from collections import defaultdict, deque
from decimal import Decimal

from .models import Fill, Lot, RealizedTrade


class FIFOLedger:
    def __init__(self):
        self._lots: dict[str, deque[Lot]] = defaultdict(deque)

    def open_lots(self, symbol: str) -> list[Lot]:
        return list(self._lots[symbol])

    def apply_fill(self, fill: Fill) -> list[RealizedTrade]:
        if fill.side == "BUY":
            return self._apply_buy(fill)
        return self._apply_sell(fill)

    def _apply_buy(self, fill: Fill) -> list[RealizedTrade]:
        fee_per_unit = fill.fee / fill.quantity if fill.quantity else Decimal(0)
        lot = Lot(
            quantity=fill.quantity,
            price_per_unit=fill.price,
            fee_per_unit=fee_per_unit,
            timestamp=fill.timestamp,
        )
        self._lots[fill.symbol].append(lot)
        return []

    def _apply_sell(self, fill: Fill) -> list[RealizedTrade]:
        symbol_lots = self._lots[fill.symbol]
        remaining_to_sell = fill.quantity
        exit_fee_per_unit = fill.fee / fill.quantity if fill.quantity else Decimal(0)
        realized_trades: list[RealizedTrade] = []

        while remaining_to_sell > 0:
            if not symbol_lots:
                raise ValueError(
                    f"Cannot sell {fill.quantity} of {fill.symbol}: no open long "
                    f"lots to match against (short selling is not supported)."
                )

            lot = symbol_lots[0]
            matched_qty = min(lot.quantity, remaining_to_sell)

            entry_fee_alloc = lot.fee_per_unit * matched_qty
            exit_fee_alloc = exit_fee_per_unit * matched_qty
            cost_basis = lot.price_per_unit * matched_qty + entry_fee_alloc
            proceeds = fill.price * matched_qty - exit_fee_alloc
            realized_pnl = proceeds - cost_basis
            net_margin_pct = (
                (realized_pnl / cost_basis * Decimal(100)) if cost_basis != 0 else Decimal(0)
            )

            realized_trades.append(
                RealizedTrade(
                    symbol=fill.symbol,
                    quantity=matched_qty,
                    entry_price=lot.price_per_unit,
                    exit_price=fill.price,
                    entry_fee_alloc=entry_fee_alloc,
                    exit_fee_alloc=exit_fee_alloc,
                    realized_pnl=realized_pnl,
                    net_profit_margin_pct=net_margin_pct,
                    opened_at=lot.timestamp,
                    closed_at=fill.timestamp,
                )
            )

            lot.quantity -= matched_qty
            remaining_to_sell -= matched_qty
            if lot.quantity == 0:
                symbol_lots.popleft()

        return realized_trades
