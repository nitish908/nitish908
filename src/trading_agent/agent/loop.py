"""The live/paper polling loop: fetch data -> generate signal -> risk-check
-> execute -> log. Maintains its own Portfolio (independent of whatever the
adapter/broker reports) so profit-margin accounting is uniform and accurate
across paper mode, live mode, and every adapter -- exchange-reported spot
balances don't carry cost-basis information, but our FIFO ledger does.
"""

from __future__ import annotations

import time
from decimal import Decimal

from trading_agent.adapters.base import ExchangeAdapter
from trading_agent.execution import OrderExecutor, TradeLogger
from trading_agent.logging_config import get_logger
from trading_agent.portfolio import Portfolio
from trading_agent.risk import RiskManager, TradeProposal
from trading_agent.strategies import Signal, Strategy
from trading_agent.utils.decimal_utils import D

logger = get_logger(__name__)


class AgentLoop:
    def __init__(
        self,
        adapter: ExchangeAdapter,
        strategy: Strategy,
        risk_manager: RiskManager,
        portfolio: Portfolio,
        executor: OrderExecutor,
        trade_logger: TradeLogger,
        symbol: str,
        timeframe: str,
        poll_interval_seconds: int = 60,
    ):
        self.adapter = adapter
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.portfolio = portfolio
        self.executor = executor
        self.trade_logger = trade_logger
        self.symbol = symbol
        self.timeframe = timeframe
        self.poll_interval_seconds = poll_interval_seconds
        self._current_day = None
        self._fetch_limit = max(strategy.required_lookback() + 10, 100)

    def step(self) -> None:
        df = self.adapter.fetch_ohlcv(self.symbol, self.timeframe, limit=self._fetch_limit)
        if len(df) < self.strategy.required_lookback():
            logger.info("Not enough bars yet (%d) for %s", len(df), self.symbol)
            return

        bar_timestamp = df["timestamp"].iloc[-1]
        bar_date = bar_timestamp.date() if hasattr(bar_timestamp, "date") else bar_timestamp
        if self._current_day is None or bar_date != self._current_day:
            self._current_day = bar_date
            self.risk_manager.start_of_day(self.portfolio.equity)

        price = D(df["close"].iloc[-1])
        self.portfolio.mark_to_market({self.symbol: price})
        self.risk_manager.check_daily_drawdown(self.portfolio.equity)

        result = self.strategy.generate_signal(df)
        if result.signal == Signal.HOLD:
            return

        open_positions = self.portfolio.open_positions()
        existing_position = next((p for p in open_positions if p.symbol == self.symbol), None)

        if result.signal == Signal.BUY:
            if existing_position is not None:
                logger.info("BUY signal for %s but a position is already open; skipping", self.symbol)
                return
            proposal = TradeProposal(
                symbol=self.symbol, side="BUY",
                entry_price=price, stop_loss=result.stop_loss, take_profit=result.take_profit,
            )
            existing_exposure = self.portfolio.exposure_for_symbol(self.symbol)
            sizing = self.risk_manager.evaluate_trade(
                proposal, self.portfolio.equity, open_positions, existing_exposure
            )
            if not sizing.approved:
                logger.info("BUY rejected for %s: %s", self.symbol, sizing.reason)
                self.trade_logger.log_rejection(self.symbol, "BUY", sizing.reason)
                return
            order_result = self.executor.execute(self.symbol, "BUY", sizing.quantity)
            self.portfolio.process_fill(order_result.to_fill())
            logger.info("Opened BUY position: %s x %s @ %s", self.symbol, sizing.quantity, price)

        elif result.signal == Signal.SELL:
            if existing_position is None:
                logger.info("SELL signal for %s but no open position to close; skipping", self.symbol)
                return
            order_result = self.executor.execute(self.symbol, "SELL", existing_position.quantity)
            self.portfolio.process_fill(order_result.to_fill())
            logger.info("Closed position: %s x %s @ %s", self.symbol, existing_position.quantity, price)

    def run_forever(self) -> None:
        logger.info(
            "Starting agent loop for %s (%s) using strategy '%s', polling every %ds",
            self.symbol, self.timeframe, self.strategy.name, self.poll_interval_seconds,
        )
        while True:
            try:
                self.step()
            except Exception:
                logger.exception("Unhandled error in agent loop step; continuing")
            time.sleep(self.poll_interval_seconds)
