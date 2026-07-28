from decimal import Decimal

from trading_agent.backtest import BacktestEngine
from trading_agent.portfolio import Portfolio
from trading_agent.risk import RiskConfig, RiskManager
from trading_agent.strategies import MACrossoverStrategy


def test_backtest_end_to_end_on_fixture(sample_ohlcv_df):
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 50})
    risk_manager = RiskManager(RiskConfig(
        risk_pct_per_trade=Decimal("0.02"),
        min_risk_reward_ratio=Decimal("1.0"),
        max_open_positions=1,
        max_exposure_pct_per_symbol=Decimal("0.5"),
        max_daily_drawdown_pct=Decimal("0.2"),
    ))
    portfolio = Portfolio(starting_cash=Decimal("10000"))
    engine = BacktestEngine(strategy, risk_manager, portfolio, fee_pct=Decimal("0.001"))

    report = engine.run(sample_ohlcv_df, symbol="TEST/USDT")

    # At least one trade should have either closed (realized) or still be
    # open (unrealized) by the end of the fixture data.
    assert report.num_trades > 0 or len(portfolio.open_positions()) > 0
    assert report.starting_equity == Decimal("10000")
    assert report.ending_equity > 0
    # win_rate should be a valid percentage
    assert Decimal(0) <= report.win_rate_pct <= Decimal(100)
    assert report.max_drawdown_pct >= Decimal(0)
    # report should render without error
    text = report.render()
    assert "Backtest Performance Report" in text
    assert "Net profit margin" in text


def test_backtest_raises_on_insufficient_data(sample_ohlcv_df):
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 50})
    risk_manager = RiskManager(RiskConfig())
    portfolio = Portfolio(starting_cash=Decimal("10000"))
    engine = BacktestEngine(strategy, risk_manager, portfolio)

    short_df = sample_ohlcv_df.iloc[:10]
    try:
        engine.run(short_df)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_daily_drawdown_kill_switch_reduces_trading_in_backtest(sample_ohlcv_df):
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 50})
    # Extremely tight daily drawdown should halt trading almost immediately,
    # resulting in fewer (or equal) trades vs a loose drawdown limit.
    tight_risk = RiskManager(RiskConfig(max_daily_drawdown_pct=Decimal("0.0001")))
    loose_risk = RiskManager(RiskConfig(max_daily_drawdown_pct=Decimal("0.5")))

    tight_portfolio = Portfolio(starting_cash=Decimal("10000"))
    loose_portfolio = Portfolio(starting_cash=Decimal("10000"))

    tight_engine = BacktestEngine(strategy, tight_risk, tight_portfolio)
    loose_engine = BacktestEngine(
        MACrossoverStrategy({"fast_period": 10, "slow_period": 50}), loose_risk, loose_portfolio
    )

    tight_report = tight_engine.run(sample_ohlcv_df, symbol="TEST/USDT")
    loose_report = loose_engine.run(sample_ohlcv_df, symbol="TEST/USDT")

    assert tight_report.num_trades <= loose_report.num_trades
