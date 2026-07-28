"""Structured trade/rejection logging, for audit trail and post-hoc review.
Supports SQLite (default, queryable) or flat CSV files.
"""

from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from trading_agent.adapters.models import OrderResult

_CREATE_TRADES_TABLE = """
CREATE TABLE IF NOT EXISTS trades (
    order_id TEXT,
    ts TEXT,
    symbol TEXT,
    side TEXT,
    quantity TEXT,
    price TEXT,
    fee TEXT,
    status TEXT,
    mode TEXT
)
"""

_CREATE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    ts TEXT,
    event_type TEXT,
    symbol TEXT,
    side TEXT,
    detail TEXT
)
"""


class TradeLogger:
    def __init__(self, path: str | Path = "logs/trades.sqlite3", log_format: Literal["sqlite", "csv"] = "sqlite"):
        self.log_format = log_format
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if log_format == "sqlite":
            self._conn = sqlite3.connect(self.path)
            self._conn.execute(_CREATE_TRADES_TABLE)
            self._conn.execute(_CREATE_EVENTS_TABLE)
            self._conn.commit()
        else:
            self._trades_csv = self.path.with_name("trades.csv")
            self._events_csv = self.path.with_name("events.csv")
            self._ensure_csv_header(self._trades_csv, [
                "order_id", "ts", "symbol", "side", "quantity", "price", "fee", "status", "mode",
            ])
            self._ensure_csv_header(self._events_csv, ["ts", "event_type", "symbol", "side", "detail"])

    @staticmethod
    def _ensure_csv_header(path: Path, header: list[str]) -> None:
        if not path.exists():
            with open(path, "w", newline="") as f:
                csv.writer(f).writerow(header)

    def log_order(self, order_result: OrderResult, mode: str) -> None:
        row = (
            order_result.order_id, order_result.timestamp.isoformat(), order_result.symbol,
            order_result.side, str(order_result.quantity), str(order_result.fill_price),
            str(order_result.fee), order_result.status, mode,
        )
        if self.log_format == "sqlite":
            self._conn.execute(
                "INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", row
            )
            self._conn.commit()
        else:
            with open(self._trades_csv, "a", newline="") as f:
                csv.writer(f).writerow(row)

    def log_event(self, event_type: str, symbol: str, side: str, detail: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        if self.log_format == "sqlite":
            self._conn.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?)", (ts, event_type, symbol, side, detail)
            )
            self._conn.commit()
        else:
            with open(self._events_csv, "a", newline="") as f:
                csv.writer(f).writerow([ts, event_type, symbol, side, detail])

    def log_rejection(self, symbol: str, side: str, reason: str) -> None:
        self.log_event("rejection", symbol, side, reason)

    def log_failure(self, symbol: str, side: str, error: str) -> None:
        self.log_event("failure", symbol, side, error)

    def close(self) -> None:
        if self.log_format == "sqlite":
            self._conn.close()
