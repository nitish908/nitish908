"""Risk management: position sizing, risk:reward gating, exposure caps, and
a daily-drawdown kill switch. Every rule is a hard reject -- there is no
"soft" override; a rejected trade is simply not sized/executed.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from trading_agent.portfolio.models import Position
from trading_agent.utils.decimal_utils import D, quantize_qty_down

from .models import RiskConfig, SizingDecision, TradeProposal


class RiskManager:
    def __init__(self, config: RiskConfig):
        self.config = config
        self.day_start_equity: Decimal | None = None
        self.halted_for_day: bool = False

    def start_of_day(self, equity: Decimal) -> None:
        """Reset the daily kill switch. Call once per UTC day, e.g. when the
        agent loop / backtest engine detects a date rollover."""
        self.day_start_equity = equity
        self.halted_for_day = False

    def check_daily_drawdown(self, current_equity: Decimal) -> bool:
        """Update and return the kill-switch state given the latest equity."""
        if self.day_start_equity is None:
            self.start_of_day(current_equity)
            return self.halted_for_day

        if self.day_start_equity == 0:
            return self.halted_for_day

        drawdown_pct = (self.day_start_equity - current_equity) / self.day_start_equity
        if drawdown_pct >= self.config.max_daily_drawdown_pct:
            self.halted_for_day = True
        return self.halted_for_day

    def evaluate_trade(
        self,
        proposal: TradeProposal,
        equity: Decimal,
        open_positions: Iterable[Position],
        existing_symbol_exposure: Decimal = Decimal(0),
    ) -> SizingDecision:
        open_positions = list(open_positions)

        if self.halted_for_day:
            return SizingDecision(False, Decimal(0), "daily drawdown kill switch is active")

        stop_distance = abs(proposal.entry_price - proposal.stop_loss)
        reward = abs(proposal.take_profit - proposal.entry_price)

        if stop_distance <= 0:
            return SizingDecision(False, Decimal(0), "stop-loss distance must be positive")

        reward_risk_ratio = reward / stop_distance
        if reward_risk_ratio < self.config.min_risk_reward_ratio:
            return SizingDecision(
                False, Decimal(0),
                f"reward:risk ratio {reward_risk_ratio:.2f} below minimum "
                f"{self.config.min_risk_reward_ratio}",
                reward_risk_ratio=reward_risk_ratio,
            )

        already_open_symbols = {p.symbol for p in open_positions}
        if (
            len(open_positions) >= self.config.max_open_positions
            and proposal.symbol not in already_open_symbols
        ):
            return SizingDecision(
                False, Decimal(0),
                f"max open positions ({self.config.max_open_positions}) reached",
                reward_risk_ratio=reward_risk_ratio,
            )

        risk_amount = equity * self.config.risk_pct_per_trade
        raw_qty = risk_amount / stop_distance

        max_position_value = equity * self.config.max_exposure_pct_per_symbol
        remaining_exposure_budget = max_position_value - existing_symbol_exposure
        qty_by_exposure = (
            remaining_exposure_budget / proposal.entry_price
            if remaining_exposure_budget > 0
            else Decimal(0)
        )

        quantity = min(raw_qty, qty_by_exposure)
        quantity = quantize_qty_down(quantity)

        if quantity <= 0:
            return SizingDecision(
                False, Decimal(0),
                "sized quantity is zero after applying exposure cap",
                risk_amount=risk_amount,
                reward_risk_ratio=reward_risk_ratio,
            )

        return SizingDecision(
            approved=True,
            quantity=quantity,
            reason="approved",
            risk_amount=risk_amount,
            reward_risk_ratio=reward_risk_ratio,
        )

    def to_dict(self) -> dict:
        """JSON-safe snapshot of the daily kill-switch state, for persisting
        across process restarts (e.g. a Cloudflare Container that sleeps
        between polls). RiskConfig itself is not included -- it comes from
        static app config, not from mutable runtime state."""
        return {
            "day_start_equity": str(self.day_start_equity) if self.day_start_equity is not None else None,
            "halted_for_day": self.halted_for_day,
        }

    def restore(self, data: dict) -> None:
        """Restore kill-switch state onto an already-constructed RiskManager
        (which needs its RiskConfig from static app config first)."""
        day_start_equity = data.get("day_start_equity")
        self.day_start_equity = D(day_start_equity) if day_start_equity is not None else None
        self.halted_for_day = bool(data.get("halted_for_day", False))
