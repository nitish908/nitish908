"""The core single-poll pipeline: fetch data -> generate signal -> risk-check
-> execute -> log. Extracted as a free function (rather than living only on
AgentLoop) so it can be driven two ways: continuously by AgentLoop.run_forever()
(self-managed in-memory state), or one poll at a time by `server.py` for a
stateless deployment (e.g. a Cloudflare Container woken by an external
scheduler), where Portfolio/RiskManager state is supplied by the caller and
the updated state is handed back for external persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type
from typing import Optional

from trading_agent.adapters.base import ExchangeAdapter
from trading_agent.adapters.models import OrderResult
from trading_agent.execution import OrderExecutor, TradeLogger
from trading_agent.portfolio import Portfolio
from trading_agent.risk import RiskManager, TradeProposal
from trading_agent.strategies import Signal, Strategy
from trading_agent.utils.decimal_utils import D


@dataclass
class StepResult:
    current_day: Optional[date_type]
    signal: str
    reason: str
    order: Optional[OrderResult] = None


def execute_step(
    adapter: ExchangeAdapter,
    strategy: Strategy,
    risk_manager: RiskManager,
    portfolio: Portfolio,
    executor: OrderExecutor,
    trade_logger: TradeLogger,
    symbol: str,
    timeframe: str,
    fetch_limit: int,
    current_day: Optional[date_type],
) -> StepResult:
    df = adapter.fetch_ohlcv(symbol, timeframe, limit=fetch_limit)
    if len(df) < strategy.required_lookback():
        return StepResult(current_day, Signal.HOLD.value, "insufficient data for lookback")

    bar_timestamp = df["timestamp"].iloc[-1]
    bar_date = bar_timestamp.date() if hasattr(bar_timestamp, "date") else bar_timestamp
    if current_day is None or bar_date != current_day:
        current_day = bar_date
        risk_manager.start_of_day(portfolio.equity)

    price = D(df["close"].iloc[-1])
    portfolio.mark_to_market({symbol: price})
    risk_manager.check_daily_drawdown(portfolio.equity)

    result = strategy.generate_signal(df)
    if result.signal == Signal.HOLD:
        return StepResult(current_day, Signal.HOLD.value, result.reason)

    open_positions = portfolio.open_positions()
    existing_position = next((p for p in open_positions if p.symbol == symbol), None)

    if result.signal == Signal.BUY:
        if existing_position is not None:
            return StepResult(current_day, Signal.BUY.value, "position already open; skipped")

        proposal = TradeProposal(
            symbol=symbol, side="BUY",
            entry_price=price, stop_loss=result.stop_loss, take_profit=result.take_profit,
        )
        existing_exposure = portfolio.exposure_for_symbol(symbol)
        sizing = risk_manager.evaluate_trade(proposal, portfolio.equity, open_positions, existing_exposure)
        if not sizing.approved:
            trade_logger.log_rejection(symbol, "BUY", sizing.reason)
            return StepResult(current_day, Signal.BUY.value, f"rejected: {sizing.reason}")

        order_result = executor.execute(symbol, "BUY", sizing.quantity)
        portfolio.process_fill(order_result.to_fill())
        return StepResult(current_day, Signal.BUY.value, "opened", order=order_result)

    if result.signal == Signal.SELL:
        if existing_position is None:
            return StepResult(current_day, Signal.SELL.value, "no position to close; skipped")

        order_result = executor.execute(symbol, "SELL", existing_position.quantity)
        portfolio.process_fill(order_result.to_fill())
        return StepResult(current_day, Signal.SELL.value, "closed", order=order_result)

    return StepResult(current_day, Signal.HOLD.value, "no signal")
