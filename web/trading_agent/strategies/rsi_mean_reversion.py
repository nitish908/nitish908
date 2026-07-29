from __future__ import annotations

from decimal import Decimal

import pandas as pd

from trading_agent.indicators import rsi
from trading_agent.utils.decimal_utils import D

from .base import Signal, Strategy, StrategyResult


class RSIMeanReversionStrategy(Strategy):
    """BUY when RSI crosses back up through the oversold threshold (reversal
    out of an oversold dip), SELL when it crosses back down through the
    overbought threshold (reversal out of an overbought spike).
    """

    name = "rsi_mean_reversion"

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.period = int(self.params.get("period", 14))
        self.oversold = D(self.params.get("oversold", 30))
        self.overbought = D(self.params.get("overbought", 70))
        self.stop_loss_pct = D(self.params.get("stop_loss_pct", 0.02))
        self.risk_reward_ratio = D(self.params.get("risk_reward_ratio", 1.5))

    def required_lookback(self) -> int:
        return self.period + 2

    def generate_signal(self, ohlcv: pd.DataFrame) -> StrategyResult:
        if len(ohlcv) < self.required_lookback():
            return StrategyResult(Signal.HOLD, "insufficient data for lookback")

        close = ohlcv["close"]
        r = rsi(close, self.period)

        if pd.isna(r.iloc[-1]) or pd.isna(r.iloc[-2]):
            return StrategyResult(Signal.HOLD, "RSI not yet available")

        prev_rsi = D(r.iloc[-2])
        curr_rsi = D(r.iloc[-1])
        entry_price = D(close.iloc[-1])

        if prev_rsi <= self.oversold < curr_rsi:
            stop_loss = entry_price * (Decimal(1) - self.stop_loss_pct)
            stop_distance = entry_price - stop_loss
            take_profit = entry_price + stop_distance * self.risk_reward_ratio
            return StrategyResult(
                Signal.BUY,
                f"RSI crossed back above oversold threshold ({self.oversold})",
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

        if prev_rsi >= self.overbought > curr_rsi:
            stop_loss = entry_price * (Decimal(1) + self.stop_loss_pct)
            stop_distance = stop_loss - entry_price
            take_profit = entry_price - stop_distance * self.risk_reward_ratio
            return StrategyResult(
                Signal.SELL,
                f"RSI crossed back below overbought threshold ({self.overbought})",
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

        return StrategyResult(Signal.HOLD, "no RSI reversal")
