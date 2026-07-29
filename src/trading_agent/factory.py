"""Shared construction helpers used by both the CLI (`cli.py`, a
continuously-running process) and the stateless HTTP server (`server.py`,
for container/serverless deployments) so the two entry points build adapters
and risk config identically instead of duplicating the logic.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Optional

from trading_agent.adapters import AlpacaAdapter, CCXTBinanceAdapter, SimulatedAdapter
from trading_agent.backtest import load_ohlcv_csv
from trading_agent.config import AppConfig, ConfigError
from trading_agent.logging_config import get_logger
from trading_agent.risk import RiskConfig
from trading_agent.utils.decimal_utils import D

logger = get_logger(__name__)

DEFAULT_FIXTURE = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures" / "sample_ohlcv.csv"
DEFAULT_STARTING_CASH = Decimal("10000")


def risk_config_from_app_config(app_config: AppConfig) -> RiskConfig:
    r = app_config.risk
    return RiskConfig(
        risk_pct_per_trade=D(r.risk_pct_per_trade),
        min_risk_reward_ratio=D(r.min_risk_reward_ratio),
        max_open_positions=r.max_open_positions,
        max_exposure_pct_per_symbol=D(r.max_exposure_pct_per_symbol),
        max_daily_drawdown_pct=D(r.max_daily_drawdown_pct),
        default_stop_loss_pct=D(r.default_stop_loss_pct),
    )


def build_adapter(app_config: AppConfig, market: str, mode: str, sim_data: Optional[str]):
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
    # simulated broker fed by historical data, so agent runs work out of the
    # box with no exchange/broker account.
    data_path = Path(sim_data) if sim_data else DEFAULT_FIXTURE
    df = load_ohlcv_csv(data_path)
    logger.warning(
        "No API keys configured for %s -- using SimulatedAdapter fed by %s. "
        "Add keys to .env to use a real sandbox/live adapter.",
        market, data_path,
    )
    return SimulatedAdapter(df, starting_cash=DEFAULT_STARTING_CASH, fee_pct=D(app_config.fees.taker_fee_pct)), True
