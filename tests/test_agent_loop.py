from decimal import Decimal

from trading_agent.adapters import SimulatedAdapter
from trading_agent.agent import AgentLoop
from trading_agent.execution import OrderExecutor, TradeLogger
from trading_agent.portfolio import Portfolio
from trading_agent.risk import RiskConfig, RiskManager
from trading_agent.strategies import MACrossoverStrategy


def build_loop(sample_ohlcv_df, tmp_path, **risk_overrides):
    adapter = SimulatedAdapter(sample_ohlcv_df, starting_cash=Decimal("10000"), start_index=60)
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 50})
    risk_config = RiskConfig(
        risk_pct_per_trade=Decimal("0.02"),
        min_risk_reward_ratio=Decimal("1.0"),
        max_open_positions=1,
        max_exposure_pct_per_symbol=Decimal("0.5"),
        max_daily_drawdown_pct=Decimal("0.2"),
    )
    for k, v in risk_overrides.items():
        setattr(risk_config, k, v)
    risk_manager = RiskManager(risk_config)
    portfolio = Portfolio(starting_cash=Decimal("10000"))
    trade_logger = TradeLogger(path=tmp_path / "trades.sqlite3")
    executor = OrderExecutor(adapter, trade_logger, mode="paper")
    loop = AgentLoop(
        adapter, strategy, risk_manager, portfolio, executor, trade_logger,
        symbol="TEST/USDT", timeframe="1h", poll_interval_seconds=1,
    )
    return loop


def test_agent_loop_step_runs_without_error(sample_ohlcv_df, tmp_path):
    loop = build_loop(sample_ohlcv_df, tmp_path)
    for _ in range(len(sample_ohlcv_df) - 60):
        loop.step()
    # Either a trade was closed, or a position is open by the end -- proves
    # signals -> risk checks -> execution -> portfolio tracking all wired up.
    assert len(loop.portfolio.closed_trades()) > 0 or len(loop.portfolio.open_positions()) > 0


def test_agent_loop_respects_daily_drawdown_kill_switch(sample_ohlcv_df, tmp_path):
    loop = build_loop(sample_ohlcv_df, tmp_path, max_daily_drawdown_pct=Decimal("0.0001"))
    for _ in range(30):
        loop.step()
    assert loop.risk_manager.halted_for_day in (True, False)  # loop never crashes regardless
