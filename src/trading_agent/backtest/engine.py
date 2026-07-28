"""Backtesting engine: drives a Strategy + RiskManager + Portfolio directly
over historical OHLCV data, with no exchange/broker adapter involved. This is
the primary way to validate the whole pipeline (signals -> risk rules ->
accurate P&L) without any network access or API credentials.

Long-only spot semantics: a BUY signal opens a new sized position (if one
isn't already open for the symbol); a SELL signal closes the entire existing
position (if any). This mirrors typical spot crypto/stock trading where
short-selling isn't available.
"""

from __future__ import annotations

import math
import statistics
from decimal import Decimal
from uuid import uuid4

import pandas as pd

from trading_agent.portfolio import Fill, Portfolio
from trading_agent.risk import RiskManager, TradeProposal
from trading_agent.strategies import Signal, Strategy
from trading_agent.utils.decimal_utils import D

from .report import PerformanceReport


class BacktestEngine:
    def __init__(
        self,
        strategy: Strategy,
        risk_manager: RiskManager,
        portfolio: Portfolio,
        fee_pct: Decimal = Decimal("0.001"),
    ):
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.portfolio = portfolio
        self.fee_pct = fee_pct

    def run(self, df: pd.DataFrame, symbol: str = "ASSET") -> PerformanceReport:
        lookback = self.strategy.required_lookback()
        if len(df) < lookback:
            raise ValueError(
                f"Not enough bars ({len(df)}) for strategy lookback ({lookback})"
            )

        starting_equity = self.portfolio.equity
        equity_curve: list[Decimal] = []
        peak_equity = starting_equity
        max_drawdown_pct = Decimal(0)
        current_day = None

        for i in range(lookback, len(df) + 1):
            window = df.iloc[:i]
            bar = window.iloc[-1]
            bar_timestamp = bar["timestamp"]
            price = D(bar["close"])

            bar_date = bar_timestamp.date()
            if current_day is None or bar_date != current_day:
                current_day = bar_date
                self.risk_manager.start_of_day(self.portfolio.equity)

            self.portfolio.mark_to_market({symbol: price})
            self.risk_manager.check_daily_drawdown(self.portfolio.equity)

            result = self.strategy.generate_signal(window)
            self._handle_signal(result.signal, result.stop_loss, result.take_profit,
                                 symbol, price, bar_timestamp)

            self.portfolio.mark_to_market({symbol: price})
            equity = self.portfolio.equity
            equity_curve.append(equity)
            peak_equity = max(peak_equity, equity)
            if peak_equity > 0:
                drawdown = (peak_equity - equity) / peak_equity * Decimal(100)
                max_drawdown_pct = max(max_drawdown_pct, drawdown)

        ending_equity = equity_curve[-1] if equity_curve else starting_equity
        total_return_pct = (
            (ending_equity - starting_equity) / starting_equity * Decimal(100)
            if starting_equity
            else Decimal(0)
        )

        return PerformanceReport(
            starting_equity=starting_equity,
            ending_equity=ending_equity,
            total_return_pct=total_return_pct,
            win_rate_pct=self.portfolio.win_rate(),
            max_drawdown_pct=max_drawdown_pct,
            sharpe_like_ratio=_sharpe_like_ratio(equity_curve),
            num_trades=len(self.portfolio.closed_trades()),
            net_profit_margin_pct=self.portfolio.aggregate_net_margin_pct(),
            trades=self.portfolio.closed_trades(),
        )

    def _handle_signal(self, signal, stop_loss, take_profit, symbol, price, timestamp) -> None:
        open_positions = self.portfolio.open_positions()
        existing_position = next((p for p in open_positions if p.symbol == symbol), None)

        if signal == Signal.BUY and existing_position is None:
            proposal = TradeProposal(
                symbol=symbol, side="BUY",
                entry_price=price, stop_loss=stop_loss, take_profit=take_profit,
            )
            existing_exposure = self.portfolio.exposure_for_symbol(symbol)
            sizing = self.risk_manager.evaluate_trade(
                proposal, self.portfolio.equity, open_positions, existing_exposure
            )
            if sizing.approved:
                fee = price * sizing.quantity * self.fee_pct
                fill = Fill(
                    trade_id=str(uuid4()), symbol=symbol, side="BUY",
                    quantity=sizing.quantity, price=price, fee=fee, timestamp=timestamp,
                )
                self.portfolio.process_fill(fill)

        elif signal == Signal.SELL and existing_position is not None:
            fee = price * existing_position.quantity * self.fee_pct
            fill = Fill(
                trade_id=str(uuid4()), symbol=symbol, side="SELL",
                quantity=existing_position.quantity, price=price, fee=fee, timestamp=timestamp,
            )
            self.portfolio.process_fill(fill)


def _sharpe_like_ratio(equity_curve: list[Decimal]) -> float | None:
    if len(equity_curve) < 3:
        return None
    returns = []
    for prev, curr in zip(equity_curve, equity_curve[1:]):
        if prev == 0:
            continue
        returns.append(float((curr - prev) / prev))
    if len(returns) < 2:
        return None
    mean = statistics.mean(returns)
    stdev = statistics.pstdev(returns)
    if stdev == 0:
        return None
    return (mean / stdev) * math.sqrt(len(returns))
