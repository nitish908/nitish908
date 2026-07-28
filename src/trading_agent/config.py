"""Configuration loading: YAML config + .env secrets, validated with pydantic.

`mode: live` is deliberately hard to reach by accident. Reaching a real
adapter requires BOTH `live.confirm_live_trading: true` in the YAML config
AND the `--live-confirm` CLI flag. Either alone is not enough.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class ConfigError(Exception):
    pass


class CryptoMarketConfig(BaseModel):
    enabled: bool = True
    provider: str = "ccxt_binance"
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    sandbox: bool = True


class StockMarketConfig(BaseModel):
    enabled: bool = True
    provider: str = "alpaca"
    symbol: str = "AAPL"
    timeframe: str = "1Hour"
    paper: bool = True


class MarketsConfig(BaseModel):
    crypto: CryptoMarketConfig = Field(default_factory=CryptoMarketConfig)
    stocks: StockMarketConfig = Field(default_factory=StockMarketConfig)


class StrategyConfig(BaseModel):
    name: str = "ma_crossover"
    params: dict = Field(default_factory=dict)


class RiskConfigModel(BaseModel):
    risk_pct_per_trade: float = 0.01
    min_risk_reward_ratio: float = 1.5
    max_open_positions: int = 5
    max_exposure_pct_per_symbol: float = 0.25
    max_daily_drawdown_pct: float = 0.05
    default_stop_loss_pct: float = 0.02


class FeesConfig(BaseModel):
    taker_fee_pct: float = 0.001


class ExecutionConfig(BaseModel):
    poll_interval_seconds: int = 60
    max_retries: int = 3
    log_format: Literal["sqlite", "csv"] = "sqlite"


class LiveConfig(BaseModel):
    confirm_live_trading: bool = False


class AppConfig(BaseModel):
    mode: Literal["paper", "live"] = "paper"
    markets: MarketsConfig = Field(default_factory=MarketsConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    risk: RiskConfigModel = Field(default_factory=RiskConfigModel)
    fees: FeesConfig = Field(default_factory=FeesConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    live: LiveConfig = Field(default_factory=LiveConfig)

    # populated from environment, not the YAML file
    binance_api_key: str | None = None
    binance_api_secret: str | None = None
    alpaca_api_key: str | None = None
    alpaca_api_secret: str | None = None


def load_config(config_path: str | Path, env_path: str | Path | None = None) -> AppConfig:
    config_path = Path(config_path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    if env_path is None:
        env_path = config_path.parent.parent / ".env"
    load_dotenv(dotenv_path=env_path, override=False)

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f) or {}

    config = AppConfig(**raw)
    config.binance_api_key = os.getenv("BINANCE_API_KEY")
    config.binance_api_secret = os.getenv("BINANCE_API_SECRET")
    config.alpaca_api_key = os.getenv("ALPACA_API_KEY")
    config.alpaca_api_secret = os.getenv("ALPACA_API_SECRET")
    return config


def assert_live_trading_allowed(config: AppConfig, cli_live_confirm: bool) -> None:
    """Raise ConfigError unless BOTH guards for live trading are satisfied."""
    if config.mode != "live":
        return
    if not (config.live.confirm_live_trading and cli_live_confirm):
        raise ConfigError(
            "Refusing to start in live mode: requires BOTH "
            "`live.confirm_live_trading: true` in config.yaml AND the "
            "`--live-confirm` CLI flag. This double guard exists to prevent "
            "accidental real-money trading."
        )
