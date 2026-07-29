from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from trading_agent.portfolio.models import RealizedTrade


@dataclass
class EquityPoint:
    timestamp: datetime
    equity: Decimal


@dataclass
class PerformanceReport:
    starting_equity: Decimal
    ending_equity: Decimal
    total_return_pct: Decimal
    win_rate_pct: Decimal
    max_drawdown_pct: Decimal
    sharpe_like_ratio: Optional[float]
    num_trades: int
    net_profit_margin_pct: Decimal
    trades: list[RealizedTrade] = field(default_factory=list)
    equity_curve: list[EquityPoint] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            "=== Backtest Performance Report ===",
            f"Starting equity:        {self.starting_equity:.2f}",
            f"Ending equity:          {self.ending_equity:.2f}",
            f"Total return:           {self.total_return_pct:.2f}%",
            f"Number of trades:       {self.num_trades}",
            f"Win rate:               {self.win_rate_pct:.2f}%",
            f"Max drawdown:           {self.max_drawdown_pct:.2f}%",
            f"Net profit margin:      {self.net_profit_margin_pct:.2f}%",
            f"Sharpe-like ratio:      "
            + (f"{self.sharpe_like_ratio:.2f}" if self.sharpe_like_ratio is not None else "n/a"),
        ]
        return "\n".join(lines)
