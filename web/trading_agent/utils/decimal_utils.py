"""Decimal helpers. All money/quantity math in this project uses Decimal,
never float, to avoid binary floating-point rounding errors in P&L accounting."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_EVEN
from typing import Union

Numeric = Union[int, float, str, Decimal]

USD_QUANTIZE = Decimal("0.01")
QTY_QUANTIZE = Decimal("0.00000001")  # 8 dp, enough precision for crypto lot sizes


def D(value: Numeric) -> Decimal:
    """Convert a value to Decimal safely (via str for floats to avoid binary noise)."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def quantize_price(value: Numeric, quantum: Decimal = USD_QUANTIZE) -> Decimal:
    return D(value).quantize(quantum, rounding=ROUND_HALF_EVEN)


def quantize_qty_down(value: Numeric, quantum: Decimal = QTY_QUANTIZE) -> Decimal:
    """Round a quantity DOWN to a lot precision. Never round order quantities up."""
    return D(value).quantize(quantum, rounding=ROUND_DOWN)
