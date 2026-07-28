"""Stock adapter backed by alpaca-py. Alpaca natively supports paper trading
via `paper=True` on the TradingClient (a separate base URL/account from
live), which is what backs the `paper` trading mode for stocks.

No real network calls are exercised anywhere in this codebase without user-
supplied API keys; this module is unit-tested against mocked Alpaca clients.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from trading_agent.portfolio.models import Position
from trading_agent.utils.decimal_utils import D

from .base import ExchangeAdapter
from .models import AdapterError, AdapterTransientError, OrderResult

_UNIT_MAP = {
    "min": TimeFrameUnit.Minute,
    "minute": TimeFrameUnit.Minute,
    "hour": TimeFrameUnit.Hour,
    "day": TimeFrameUnit.Day,
    "week": TimeFrameUnit.Week,
    "month": TimeFrameUnit.Month,
}


def _parse_timeframe(timeframe: str) -> TimeFrame:
    match = re.match(r"(\d+)\s*([A-Za-z]+)", timeframe)
    if not match:
        raise ValueError(f"Unrecognized timeframe format: {timeframe!r}")
    amount, unit_str = int(match.group(1)), match.group(2).lower()
    unit = _UNIT_MAP.get(unit_str)
    if unit is None:
        raise ValueError(f"Unsupported timeframe unit: {unit_str!r}")
    return TimeFrame(amount, unit)


class AlpacaAdapter(ExchangeAdapter):
    def __init__(self, api_key: str, api_secret: str, paper: bool = True):
        self.trading_client = TradingClient(api_key, api_secret, paper=paper)
        self.data_client = StockHistoricalDataClient(api_key, api_secret)

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        try:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=_parse_timeframe(timeframe),
                limit=limit,
            )
            bar_set = self.data_client.get_stock_bars(request)
        except Exception as exc:
            raise AdapterError(str(exc)) from exc

        df = bar_set.df.reset_index()
        if "symbol" in df.columns:
            df = df.drop(columns=["symbol"])
        df = df.rename(columns={"timestamp": "timestamp"})
        return df[["timestamp", "open", "high", "low", "close", "volume"]]

    def get_balance(self) -> dict[str, Decimal]:
        try:
            account = self.trading_client.get_account()
        except Exception as exc:
            raise AdapterError(str(exc)) from exc
        return {"USD": D(account.cash)}

    def get_positions(self) -> list[Position]:
        try:
            positions = self.trading_client.get_all_positions()
        except Exception as exc:
            raise AdapterError(str(exc)) from exc
        return [
            Position(
                symbol=p.symbol,
                quantity=D(p.qty),
                avg_cost_basis_per_unit=D(p.avg_entry_price),
            )
            for p in positions
        ]

    def place_order(
        self,
        symbol: str,
        side: Literal["BUY", "SELL"],
        quantity: Decimal,
        order_type: Literal["market", "limit"] = "market",
        price: Optional[Decimal] = None,
    ) -> OrderResult:
        if order_type != "market":
            raise AdapterError("AlpacaAdapter currently only supports market orders")

        try:
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=float(quantity),
                side=OrderSide.BUY if side == "BUY" else OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
            order = self.trading_client.submit_order(order_request)
        except Exception as exc:
            raise AdapterTransientError(str(exc)) from exc

        fill_price = D(order.filled_avg_price or price or 0)
        filled_qty = D(order.filled_qty or quantity)
        timestamp = order.filled_at or datetime.now(timezone.utc)

        return OrderResult(
            order_id=str(order.id),
            symbol=symbol, side=side, quantity=filled_qty,
            fill_price=fill_price, fee=Decimal(0),  # Alpaca is commission-free
            status=str(order.status),
            timestamp=timestamp,
        )

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        try:
            self.trading_client.cancel_order_by_id(order_id)
            return True
        except Exception:
            return False
