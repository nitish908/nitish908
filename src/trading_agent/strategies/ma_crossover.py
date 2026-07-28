from __future__ import annotations

from decimal import Decimal

import pandas as pd

from trading_agent.indicators import sma
from trading_agent.utils.decimal_utils import D

from .base import Signal, Strategy, StrategyResult


class MACrossoverStrategy(Strategy):
    """Golden/death cross: BUY when the fast MA crosses above the slow MA,
    SELL when it crosses below. Stop-loss/take-profit are derived from a
    fixed percentage of entry price and a minimum risk:reward ratio, since
    the crossover itself doesn't imply a natural stop level.
    """

    name = "ma_crossover"

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.fast_period = int(self.params.get("fast_period", 10))
        self.slow_period = int(self.params.get("slow_period", 50))
        self.stop_loss_pct = D(self.params.get("stop_loss_pct", 0.02))
        self.risk_reward_ratio = D(self.params.get("risk_reward_ratio", 1.5))
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period")

    def required_lookback(self) -> int:
        return self.slow_period + 1

    def generate_signal(self, ohlcv: pd.DataFrame) -> StrategyResult:
        if len(ohlcv) < self.required_lookback():
            return StrategyResult(Signal.HOLD, "insufficient data for lookback")

        close = ohlcv["close"]
        fast = sma(close, self.fast_period)
        slow = sma(close, self.slow_period)

        if pd.isna(fast.iloc[-1]) or pd.isna(slow.iloc[-1]) or pd.isna(fast.iloc[-2]) or pd.isna(slow.iloc[-2]):
            return StrategyResult(Signal.HOLD, "indicators not yet available")

        prev_diff = fast.iloc[-2] - slow.iloc[-2]
        curr_diff = fast.iloc[-1] - slow.iloc[-1]
        entry_price = D(close.iloc[-1])

        if prev_diff <= 0 and curr_diff > 0:
            stop_loss = entry_price * (Decimal(1) - self.stop_loss_pct)
            stop_distance = entry_price - stop_loss
            take_profit = entry_price + stop_distance * self.risk_reward_ratio
            return StrategyResult(
                Signal.BUY,
                f"fast SMA({self.fast_period}) crossed above slow SMA({self.slow_period})",
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

        if prev_diff >= 0 and curr_diff < 0:
            stop_loss = entry_price * (Decimal(1) + self.stop_loss_pct)
            stop_distance = stop_loss - entry_price
            take_profit = entry_price - stop_distance * self.risk_reward_ratio
            return StrategyResult(
                Signal.SELL,
                f"fast SMA({self.fast_period}) crossed below slow SMA({self.slow_period})",
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

        return StrategyResult(Signal.HOLD, "no crossover")
