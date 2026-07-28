from __future__ import annotations

from decimal import Decimal

import pandas as pd

from trading_agent.indicators import macd
from trading_agent.utils.decimal_utils import D

from .base import Signal, Strategy, StrategyResult


class MACDStrategy(Strategy):
    """BUY when the MACD line crosses above its signal line, SELL when it
    crosses below."""

    name = "macd"

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.fast = int(self.params.get("fast", 12))
        self.slow = int(self.params.get("slow", 26))
        self.signal_period = int(self.params.get("signal", 9))
        self.stop_loss_pct = D(self.params.get("stop_loss_pct", 0.02))
        self.risk_reward_ratio = D(self.params.get("risk_reward_ratio", 1.5))

    def required_lookback(self) -> int:
        return self.slow + self.signal_period + 1

    def generate_signal(self, ohlcv: pd.DataFrame) -> StrategyResult:
        if len(ohlcv) < self.required_lookback():
            return StrategyResult(Signal.HOLD, "insufficient data for lookback")

        close = ohlcv["close"]
        result = macd(close, self.fast, self.slow, self.signal_period)

        if result["histogram"].iloc[-2:].isna().any():
            return StrategyResult(Signal.HOLD, "MACD not yet available")

        prev_hist = result["histogram"].iloc[-2]
        curr_hist = result["histogram"].iloc[-1]
        entry_price = D(close.iloc[-1])

        if prev_hist <= 0 and curr_hist > 0:
            stop_loss = entry_price * (Decimal(1) - self.stop_loss_pct)
            stop_distance = entry_price - stop_loss
            take_profit = entry_price + stop_distance * self.risk_reward_ratio
            return StrategyResult(
                Signal.BUY, "MACD line crossed above signal line",
                stop_loss=stop_loss, take_profit=take_profit,
            )

        if prev_hist >= 0 and curr_hist < 0:
            stop_loss = entry_price * (Decimal(1) + self.stop_loss_pct)
            stop_distance = stop_loss - entry_price
            take_profit = entry_price - stop_distance * self.risk_reward_ratio
            return StrategyResult(
                Signal.SELL, "MACD line crossed below signal line",
                stop_loss=stop_loss, take_profit=take_profit,
            )

        return StrategyResult(Signal.HOLD, "no MACD crossover")
