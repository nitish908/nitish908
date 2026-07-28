import numpy as np
import pandas as pd
import pytest

from trading_agent.indicators import sma, ema, rsi, macd, bollinger_bands


def test_sma_basic():
    s = pd.Series([1, 2, 3, 4, 5])
    result = sma(s, 3)
    assert pd.isna(result.iloc[0])
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == pytest.approx(2.0)
    assert result.iloc[3] == pytest.approx(3.0)
    assert result.iloc[4] == pytest.approx(4.0)


def test_sma_rejects_nonpositive_period():
    with pytest.raises(ValueError):
        sma(pd.Series([1, 2, 3]), 0)


def test_ema_reacts_faster_than_sma_to_recent_move(trending_series):
    e = ema(trending_series, 10)
    s = sma(trending_series, 10)
    # In the middle of the uptrend, EMA (more weight on recent prices) should be >= SMA
    idx = 25
    assert e.iloc[idx] >= s.iloc[idx]


def test_rsi_bounds(trending_series):
    result = rsi(trending_series, period=14)
    valid = result.dropna()
    assert (valid >= 0).all()
    assert (valid <= 100).all()
    # Sustained uptrend should push RSI well above 50 before the reversal
    assert valid.iloc[10] > 50


def test_rsi_all_gains_is_100():
    s = pd.Series(np.linspace(1, 50, 20))
    result = rsi(s, period=14)
    assert result.iloc[-1] == pytest.approx(100.0)


def test_macd_columns_and_crossover(trending_series):
    result = macd(trending_series, fast=5, slow=10, signal=3)
    assert list(result.columns) == ["macd_line", "signal_line", "histogram"]
    # During the uptrend leg the histogram should be positive at some point
    uptrend_hist = result["histogram"].iloc[10:29]
    assert (uptrend_hist.dropna() > 0).any()


def test_macd_rejects_fast_ge_slow():
    with pytest.raises(ValueError):
        macd(pd.Series([1, 2, 3]), fast=10, slow=10)


def test_bollinger_bands_ordering(trending_series):
    result = bollinger_bands(trending_series, period=10, num_std=2.0)
    valid = result.dropna()
    assert (valid["upper"] >= valid["middle"]).all()
    assert (valid["middle"] >= valid["lower"]).all()
