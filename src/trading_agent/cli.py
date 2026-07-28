"""CLI entry point.

`backtest` runs the whole pipeline offline against historical OHLCV data --
no network calls, no credentials needed.

`run` starts the live/paper polling loop. In paper mode with no API keys
configured, it automatically falls back to a zero-network SimulatedAdapter
fed by a bundled (or user-supplied) OHLCV CSV, so the whole agent loop is
demonstrable without any exchange/broker account. Live mode requires BOTH
`live.confirm_live_trading: true` in the config file AND the `--live-confirm`
CLI flag -- a deliberate double guard against accidental real-money trading.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import click

from trading_agent.adapters import AlpacaAdapter, CCXTBinanceAdapter, SimulatedAdapter
from trading_agent.agent import AgentLoop
from trading_agent.backtest import BacktestEngine, load_ohlcv_csv
from trading_agent.config import AppConfig, ConfigError, assert_live_trading_allowed, load_config
from trading_agent.execution import OrderExecutor, TradeLogger
from trading_agent.logging_config import configure_logging, get_logger, warn_live_trading
from trading_agent.portfolio import Portfolio
from trading_agent.risk import RiskConfig, RiskManager
from trading_agent.strategies import STRATEGIES, build_strategy
from trading_agent.utils.decimal_utils import D

logger = get_logger(__name__)

DEFAULT_FIXTURE = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures" / "sample_ohlcv.csv"
DEFAULT_STARTING_CASH = Decimal("10000")


def _risk_config_from_app_config(app_config: AppConfig) -> RiskConfig:
    r = app_config.risk
    return RiskConfig(
        risk_pct_per_trade=D(r.risk_pct_per_trade),
        min_risk_reward_ratio=D(r.min_risk_reward_ratio),
        max_open_positions=r.max_open_positions,
        max_exposure_pct_per_symbol=D(r.max_exposure_pct_per_symbol),
        max_daily_drawdown_pct=D(r.max_daily_drawdown_pct),
        default_stop_loss_pct=D(r.default_stop_loss_pct),
    )


def _build_adapter(app_config: AppConfig, market: str, mode: str, sim_data: str | None):
    """Returns (adapter, using_simulated: bool)."""
    if market == "crypto":
        market_config = app_config.markets.crypto
        has_keys = bool(app_config.binance_api_key and app_config.binance_api_secret)
        if mode == "live":
            if not has_keys:
                raise ConfigError("Live crypto trading requires BINANCE_API_KEY/BINANCE_API_SECRET in .env")
            return CCXTBinanceAdapter(app_config.binance_api_key, app_config.binance_api_secret, sandbox=False), False
        if has_keys and market_config.sandbox:
            return CCXTBinanceAdapter(app_config.binance_api_key, app_config.binance_api_secret, sandbox=True), False
    else:
        market_config = app_config.markets.stocks
        has_keys = bool(app_config.alpaca_api_key and app_config.alpaca_api_secret)
        if mode == "live":
            if not has_keys:
                raise ConfigError("Live stock trading requires ALPACA_API_KEY/ALPACA_API_SECRET in .env")
            return AlpacaAdapter(app_config.alpaca_api_key, app_config.alpaca_api_secret, paper=False), False
        if has_keys:
            return AlpacaAdapter(app_config.alpaca_api_key, app_config.alpaca_api_secret, paper=True), False

    # Paper mode, no real API keys configured: fall back to a zero-network
    # simulated broker fed by historical data, so `run --mode paper` works
    # out of the box with no exchange/broker account.
    data_path = Path(sim_data) if sim_data else DEFAULT_FIXTURE
    df = load_ohlcv_csv(data_path)
    logger.warning(
        "No API keys configured for %s -- using SimulatedAdapter fed by %s. "
        "Add keys to .env to use a real sandbox/live adapter.",
        market, data_path,
    )
    return SimulatedAdapter(df, starting_cash=DEFAULT_STARTING_CASH, fee_pct=D(app_config.fees.taker_fee_pct)), True


@click.group()
def cli():
    pass


@cli.command()
@click.option("--mode", type=click.Choice(["paper", "live"]), default=None,
              help="Overrides the mode in config.yaml. Defaults to whatever config.yaml specifies (paper by default).")
@click.option("--config", "config_path", default="config/config.yaml", show_default=True)
@click.option("--market", type=click.Choice(["crypto", "stocks"]), default="crypto", show_default=True)
@click.option("--live-confirm", is_flag=True, default=False,
              help="Required (in addition to config.live.confirm_live_trading) to actually trade real money.")
@click.option("--sim-data", default=None,
              help="OHLCV CSV to feed the SimulatedAdapter when no real API keys are configured.")
def run(mode, config_path, market, live_confirm, sim_data):
    configure_logging()
    app_config = load_config(config_path)
    app_config.mode = mode or app_config.mode

    try:
        assert_live_trading_allowed(app_config, live_confirm)
        adapter, using_simulated = _build_adapter(app_config, market, app_config.mode, sim_data)
    except ConfigError as exc:
        raise click.ClickException(str(exc))

    if app_config.mode == "live":
        warn_live_trading(logger)

    market_config = app_config.markets.crypto if market == "crypto" else app_config.markets.stocks
    symbol, timeframe = market_config.symbol, market_config.timeframe

    strategy = build_strategy(app_config.strategy.name, app_config.strategy.params)
    risk_manager = RiskManager(_risk_config_from_app_config(app_config))

    starting_cash = DEFAULT_STARTING_CASH
    if not using_simulated:
        try:
            balances = adapter.get_balance()
            if balances:
                starting_cash = next(iter(balances.values()))
        except Exception:
            logger.warning("Could not fetch starting balance from adapter; defaulting to %s", starting_cash)
    portfolio = Portfolio(starting_cash=starting_cash)

    trade_logger = TradeLogger(
        path=f"logs/trades.{'sqlite3' if app_config.execution.log_format == 'sqlite' else 'csv'}",
        log_format=app_config.execution.log_format,
    )
    executor = OrderExecutor(adapter, trade_logger, mode=app_config.mode, max_retries=app_config.execution.max_retries)

    agent_loop = AgentLoop(
        adapter, strategy, risk_manager, portfolio, executor, trade_logger,
        symbol=symbol, timeframe=timeframe,
        poll_interval_seconds=app_config.execution.poll_interval_seconds,
    )
    agent_loop.run_forever()


@cli.command()
@click.option("--data", "data_path", default=str(DEFAULT_FIXTURE), show_default=True,
              help="Path to an OHLCV CSV (columns: timestamp, open, high, low, close, volume).")
@click.option("--strategy", "strategy_name", type=click.Choice(list(STRATEGIES)), default=None,
              help="Defaults to the strategy configured in config.yaml.")
@click.option("--config", "config_path", default="config/config.yaml", show_default=True)
@click.option("--symbol", default="ASSET", show_default=True, help="Label used in the report/logs.")
@click.option("--starting-cash", default="10000", show_default=True)
def backtest(data_path, strategy_name, config_path, symbol, starting_cash):
    app_config = load_config(config_path)
    strategy = build_strategy(strategy_name or app_config.strategy.name, app_config.strategy.params)
    risk_manager = RiskManager(_risk_config_from_app_config(app_config))
    portfolio = Portfolio(starting_cash=Decimal(starting_cash))
    engine = BacktestEngine(strategy, risk_manager, portfolio, fee_pct=D(app_config.fees.taker_fee_pct))

    df = load_ohlcv_csv(data_path)
    report = engine.run(df, symbol=symbol)
    click.echo(report.render())


if __name__ == "__main__":
    cli()
