from typing import Type

from .base import Strategy
from .ma_crossover import MACrossoverStrategy
from .rsi_mean_reversion import RSIMeanReversionStrategy
from .macd_strategy import MACDStrategy

STRATEGIES: dict[str, Type[Strategy]] = {
    MACrossoverStrategy.name: MACrossoverStrategy,
    RSIMeanReversionStrategy.name: RSIMeanReversionStrategy,
    MACDStrategy.name: MACDStrategy,
}


def build_strategy(name: str, params: dict | None = None) -> Strategy:
    try:
        cls = STRATEGIES[name]
    except KeyError:
        raise ValueError(f"Unknown strategy '{name}'. Available: {list(STRATEGIES)}")
    return cls(params or {})
