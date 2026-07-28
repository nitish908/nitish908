"""Crypto adapter backed by ccxt, targeting Binance (or any ccxt-supported
exchange with the same call shape). Supports Binance's public testnet via
`sandbox=True`, which is what backs the `paper` trading mode for crypto.

No real network calls are exercised anywhere in this codebase without user-
supplied API keys; this module is unit-tested against a mocked ccxt client.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

import ccxt
import pandas as pd

from trading_agent.portfolio.models import Position
from trading_agent.utils.decimal_utils import D

from .base import ExchangeAdapter
from .models import AdapterError, AdapterTransientError, OrderResult

_TRANSIENT_ERRORS = (ccxt.NetworkError, ccxt.ExchangeNotAvailable, ccxt.RequestTimeout)


class CCXTBinanceAdapter(ExchangeAdapter):
    def __init__(self, api_key: str, api_secret: str, sandbox: bool = True):
        self.exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })
        if sandbox:
            self.exchange.set_sandbox_mode(True)

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        try:
            raw = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        except _TRANSIENT_ERRORS as exc:
            raise AdapterTransientError(str(exc)) from exc
        except Exception as exc:
            raise AdapterError(str(exc)) from exc

        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df

    def get_balance(self) -> dict[str, Decimal]:
        try:
            raw = self.exchange.fetch_balance()
        except _TRANSIENT_ERRORS as exc:
            raise AdapterTransientError(str(exc)) from exc
        except Exception as exc:
            raise AdapterError(str(exc)) from exc

        free = raw.get("free", {}) or {}
        return {asset: D(amount) for asset, amount in free.items() if amount}

    def get_positions(self) -> list[Position]:
        # ccxt/Binance spot balances don't carry cost-basis information --
        # this agent's own Portfolio/FIFO ledger is the source of truth for
        # accurate P&L. This method reflects raw non-zero spot holdings only,
        # with cost basis unknown (reported as the current balance amount at
        # zero cost) and is not used for risk-manager exposure decisions.
        try:
            raw = self.exchange.fetch_balance()
        except _TRANSIENT_ERRORS as exc:
            raise AdapterTransientError(str(exc)) from exc
        except Exception as exc:
            raise AdapterError(str(exc)) from exc

        total = raw.get("total", {}) or {}
        return [
            Position(symbol=asset, quantity=D(amount), avg_cost_basis_per_unit=Decimal(0))
            for asset, amount in total.items()
            if amount
        ]

    def place_order(
        self,
        symbol: str,
        side: Literal["BUY", "SELL"],
        quantity: Decimal,
        order_type: Literal["market", "limit"] = "market",
        price: Optional[Decimal] = None,
    ) -> OrderResult:
        try:
            result = self.exchange.create_order(
                symbol, order_type, side.lower(), float(quantity),
                float(price) if price is not None else None,
            )
        except _TRANSIENT_ERRORS as exc:
            raise AdapterTransientError(str(exc)) from exc
        except Exception as exc:
            raise AdapterError(str(exc)) from exc

        fill_price = D(result.get("average") or result.get("price") or price or 0)
        filled_qty = D(result.get("filled") or quantity)
        fee_info = result.get("fee") or {}
        fee = D(fee_info.get("cost", 0)) if fee_info else Decimal(0)
        timestamp_ms = result.get("timestamp")
        timestamp = (
            datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            if timestamp_ms
            else datetime.now(timezone.utc)
        )

        return OrderResult(
            order_id=str(result.get("id", "")),
            symbol=symbol, side=side, quantity=filled_qty,
            fill_price=fill_price, fee=fee,
            status=str(result.get("status", "unknown")),
            timestamp=timestamp,
        )

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        try:
            self.exchange.cancel_order(order_id, symbol)
            return True
        except Exception:
            return False
