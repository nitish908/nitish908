"""Vercel Python serverless function: runs a full backtest (strategy + risk
manager + portfolio over historical OHLCV data) against the bundled
synthetic fixture, with zero network calls and zero credentials -- the same
BacktestEngine used by `trading_agent.cli backtest`.
"""

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_agent.backtest import BacktestEngine, load_ohlcv_csv
from trading_agent.portfolio import Portfolio
from trading_agent.risk import RiskConfig, RiskManager
from trading_agent.strategies import STRATEGIES, build_strategy

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_ohlcv.csv"
STARTING_CASH = Decimal("10000")

DEFAULT_STRATEGY_PARAMS = {
    "ma_crossover": {"fast_period": 10, "slow_period": 50},
    "rsi_mean_reversion": {"period": 14, "oversold": 30, "overbought": 70},
    "macd": {"fast": 12, "slow": 26, "signal": 9},
}


def run_backtest(strategy_name: str) -> dict:
    if strategy_name not in STRATEGIES:
        raise ValueError(f"unknown strategy '{strategy_name}'. Available: {list(STRATEGIES)}")

    strategy = build_strategy(strategy_name, DEFAULT_STRATEGY_PARAMS.get(strategy_name, {}))
    risk_manager = RiskManager(RiskConfig(
        risk_pct_per_trade=Decimal("0.02"),
        min_risk_reward_ratio=Decimal("1.0"),
        max_open_positions=1,
        max_exposure_pct_per_symbol=Decimal("0.5"),
        max_daily_drawdown_pct=Decimal("0.2"),
    ))
    portfolio = Portfolio(starting_cash=STARTING_CASH)
    engine = BacktestEngine(strategy, risk_manager, portfolio, fee_pct=Decimal("0.001"))

    df = load_ohlcv_csv(DATA_PATH)
    report = engine.run(df, symbol="DEMO/USDT")

    return {
        "strategy": strategy_name,
        "starting_equity": str(report.starting_equity),
        "ending_equity": str(report.ending_equity),
        "total_return_pct": str(report.total_return_pct),
        "win_rate_pct": str(report.win_rate_pct),
        "max_drawdown_pct": str(report.max_drawdown_pct),
        "net_profit_margin_pct": str(report.net_profit_margin_pct),
        "sharpe_like_ratio": report.sharpe_like_ratio,
        "num_trades": report.num_trades,
        "equity_curve": [
            {"timestamp": p.timestamp.isoformat(), "equity": str(p.equity)}
            for p in report.equity_curve
        ],
        "trades": [
            {
                "symbol": t.symbol,
                "quantity": str(t.quantity),
                "entry_price": str(t.entry_price),
                "exit_price": str(t.exit_price),
                "realized_pnl": str(t.realized_pnl),
                "net_profit_margin_pct": str(t.net_profit_margin_pct),
                "opened_at": t.opened_at.isoformat(),
                "closed_at": t.closed_at.isoformat(),
            }
            for t in report.trades
        ],
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
        strategy_name = query.get("strategy", ["ma_crossover"])[0]
        self._run(strategy_name)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON body"})
            return
        self._run(body.get("strategy", "ma_crossover"))

    def _run(self, strategy_name: str) -> None:
        try:
            result = run_backtest(strategy_name)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})
            return
        self._send_json(200, result)
