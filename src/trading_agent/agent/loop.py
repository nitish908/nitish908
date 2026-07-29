"""The live/paper polling loop: fetch data -> generate signal -> risk-check
-> execute -> log. Maintains its own Portfolio (independent of whatever the
adapter/broker reports) so profit-margin accounting is uniform and accurate
across paper mode, live mode, and every adapter -- exchange-reported spot
balances don't carry cost-basis information, but our FIFO ledger does.

The actual per-poll pipeline lives in `step.py::execute_step`, shared with
the stateless HTTP server used for container/serverless deployments.
"""

from __future__ import annotations

import time

from trading_agent.adapters.base import ExchangeAdapter
from trading_agent.execution import OrderExecutor, TradeLogger
from trading_agent.logging_config import get_logger
from trading_agent.portfolio import Portfolio
from trading_agent.risk import RiskManager
from trading_agent.strategies import Strategy

from .step import execute_step

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
        result = execute_step(
            self.adapter, self.strategy, self.risk_manager, self.portfolio,
            self.executor, self.trade_logger, self.symbol, self.timeframe,
            self._fetch_limit, self._current_day,
        )
        self._current_day = result.current_day
        logger.info("%s %s: %s", result.signal, self.symbol, result.reason)

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
