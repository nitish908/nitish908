from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from trading_agent.adapters import SimulatedAdapter, CCXTBinanceAdapter, AlpacaAdapter
from trading_agent.adapters.models import AdapterError, AdapterTransientError


# ---------------------------------------------------------------------------
# SimulatedAdapter (zero-network)
# ---------------------------------------------------------------------------

def test_simulated_adapter_fetch_ohlcv_advances_cursor(sample_ohlcv_df):
    adapter = SimulatedAdapter(sample_ohlcv_df, starting_cash=Decimal("10000"), start_index=60)
    first = adapter.fetch_ohlcv("TEST/USDT", "1h", limit=10)
    second = adapter.fetch_ohlcv("TEST/USDT", "1h", limit=10)
    assert len(first) == 10
    assert first["timestamp"].iloc[-1] < second["timestamp"].iloc[-1]


def test_simulated_adapter_place_order_updates_balance_and_positions(sample_ohlcv_df):
    adapter = SimulatedAdapter(sample_ohlcv_df, starting_cash=Decimal("10000"), start_index=60)
    result = adapter.place_order("TEST/USDT", "BUY", Decimal("1"))

    assert result.status == "filled"
    assert result.fill_price > 0

    positions = adapter.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "TEST/USDT"

    balance = adapter.get_balance()
    assert balance["USD"] < Decimal("10000")  # cash reduced by the buy


def test_simulated_adapter_sell_realizes_pnl(sample_ohlcv_df):
    adapter = SimulatedAdapter(sample_ohlcv_df, starting_cash=Decimal("10000"), start_index=60,
                                fee_pct=Decimal("0"))
    adapter.place_order("TEST/USDT", "BUY", Decimal("1"))
    adapter.fetch_ohlcv("TEST/USDT", "1h", limit=1)  # advance a bar
    adapter.place_order("TEST/USDT", "SELL", Decimal("1"))

    assert len(adapter.portfolio.closed_trades()) == 1


def test_simulated_adapter_cancel_order_returns_false(sample_ohlcv_df):
    adapter = SimulatedAdapter(sample_ohlcv_df, starting_cash=Decimal("10000"))
    assert adapter.cancel_order("whatever", "TEST/USDT") is False


# ---------------------------------------------------------------------------
# CCXTBinanceAdapter (mocked ccxt client -- no real network calls)
# ---------------------------------------------------------------------------

@patch("trading_agent.adapters.ccxt_binance_adapter.ccxt.binance")
def test_ccxt_adapter_fetch_ohlcv_translates_to_dataframe(mock_binance_cls):
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = [
        [1704067200000, 100.0, 105.0, 99.0, 104.0, 10.0],
        [1704070800000, 104.0, 108.0, 103.0, 107.0, 12.0],
    ]
    mock_binance_cls.return_value = mock_exchange

    adapter = CCXTBinanceAdapter(api_key="k", api_secret="s", sandbox=True)
    mock_exchange.set_sandbox_mode.assert_called_once_with(True)

    df = adapter.fetch_ohlcv("BTC/USDT", "1h", limit=2)
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert df["close"].iloc[-1] == 107.0


@patch("trading_agent.adapters.ccxt_binance_adapter.ccxt.binance")
def test_ccxt_adapter_place_order_success(mock_binance_cls):
    mock_exchange = MagicMock()
    mock_exchange.create_order.return_value = {
        "id": "12345",
        "average": 100.5,
        "filled": 1.0,
        "fee": {"cost": 0.1},
        "timestamp": 1704067200000,
        "status": "closed",
    }
    mock_binance_cls.return_value = mock_exchange

    adapter = CCXTBinanceAdapter(api_key="k", api_secret="s")
    result = adapter.place_order("BTC/USDT", "BUY", Decimal("1"))

    assert result.order_id == "12345"
    assert result.fill_price == Decimal("100.5")
    assert result.fee == Decimal("0.1")


@patch("trading_agent.adapters.ccxt_binance_adapter.ccxt.binance")
def test_ccxt_adapter_wraps_network_errors_as_transient(mock_binance_cls):
    import ccxt

    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.side_effect = ccxt.NetworkError("timeout")
    mock_binance_cls.return_value = mock_exchange

    adapter = CCXTBinanceAdapter(api_key="k", api_secret="s")
    with pytest.raises(AdapterTransientError):
        adapter.fetch_ohlcv("BTC/USDT", "1h", limit=10)


# ---------------------------------------------------------------------------
# AlpacaAdapter (mocked alpaca-py clients -- no real network calls)
# ---------------------------------------------------------------------------

@patch("trading_agent.adapters.alpaca_adapter.StockHistoricalDataClient")
@patch("trading_agent.adapters.alpaca_adapter.TradingClient")
def test_alpaca_adapter_get_balance(mock_trading_cls, mock_data_cls):
    mock_trading = MagicMock()
    mock_account = MagicMock()
    mock_account.cash = "5000.00"
    mock_trading.get_account.return_value = mock_account
    mock_trading_cls.return_value = mock_trading

    adapter = AlpacaAdapter(api_key="k", api_secret="s", paper=True)
    mock_trading_cls.assert_called_once_with("k", "s", paper=True)

    balance = adapter.get_balance()
    assert balance["USD"] == Decimal("5000.00")


@patch("trading_agent.adapters.alpaca_adapter.StockHistoricalDataClient")
@patch("trading_agent.adapters.alpaca_adapter.TradingClient")
def test_alpaca_adapter_get_positions(mock_trading_cls, mock_data_cls):
    mock_trading = MagicMock()
    mock_position = MagicMock()
    mock_position.symbol = "AAPL"
    mock_position.qty = "10"
    mock_position.avg_entry_price = "150.25"
    mock_trading.get_all_positions.return_value = [mock_position]
    mock_trading_cls.return_value = mock_trading

    adapter = AlpacaAdapter(api_key="k", api_secret="s")
    positions = adapter.get_positions()

    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"
    assert positions[0].quantity == Decimal("10")
    assert positions[0].avg_cost_basis_per_unit == Decimal("150.25")


@patch("trading_agent.adapters.alpaca_adapter.StockHistoricalDataClient")
@patch("trading_agent.adapters.alpaca_adapter.TradingClient")
def test_alpaca_adapter_place_order(mock_trading_cls, mock_data_cls):
    mock_trading = MagicMock()
    mock_order = MagicMock()
    mock_order.id = "abc-123"
    mock_order.filled_avg_price = "151.00"
    mock_order.filled_qty = "5"
    mock_order.filled_at = None
    mock_order.status = "filled"
    mock_trading.submit_order.return_value = mock_order
    mock_trading_cls.return_value = mock_trading

    adapter = AlpacaAdapter(api_key="k", api_secret="s")
    result = adapter.place_order("AAPL", "BUY", Decimal("5"))

    assert result.order_id == "abc-123"
    assert result.fill_price == Decimal("151.00")
    assert result.fee == Decimal(0)


@patch("trading_agent.adapters.alpaca_adapter.StockHistoricalDataClient")
@patch("trading_agent.adapters.alpaca_adapter.TradingClient")
def test_alpaca_adapter_rejects_limit_orders(mock_trading_cls, mock_data_cls):
    adapter = AlpacaAdapter(api_key="k", api_secret="s")
    with pytest.raises(AdapterError):
        adapter.place_order("AAPL", "BUY", Decimal("5"), order_type="limit", price=Decimal("100"))
