"""Places orders through an ExchangeAdapter with retry/backoff on transient
errors, and logs every attempt (success or failure) via TradeLogger."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from trading_agent.adapters.base import ExchangeAdapter
from trading_agent.adapters.models import AdapterTransientError, OrderResult

from .trade_logger import TradeLogger


class OrderExecutor:
    def __init__(
        self,
        adapter: ExchangeAdapter,
        trade_logger: TradeLogger,
        mode: str = "paper",
        max_retries: int = 3,
    ):
        self.adapter = adapter
        self.trade_logger = trade_logger
        self.mode = mode
        self.max_retries = max_retries

    def execute(
        self,
        symbol: str,
        side: Literal["BUY", "SELL"],
        quantity: Decimal,
        order_type: Literal["market", "limit"] = "market",
        price: Optional[Decimal] = None,
    ) -> OrderResult:
        try:
            order_result = self._execute_with_retry(symbol, side, quantity, order_type, price)
        except Exception as exc:
            self.trade_logger.log_failure(symbol, side, str(exc))
            raise

        self.trade_logger.log_order(order_result, self.mode)
        return order_result

    def _execute_with_retry(self, symbol, side, quantity, order_type, price) -> OrderResult:
        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(AdapterTransientError),
            reraise=True,
        )
        def _place():
            return self.adapter.place_order(symbol, side, quantity, order_type, price)

        return _place()
