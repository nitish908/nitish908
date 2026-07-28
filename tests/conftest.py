from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "data" / "fixtures"


@pytest.fixture
def trending_series() -> pd.Series:
    """A short, deterministic uptrend-then-downtrend price series for indicator tests."""
    up = np.linspace(100, 150, 30)
    down = np.linspace(150, 110, 30)
    prices = np.concatenate([up, down])
    return pd.Series(prices, name="close")


@pytest.fixture
def sample_ohlcv_path() -> Path:
    return FIXTURES_DIR / "sample_ohlcv.csv"


@pytest.fixture
def sample_ohlcv_df(sample_ohlcv_path) -> pd.DataFrame:
    from trading_agent.backtest.data_loader import load_ohlcv_csv

    return load_ohlcv_csv(sample_ohlcv_path)
