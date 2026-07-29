"""Proves the design used by server.py / the Cloudflare deployment: if
Portfolio and RiskManager are fully serialized to JSON-safe dicts and
rebuilt from scratch between every single poll (simulating a container that
sleeps or restarts between every call), the end result is identical to
running the same sequence of polls with continuous in-memory state. This is
the correctness guarantee the whole persistence layer exists for.
"""

from decimal import Decimal

from trading_agent.adapters import SimulatedAdapter
from trading_agent.agent.step import execute_step
from trading_agent.execution import OrderExecutor, TradeLogger
from trading_agent.portfolio import Portfolio
from trading_agent.risk import RiskConfig, RiskManager
from trading_agent.strategies import MACrossoverStrategy

RISK_CONFIG_KWARGS = dict(
    risk_pct_per_trade=Decimal("0.02"),
    min_risk_reward_ratio=Decimal("1.0"),
    max_open_positions=1,
    max_exposure_pct_per_symbol=Decimal("0.5"),
    max_daily_drawdown_pct=Decimal("0.2"),
)


def _run_continuous(sample_ohlcv_df, tmp_path, n_steps):
    adapter = SimulatedAdapter(sample_ohlcv_df, starting_cash=Decimal("10000"), start_index=60)
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 50})
    risk_manager = RiskManager(RiskConfig(**RISK_CONFIG_KWARGS))
    portfolio = Portfolio(starting_cash=Decimal("10000"))
    trade_logger = TradeLogger(path=tmp_path / "continuous.sqlite3")
    executor = OrderExecutor(adapter, trade_logger, mode="paper")

    current_day = None
    for _ in range(n_steps):
        result = execute_step(
            adapter, strategy, risk_manager, portfolio, executor, trade_logger,
            "TEST/USDT", "1h", 100, current_day,
        )
        current_day = result.current_day

    return portfolio


def _run_with_restart_between_every_step(sample_ohlcv_df, tmp_path, n_steps):
    adapter = SimulatedAdapter(sample_ohlcv_df, starting_cash=Decimal("10000"), start_index=60)
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 50})
    trade_logger = TradeLogger(path=tmp_path / "restarted.sqlite3")
    executor = OrderExecutor(adapter, trade_logger, mode="paper")

    portfolio = Portfolio(starting_cash=Decimal("10000"))
    risk_manager = RiskManager(RiskConfig(**RISK_CONFIG_KWARGS))
    current_day = None

    for _ in range(n_steps):
        result = execute_step(
            adapter, strategy, risk_manager, portfolio, executor, trade_logger,
            "TEST/USDT", "1h", 100, current_day,
        )
        current_day = result.current_day

        # Simulate a container restart: serialize state to JSON-safe dicts,
        # throw away the in-memory objects, and rebuild fresh ones from the
        # serialized state only -- exactly what server.py does between HTTP
        # requests, and what a real container restart would force.
        portfolio_state = portfolio.to_dict()
        risk_state = risk_manager.to_dict()
        current_day_str = current_day.isoformat() if current_day else None

        portfolio = Portfolio.from_dict(portfolio_state)
        risk_manager = RiskManager(RiskConfig(**RISK_CONFIG_KWARGS))
        risk_manager.restore(risk_state)
        from datetime import date
        current_day = date.fromisoformat(current_day_str) if current_day_str else None

    return portfolio


def test_full_serialization_between_every_step_matches_continuous_in_memory(sample_ohlcv_df, tmp_path):
    n_steps = len(sample_ohlcv_df) - 60

    continuous = _run_continuous(sample_ohlcv_df, tmp_path, n_steps)
    restarted = _run_with_restart_between_every_step(sample_ohlcv_df, tmp_path, n_steps)

    assert restarted.cash == continuous.cash
    assert restarted.equity == continuous.equity
    assert restarted.realized_pnl == continuous.realized_pnl
    assert restarted.aggregate_net_margin_pct() == continuous.aggregate_net_margin_pct()
    assert restarted.win_rate() == continuous.win_rate()
    assert len(restarted.closed_trades()) == len(continuous.closed_trades())

    continuous_positions = {p.symbol: (p.quantity, p.avg_cost_basis_per_unit) for p in continuous.open_positions()}
    restarted_positions = {p.symbol: (p.quantity, p.avg_cost_basis_per_unit) for p in restarted.open_positions()}
    assert restarted_positions == continuous_positions

    # Sanity check the scenario actually exercised something meaningful,
    # not just two empty portfolios trivially matching.
    assert len(continuous.closed_trades()) > 0 or len(continuous.open_positions()) > 0


def test_serialization_preserves_daily_kill_switch_across_restart(sample_ohlcv_df, tmp_path):
    """A tighter drawdown limit should still halt trading the same way
    whether or not a 'restart' happens between every poll."""
    tight_kwargs = dict(RISK_CONFIG_KWARGS, max_daily_drawdown_pct=Decimal("0.001"))

    def run_continuous():
        adapter = SimulatedAdapter(sample_ohlcv_df, starting_cash=Decimal("10000"), start_index=60)
        strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 50})
        risk_manager = RiskManager(RiskConfig(**tight_kwargs))
        portfolio = Portfolio(starting_cash=Decimal("10000"))
        trade_logger = TradeLogger(path=tmp_path / "tight_continuous.sqlite3")
        executor = OrderExecutor(adapter, trade_logger, mode="paper")
        current_day = None
        n_steps = len(sample_ohlcv_df) - 60
        for _ in range(n_steps):
            result = execute_step(
                adapter, strategy, risk_manager, portfolio, executor, trade_logger,
                "TEST/USDT", "1h", 100, current_day,
            )
            current_day = result.current_day
        return portfolio, risk_manager

    def run_restarted():
        adapter = SimulatedAdapter(sample_ohlcv_df, starting_cash=Decimal("10000"), start_index=60)
        strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 50})
        trade_logger = TradeLogger(path=tmp_path / "tight_restarted.sqlite3")
        executor = OrderExecutor(adapter, trade_logger, mode="paper")
        portfolio = Portfolio(starting_cash=Decimal("10000"))
        risk_manager = RiskManager(RiskConfig(**tight_kwargs))
        current_day = None
        n_steps = len(sample_ohlcv_df) - 60
        from datetime import date
        for _ in range(n_steps):
            result = execute_step(
                adapter, strategy, risk_manager, portfolio, executor, trade_logger,
                "TEST/USDT", "1h", 100, current_day,
            )
            current_day = result.current_day
            p_state, r_state = portfolio.to_dict(), risk_manager.to_dict()
            cd_str = current_day.isoformat() if current_day else None
            portfolio = Portfolio.from_dict(p_state)
            risk_manager = RiskManager(RiskConfig(**tight_kwargs))
            risk_manager.restore(r_state)
            current_day = date.fromisoformat(cd_str) if cd_str else None
        return portfolio, risk_manager

    continuous_portfolio, continuous_risk = run_continuous()
    restarted_portfolio, restarted_risk = run_restarted()

    assert restarted_risk.halted_for_day == continuous_risk.halted_for_day
    assert restarted_portfolio.equity == continuous_portfolio.equity
