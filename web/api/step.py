"""Vercel Python serverless function: advances the paper agent by exactly
one poll (fetch -> signal -> risk -> execute), against the bundled
SimulatedAdapter fixture data. Fully stateless server-side -- the caller
(the dashboard's browser tab) holds `state` between calls and posts it back
each time, exactly like src/trading_agent/server.py does for the Cloudflare
deployment. There is no server-side database here: state only survives as
long as the browser tab does, so this is an interactive demo of one poll at
a time, not an unattended background bot.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from decimal import Decimal
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_agent.adapters import SimulatedAdapter
from trading_agent.agent.step import execute_step
from trading_agent.backtest import load_ohlcv_csv
from trading_agent.execution import OrderExecutor, TradeLogger
from trading_agent.portfolio import Portfolio
from trading_agent.risk import RiskConfig, RiskManager
from trading_agent.strategies import build_strategy

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_ohlcv.csv"
SYMBOL = "DEMO/USDT"
TIMEFRAME = "1h"
STARTING_CASH = Decimal("10000")
STRATEGY_NAME = "ma_crossover"
STRATEGY_PARAMS = {"fast_period": 10, "slow_period": 50}
DEFAULT_START_INDEX = 60


def _build_risk_manager() -> RiskManager:
    return RiskManager(RiskConfig(
        risk_pct_per_trade=Decimal("0.02"),
        min_risk_reward_ratio=Decimal("1.0"),
        max_open_positions=1,
        max_exposure_pct_per_symbol=Decimal("0.5"),
        max_daily_drawdown_pct=Decimal("0.2"),
    ))


def run_step(state: dict | None) -> dict:
    df = load_ohlcv_csv(DATA_PATH)

    if state:
        portfolio = Portfolio.from_dict(state["portfolio"])
        risk_manager = _build_risk_manager()
        risk_manager.restore(state["risk"])
        current_day = date.fromisoformat(state["current_day"]) if state.get("current_day") else None
        cursor = state.get("cursor", DEFAULT_START_INDEX)
    else:
        portfolio = Portfolio(starting_cash=STARTING_CASH)
        risk_manager = _build_risk_manager()
        current_day = None
        cursor = DEFAULT_START_INDEX

    adapter = SimulatedAdapter(df, starting_cash=STARTING_CASH, start_index=cursor)
    strategy = build_strategy(STRATEGY_NAME, STRATEGY_PARAMS)
    trade_logger = TradeLogger(path="/tmp/trades.sqlite3")
    executor = OrderExecutor(adapter, trade_logger, mode="paper")
    fetch_limit = max(strategy.required_lookback() + 10, 100)

    result = execute_step(
        adapter, strategy, risk_manager, portfolio, executor, trade_logger,
        SYMBOL, TIMEFRAME, fetch_limit, current_day,
    )

    new_state = {
        "portfolio": portfolio.to_dict(),
        "risk": risk_manager.to_dict(),
        "current_day": result.current_day.isoformat() if result.current_day else None,
        "cursor": adapter.cursor,
    }
    order = result.order
    return {
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
    }


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        state_raw = query.get("state", [None])[0]
        state = json.loads(state_raw) if state_raw else None
        self._run(state)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON body"})
            return
        self._run(body.get("state"))

    def _run(self, state: dict | None) -> None:
        try:
            result = run_step(state)
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})
            return
        self._send_json(200, result)
