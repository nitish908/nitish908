"""Stateless HTTP wrapper around a single agent poll, for deployment as a
Cloudflare Container (or any other environment where an external scheduler
drives polling instead of a long-lived Python process).

Contract: `POST /step` takes `{"state": <previously-returned state, or null
on the first call>}`, performs exactly one fetch -> signal -> risk -> execute
cycle, and returns `{"state": <new state>, "signal": ..., "reason": ...,
"equity": ..., "order": ...}`. The caller (e.g. a Cloudflare Durable Object)
is responsible for persisting `state` between calls and passing it back on
the next poll -- that's what lets Portfolio/RiskManager state (open
positions, cost-basis history, the daily kill switch) survive the container
sleeping or restarting between polls, which an in-memory-only design like
`agent/loop.py::AgentLoop` cannot do on a platform that can suspend the
process at any time.

Listens on port 8080 (the port Cloudflare Containers require) using only the
Python standard library, so no extra HTTP framework dependency is needed.
"""

from __future__ import annotations

import json
import os
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from trading_agent.agent.step import execute_step
from trading_agent.config import load_config
from trading_agent.execution import OrderExecutor, TradeLogger
from trading_agent.factory import DEFAULT_STARTING_CASH, build_adapter, risk_config_from_app_config
from trading_agent.logging_config import configure_logging, get_logger
from trading_agent.portfolio import Portfolio
from trading_agent.risk import RiskManager
from trading_agent.strategies import build_strategy

configure_logging()
logger = get_logger(__name__)

CONFIG_PATH = os.environ.get("TRADING_AGENT_CONFIG", "config/config.yaml")
MARKET = os.environ.get("TRADING_AGENT_MARKET", "crypto")
PORT = int(os.environ.get("PORT", "8080"))

# Built once at process startup: adapter/strategy/executor are stateless (or
# own their own external side effects like the SQLite trade log) and don't
# need to survive a restart the way Portfolio/RiskManager do.
_app_config = load_config(CONFIG_PATH)
_adapter, _using_simulated = build_adapter(_app_config, MARKET, _app_config.mode, sim_data=None)
_market_config = _app_config.markets.crypto if MARKET == "crypto" else _app_config.markets.stocks
_symbol, _timeframe = _market_config.symbol, _market_config.timeframe
_strategy = build_strategy(_app_config.strategy.name, _app_config.strategy.params)
_fetch_limit = max(_strategy.required_lookback() + 10, 100)
_trade_logger = TradeLogger(
    path=f"/tmp/trades.{'sqlite3' if _app_config.execution.log_format == 'sqlite' else 'csv'}",
    log_format=_app_config.execution.log_format,
)
_executor = OrderExecutor(_adapter, _trade_logger, mode=_app_config.mode, max_retries=_app_config.execution.max_retries)


def _fresh_portfolio_and_risk() -> tuple[Portfolio, RiskManager]:
    return Portfolio(starting_cash=DEFAULT_STARTING_CASH), RiskManager(risk_config_from_app_config(_app_config))


def _restore_portfolio_and_risk(state: dict) -> tuple[Portfolio, RiskManager, "date | None"]:
    portfolio = Portfolio.from_dict(state["portfolio"])
    risk_manager = RiskManager(risk_config_from_app_config(_app_config))
    risk_manager.restore(state["risk"])
    current_day = date.fromisoformat(state["current_day"]) if state.get("current_day") else None
    return portfolio, risk_manager, current_day


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "symbol": _symbol, "market": MARKET})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/step":
            self._send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON body"})
            return

        state = body.get("state")
        if state:
            portfolio, risk_manager, current_day = _restore_portfolio_and_risk(state)
        else:
            portfolio, risk_manager = _fresh_portfolio_and_risk()
            current_day = None

        try:
            result = execute_step(
                _adapter, _strategy, risk_manager, portfolio, _executor, _trade_logger,
                _symbol, _timeframe, _fetch_limit, current_day,
            )
        except Exception as exc:
            logger.exception("step failed")
            self._send_json(500, {"error": str(exc)})
            return

        new_state = {
            "portfolio": portfolio.to_dict(),
            "risk": risk_manager.to_dict(),
            "current_day": result.current_day.isoformat() if result.current_day else None,
        }
        order = result.order
        self._send_json(200, {
            "state": new_state,
            "signal": result.signal,
            "reason": result.reason,
            "equity": str(portfolio.equity),
            "order": (
                {
                    "order_id": order.order_id,
                    "side": order.side,
                    "quantity": str(order.quantity),
                    "fill_price": str(order.fill_price),
                }
                if order else None
            ),
        })

    def log_message(self, format, *args):  # noqa: A002 (matches BaseHTTPRequestHandler signature)
        logger.info("%s - %s", self.address_string(), format % args)


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    logger.info(
        "Serving agent step endpoint on :%d (symbol=%s, market=%s, mode=%s)",
        PORT, _symbol, MARKET, _app_config.mode,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
