from datetime import datetime, timedelta
from decimal import Decimal

from trading_agent.portfolio.models import Fill
from trading_agent.portfolio.portfolio import Portfolio
from trading_agent.risk import RiskConfig, RiskManager

T0 = datetime(2024, 1, 1)


def fill(trade_id, symbol, side, qty, price, fee, ts=T0):
    return Fill(
        trade_id=trade_id, symbol=symbol, side=side,
        quantity=Decimal(str(qty)), price=Decimal(str(price)), fee=Decimal(str(fee)),
        timestamp=ts,
    )


def test_portfolio_round_trip_preserves_cash_and_open_position():
    portfolio = Portfolio(starting_cash=Decimal("10000"))
    portfolio.process_fill(fill("1", "BTC/USDT", "BUY", 1, 100, 1, T0))
    portfolio.mark_to_market({"BTC/USDT": Decimal("150")})

    data = portfolio.to_dict()
    restored = Portfolio.from_dict(data)

    assert restored.cash == portfolio.cash
    assert restored.equity == portfolio.equity
    positions = restored.open_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "BTC/USDT"
    assert positions[0].quantity == Decimal("1")


def test_portfolio_round_trip_preserves_closed_trades_and_margin():
    portfolio = Portfolio(starting_cash=Decimal("10000"))
    portfolio.process_fill(fill("1", "BTC/USDT", "BUY", 1, 100, 1, T0))
    portfolio.process_fill(fill("2", "BTC/USDT", "SELL", 1, 110, 1, T0 + timedelta(hours=1)))

    data = portfolio.to_dict()
    restored = Portfolio.from_dict(data)

    assert restored.realized_pnl == portfolio.realized_pnl
    assert restored.aggregate_net_margin_pct() == portfolio.aggregate_net_margin_pct()
    assert restored.win_rate() == portfolio.win_rate()
    assert len(restored.closed_trades()) == 1
    assert restored.closed_trades()[0].realized_pnl == Decimal("8")


def test_portfolio_round_trip_across_multiple_symbols_and_partial_lots():
    portfolio = Portfolio(starting_cash=Decimal("10000"))
    portfolio.process_fill(fill("1", "ETH/USDT", "BUY", 2, 100, 0, T0))
    portfolio.process_fill(fill("2", "ETH/USDT", "SELL", 1, 150, 0, T0 + timedelta(hours=1)))
    portfolio.process_fill(fill("3", "AAPL", "BUY", 5, 200, 1, T0 + timedelta(hours=2)))

    data = portfolio.to_dict()
    restored = Portfolio.from_dict(data)

    restored_positions = {p.symbol: p for p in restored.open_positions()}
    assert restored_positions["ETH/USDT"].quantity == Decimal("1")
    assert restored_positions["AAPL"].quantity == Decimal("5")
    assert len(restored.closed_trades()) == 1


def test_risk_manager_round_trip_preserves_kill_switch_state():
    risk_manager = RiskManager(RiskConfig(max_daily_drawdown_pct=Decimal("0.05")))
    risk_manager.start_of_day(Decimal("10000"))
    risk_manager.check_daily_drawdown(Decimal("9000"))
    assert risk_manager.halted_for_day is True

    data = risk_manager.to_dict()

    restored = RiskManager(RiskConfig(max_daily_drawdown_pct=Decimal("0.05")))
    restored.restore(data)

    assert restored.halted_for_day is True
    assert restored.day_start_equity == Decimal("10000")


def test_risk_manager_round_trip_with_no_prior_day_started():
    risk_manager = RiskManager(RiskConfig())
    data = risk_manager.to_dict()
    assert data["day_start_equity"] is None

    restored = RiskManager(RiskConfig())
    restored.restore(data)
    assert restored.day_start_equity is None
    assert restored.halted_for_day is False
