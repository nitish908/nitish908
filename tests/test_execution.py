import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from trading_agent.adapters.models import AdapterError, AdapterTransientError, OrderResult
from trading_agent.execution import OrderExecutor, TradeLogger


def make_order_result(order_id="1") -> OrderResult:
    return OrderResult(
        order_id=order_id, symbol="BTC/USDT", side="BUY", quantity=Decimal("1"),
        fill_price=Decimal("100"), fee=Decimal("0.1"), status="filled",
        timestamp=datetime.now(timezone.utc),
    )


def test_trade_logger_sqlite_writes_row(tmp_path):
    logger = TradeLogger(path=tmp_path / "trades.sqlite3", log_format="sqlite")
    logger.log_order(make_order_result(), mode="paper")
    logger.close()

    conn = sqlite3.connect(tmp_path / "trades.sqlite3")
    rows = conn.execute("SELECT order_id, symbol, mode FROM trades").fetchall()
    assert rows == [("1", "BTC/USDT", "paper")]


def test_trade_logger_csv_writes_row(tmp_path):
    logger = TradeLogger(path=tmp_path / "trades.sqlite3", log_format="csv")
    logger.log_order(make_order_result(), mode="paper")

    content = (tmp_path / "trades.csv").read_text()
    assert "BTC/USDT" in content
    assert "paper" in content


def test_trade_logger_records_rejections_and_failures(tmp_path):
    logger = TradeLogger(path=tmp_path / "trades.sqlite3", log_format="sqlite")
    logger.log_rejection("AAPL", "BUY", "max open positions reached")
    logger.log_failure("AAPL", "BUY", "adapter timeout")
    logger.close()

    conn = sqlite3.connect(tmp_path / "trades.sqlite3")
    rows = conn.execute("SELECT event_type, detail FROM events").fetchall()
    assert ("rejection", "max open positions reached") in rows
    assert ("failure", "adapter timeout") in rows


def test_order_executor_success_logs_trade(tmp_path):
    adapter = MagicMock()
    adapter.place_order.return_value = make_order_result()
    logger = TradeLogger(path=tmp_path / "trades.sqlite3")

    executor = OrderExecutor(adapter, logger, mode="paper", max_retries=3)
    result = executor.execute("BTC/USDT", "BUY", Decimal("1"))

    assert result.order_id == "1"
    conn = sqlite3.connect(tmp_path / "trades.sqlite3")
    assert conn.execute("SELECT count(*) FROM trades").fetchone()[0] == 1


def test_order_executor_retries_on_transient_error_then_succeeds(tmp_path):
    adapter = MagicMock()
    adapter.place_order.side_effect = [
        AdapterTransientError("timeout"),
        AdapterTransientError("timeout"),
        make_order_result(),
    ]
    logger = TradeLogger(path=tmp_path / "trades.sqlite3")
    executor = OrderExecutor(adapter, logger, max_retries=5)

    result = executor.execute("BTC/USDT", "BUY", Decimal("1"))
    assert result.order_id == "1"
    assert adapter.place_order.call_count == 3


def test_order_executor_gives_up_after_max_retries_and_logs_failure(tmp_path):
    adapter = MagicMock()
    adapter.place_order.side_effect = AdapterTransientError("still down")
    logger = TradeLogger(path=tmp_path / "trades.sqlite3")
    executor = OrderExecutor(adapter, logger, max_retries=2)

    with pytest.raises(AdapterTransientError):
        executor.execute("BTC/USDT", "BUY", Decimal("1"))

    assert adapter.place_order.call_count == 2
    conn = sqlite3.connect(tmp_path / "trades.sqlite3")
    rows = conn.execute("SELECT event_type FROM events").fetchall()
    assert ("failure",) in rows


def test_order_executor_does_not_retry_nontransient_error(tmp_path):
    adapter = MagicMock()
    adapter.place_order.side_effect = AdapterError("invalid order")
    logger = TradeLogger(path=tmp_path / "trades.sqlite3")
    executor = OrderExecutor(adapter, logger, max_retries=5)

    with pytest.raises(AdapterError):
        executor.execute("BTC/USDT", "BUY", Decimal("1"))

    assert adapter.place_order.call_count == 1
