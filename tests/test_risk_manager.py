from decimal import Decimal

import pytest

from trading_agent.portfolio.models import Position
from trading_agent.risk import RiskConfig, RiskManager, TradeProposal


def make_manager(**overrides) -> RiskManager:
    config = RiskConfig(
        risk_pct_per_trade=Decimal("0.01"),
        min_risk_reward_ratio=Decimal("1.5"),
        max_open_positions=5,
        max_exposure_pct_per_symbol=Decimal("0.25"),
        max_daily_drawdown_pct=Decimal("0.05"),
        default_stop_loss_pct=Decimal("0.02"),
    )
    for key, value in overrides.items():
        setattr(config, key, value)
    return RiskManager(config)


def test_position_sizing_formula():
    manager = make_manager()
    equity = Decimal("10000")
    proposal = TradeProposal(
        symbol="BTC/USDT", side="BUY",
        entry_price=Decimal("100"), stop_loss=Decimal("95"), take_profit=Decimal("115"),
    )
    decision = manager.evaluate_trade(proposal, equity, open_positions=[])

    # risk_amount = 10000 * 0.01 = 100; stop_distance = 5; raw_qty = 20
    # exposure cap: max_position_value = 10000*0.25=2500; qty_by_exposure = 2500/100=25
    # quantity = min(20, 25) = 20
    assert decision.approved
    assert decision.risk_amount == Decimal("100")
    assert decision.quantity == Decimal("20.00000000")


def test_rejects_when_reward_risk_ratio_too_low():
    manager = make_manager(min_risk_reward_ratio=Decimal("2.0"))
    proposal = TradeProposal(
        symbol="AAPL", side="BUY",
        entry_price=Decimal("100"), stop_loss=Decimal("95"), take_profit=Decimal("105"),
    )
    # reward=5, risk=5 -> ratio 1.0 < 2.0
    decision = manager.evaluate_trade(proposal, Decimal("10000"), open_positions=[])
    assert not decision.approved
    assert "risk" in decision.reason.lower()


def test_rejects_when_max_open_positions_reached():
    manager = make_manager(max_open_positions=2)
    open_positions = [
        Position(symbol="AAPL", quantity=Decimal("10"), avg_cost_basis_per_unit=Decimal("100")),
        Position(symbol="ETH/USDT", quantity=Decimal("2"), avg_cost_basis_per_unit=Decimal("2000")),
    ]
    proposal = TradeProposal(
        symbol="BTC/USDT", side="BUY",
        entry_price=Decimal("100"), stop_loss=Decimal("95"), take_profit=Decimal("115"),
    )
    decision = manager.evaluate_trade(proposal, Decimal("10000"), open_positions=open_positions)
    assert not decision.approved
    assert "max open positions" in decision.reason


def test_allows_adding_to_existing_symbol_even_at_position_cap():
    manager = make_manager(max_open_positions=1)
    open_positions = [
        Position(symbol="BTC/USDT", quantity=Decimal("1"), avg_cost_basis_per_unit=Decimal("100")),
    ]
    proposal = TradeProposal(
        symbol="BTC/USDT", side="BUY",
        entry_price=Decimal("100"), stop_loss=Decimal("95"), take_profit=Decimal("115"),
    )
    decision = manager.evaluate_trade(proposal, Decimal("10000"), open_positions=open_positions)
    assert decision.approved


def test_exposure_cap_limits_quantity():
    manager = make_manager(max_exposure_pct_per_symbol=Decimal("0.01"))
    equity = Decimal("10000")
    proposal = TradeProposal(
        symbol="BTC/USDT", side="BUY",
        entry_price=Decimal("100"), stop_loss=Decimal("95"), take_profit=Decimal("115"),
    )
    # max_position_value = 10000*0.01=100 -> qty_by_exposure = 1; raw_qty(from risk) = 20
    decision = manager.evaluate_trade(proposal, equity, open_positions=[])
    assert decision.approved
    assert decision.quantity == Decimal("1.00000000")


def test_existing_exposure_reduces_available_room():
    manager = make_manager(max_exposure_pct_per_symbol=Decimal("0.25"))
    equity = Decimal("10000")
    proposal = TradeProposal(
        symbol="BTC/USDT", side="BUY",
        entry_price=Decimal("100"), stop_loss=Decimal("95"), take_profit=Decimal("115"),
    )
    # max_position_value=2500; existing exposure=2450 -> remaining budget=50 -> qty_by_exposure=0.5
    decision = manager.evaluate_trade(
        proposal, equity, open_positions=[], existing_symbol_exposure=Decimal("2450")
    )
    assert decision.approved
    assert decision.quantity == Decimal("0.50000000")


def test_rejects_when_zero_stop_distance():
    manager = make_manager()
    proposal = TradeProposal(
        symbol="BTC/USDT", side="BUY",
        entry_price=Decimal("100"), stop_loss=Decimal("100"), take_profit=Decimal("115"),
    )
    decision = manager.evaluate_trade(proposal, Decimal("10000"), open_positions=[])
    assert not decision.approved
    assert "stop-loss" in decision.reason


def test_daily_drawdown_kill_switch_blocks_new_trades():
    manager = make_manager(max_daily_drawdown_pct=Decimal("0.05"))
    manager.start_of_day(Decimal("10000"))

    # 6% drawdown -> should trip the kill switch
    halted = manager.check_daily_drawdown(Decimal("9400"))
    assert halted is True

    proposal = TradeProposal(
        symbol="BTC/USDT", side="BUY",
        entry_price=Decimal("100"), stop_loss=Decimal("95"), take_profit=Decimal("115"),
    )
    decision = manager.evaluate_trade(proposal, Decimal("9400"), open_positions=[])
    assert not decision.approved
    assert "kill switch" in decision.reason


def test_daily_drawdown_resets_on_new_day():
    manager = make_manager(max_daily_drawdown_pct=Decimal("0.05"))
    manager.start_of_day(Decimal("10000"))
    manager.check_daily_drawdown(Decimal("9000"))
    assert manager.halted_for_day is True

    manager.start_of_day(Decimal("9000"))
    assert manager.halted_for_day is False
    assert manager.check_daily_drawdown(Decimal("8950")) is False
