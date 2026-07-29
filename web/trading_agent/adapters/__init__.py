from .base import ExchangeAdapter
from .models import Order, OrderResult, AdapterError, AdapterTransientError
from .simulated_adapter import SimulatedAdapter

__all__ = [
    "ExchangeAdapter",
    "Order",
    "OrderResult",
    "AdapterError",
    "AdapterTransientError",
    "SimulatedAdapter",
]

# CCXTBinanceAdapter/AlpacaAdapter pull in ccxt/alpaca-py, which are heavy
# and unnecessary for deployments that only ever use SimulatedAdapter (e.g.
# the lightweight Vercel dashboard). Import them lazily so this package
# still works without those dependencies installed.
try:
    from .ccxt_binance_adapter import CCXTBinanceAdapter

    __all__.append("CCXTBinanceAdapter")
except ImportError:
    pass

try:
    from .alpaca_adapter import AlpacaAdapter

    __all__.append("AlpacaAdapter")
except ImportError:
    pass
