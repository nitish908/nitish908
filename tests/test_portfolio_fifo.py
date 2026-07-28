from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from trading_agent.portfolio.models import Fill
from trading_agent.portfolio.fifo_ledger import FIFOLedger
from trading_agent.portfolio.portfolio import Portfolio

T0 = datetime(2024, 1, 1)


def fill(trade_id, symbol, side, qty, price, fee, ts=T0):
    return Fill(
        trade_id=trade_id, symbol=symbol, side=side,
        quantity=Decimal(str(qty)), price=Decimal(str(price)), fee=Decimal(str(fee)),
        timestamp=ts,
    )


def test_simple_buy_then_sell_realized_pnl_and_margin():
    ledger = FIFOLedger()
    ledger.apply_fill(fill("1", "BTC/USDT", "BUY", 1, 100, 1, T0))
    trades = ledger.apply_fill(
        fill("2", "BTC/USDT", "SELL", 1, 110, 1, T0 + timedelta(hours=1))
    )

    assert len(trades) == 1
    trade = trades[0]
    # cost_basis = 100*1 + 1 = 101; proceeds = 110*1 - 1 = 109; pnl = 8
    assert trade.realized_pnl == Decimal("8")
    assert trade.cost_basis == Decimal("101")
    # margin = 8/101*100
    expected_margin = (Decimal("8") / Decimal("101") * Decimal(100))
    assert trade.net_profit_margin_pct == expected_margin


def test_sell_spans_multiple_lots_fifo_order():
    ledger = FIFOLedger()
    ledger.apply_fill(fill("1", "ETH/USDT", "BUY", 1, 100, 0, T0))
    ledger.apply_fill(fill("2", "ETH/USDT", "BUY", 1, 200, 0, T0 + timedelta(hours=1)))

    trades = ledger.apply_fill(
        fill("3", "ETH/USDT", "SELL", 1.5, 300, 0, T0 + timedelta(hours=2))
    )

    # Should match 1.0 from the first (cheaper) lot, then 0.5 from the second
    assert len(trades) == 2
    assert trades[0].entry_price == Decimal("100")
    assert trades[0].quantity == Decimal("1")
    assert trades[1].entry_price == Decimal("200")
    assert trades[1].quantity == Decimal("0.5")

    # One lot remains: 0.5 units left at price 200
    remaining = ledger.open_lots("ETH/USDT")
    assert len(remaining) == 1
    assert remaining[0].quantity == Decimal("0.5")


def test_sell_more_than_held_raises():
    ledger = FIFOLedger()
    ledger.apply_fill(fill("1", "AAPL", "BUY", 1, 100, 0, T0))
    with pytest.raises(ValueError):
        ledger.apply_fill(fill("2", "AAPL", "SELL", 2, 110, 0, T0 + timedelta(hours=1)))


def test_fee_proration_on_partial_lot_match():
    ledger = FIFOLedger()
    # Buy 2 units for 200 total price + fee 2 -> fee_per_unit = 1
    ledger.apply_fill(fill("1", "AAPL", "BUY", 2, 100, 2, T0))
    # Sell only 1 of the 2 units
    trades = ledger.apply_fill(fill("2", "AAPL", "SELL", 1, 120, 1, T0 + timedelta(hours=1)))

    assert len(trades) == 1
    trade = trades[0]
    assert trade.entry_fee_alloc == Decimal("1")  # 1 unit * fee_per_unit(1)
    assert trade.exit_fee_alloc == Decimal("1")
    # cost_basis = 100*1 + 1 = 101; proceeds = 120*1 - 1 = 119; pnl = 18
    assert trade.realized_pnl == Decimal("18")


def test_portfolio_equity_cash_and_open_position():
    portfolio = Portfolio(starting_cash=Decimal("10000"))
    portfolio.process_fill(fill("1", "BTC/USDT", "BUY", 1, 100, 1, T0))

    # cash = 10000 - (100*1 + 1) = 9899
    assert portfolio.cash == Decimal("9899")

    portfolio.mark_to_market({"BTC/USDT": Decimal("150")})
    positions = portfolio.open_positions()
    assert len(positions) == 1
    assert positions[0].quantity == Decimal("1")

    # equity = cash + market value = 9899 + 150 = 10049
    assert portfolio.equity == Decimal("10049")
    assert portfolio.unrealized_pnl == Decimal("150") - Decimal("101")  # market - cost_basis


def test_portfolio_realized_pnl_and_aggregate_margin_after_round_trip():
    portfolio = Portfolio(starting_cash=Decimal("10000"))
    portfolio.process_fill(fill("1", "BTC/USDT", "BUY", 1, 100, 1, T0))
    portfolio.process_fill(fill("2", "BTC/USDT", "SELL", 1, 110, 1, T0 + timedelta(hours=1)))

    assert portfolio.realized_pnl == Decimal("8")
    assert len(portfolio.closed_trades()) == 1
    assert portfolio.win_rate() == Decimal("100")

    expected_margin = Decimal("8") / Decimal("101") * Decimal(100)
    assert portfolio.aggregate_net_margin_pct() == expected_margin

    # Position fully closed, no open lots left
    assert portfolio.open_positions() == []
    # cash = 10000 - 101 (buy) + 109 (sell) = 10008
    assert portfolio.cash == Decimal("10008")
    assert portfolio.equity == Decimal("10008")


def test_win_rate_with_mixed_outcomes():
    portfolio = Portfolio(starting_cash=Decimal("10000"))
    # Winning trade
    portfolio.process_fill(fill("1", "AAPL", "BUY", 1, 100, 0, T0))
    portfolio.process_fill(fill("2", "AAPL", "SELL", 1, 110, 0, T0 + timedelta(hours=1)))
    # Losing trade
    portfolio.process_fill(fill("3", "AAPL", "BUY", 1, 100, 0, T0 + timedelta(hours=2)))
    portfolio.process_fill(fill("4", "AAPL", "SELL", 1, 90, 0, T0 + timedelta(hours=3)))

    assert len(portfolio.closed_trades()) == 2
    assert portfolio.win_rate() == Decimal("50")
