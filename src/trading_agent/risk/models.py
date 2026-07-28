from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass
class RiskConfig:
    risk_pct_per_trade: Decimal = Decimal("0.01")
    min_risk_reward_ratio: Decimal = Decimal("1.5")
    max_open_positions: int = 5
    max_exposure_pct_per_symbol: Decimal = Decimal("0.25")
    max_daily_drawdown_pct: Decimal = Decimal("0.05")
    default_stop_loss_pct: Decimal = Decimal("0.02")


@dataclass
class TradeProposal:
    symbol: str
    side: Literal["BUY", "SELL"]
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal


@dataclass
class SizingDecision:
    approved: bool
    quantity: Decimal
    reason: str
    risk_amount: Decimal = Decimal(0)
    reward_risk_ratio: Decimal = Decimal(0)
