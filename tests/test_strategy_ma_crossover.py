import numpy as np
import pandas as pd
import pytest

from trading_agent.strategies import Signal, MACrossoverStrategy, RSIMeanReversionStrategy, build_strategy


def make_ohlcv(closes: np.ndarray) -> pd.DataFrame:
    n = len(closes)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="1h")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": closes,
            "high": closes * 1.001,
            "low": closes * 0.999,
            "close": closes,
            "volume": np.full(n, 1000.0),
        }
    )


@pytest.fixture
def uptrend_then_flat_df():
    # Initial decline (fast MA below slow MA), then a sharp uptrend (fast
    # crosses above slow -> BUY), then a decline (fast crosses below -> SELL).
    down1 = np.linspace(150, 100, 20)
    up = np.linspace(100, 200, 40)
    down2 = np.linspace(200, 150, 20)
    closes = np.concatenate([down1, up, down2])
    return make_ohlcv(closes)


def test_ma_crossover_produces_buy_then_sell(uptrend_then_flat_df):
    strategy = MACrossoverStrategy({"fast_period": 5, "slow_period": 15})
    signals = []
    lookback = strategy.required_lookback()
    for i in range(lookback, len(uptrend_then_flat_df) + 1):
        window = uptrend_then_flat_df.iloc[:i]
        result = strategy.generate_signal(window)
        if result.signal != Signal.HOLD:
            signals.append(result.signal)

    assert Signal.BUY in signals
    assert Signal.SELL in signals
    assert signals.index(Signal.BUY) < signals.index(Signal.SELL)


def test_ma_crossover_buy_sets_stop_below_and_target_above_entry(uptrend_then_flat_df):
    strategy = MACrossoverStrategy({"fast_period": 5, "slow_period": 15})
    lookback = strategy.required_lookback()
    for i in range(lookback, len(uptrend_then_flat_df) + 1):
        window = uptrend_then_flat_df.iloc[:i]
        result = strategy.generate_signal(window)
        if result.signal == Signal.BUY:
            entry = window["close"].iloc[-1]
            assert result.stop_loss < entry
            assert result.take_profit > entry
            return
    pytest.fail("expected at least one BUY signal")


def test_ma_crossover_rejects_invalid_periods():
    with pytest.raises(ValueError):
        MACrossoverStrategy({"fast_period": 20, "slow_period": 10})


def test_ma_crossover_hold_on_insufficient_data():
    strategy = MACrossoverStrategy({"fast_period": 5, "slow_period": 15})
    df = make_ohlcv(np.linspace(100, 110, 5))
    result = strategy.generate_signal(df)
    assert result.signal == Signal.HOLD


def test_rsi_mean_reversion_buy_on_oversold_recovery():
    # Sharp drop (oversold) then a bounce back up should trigger a BUY.
    down = np.linspace(150, 90, 20)
    bounce = np.linspace(90, 110, 10)
    closes = np.concatenate([down, bounce])
    df = make_ohlcv(closes)

    strategy = RSIMeanReversionStrategy({"period": 14, "oversold": 30, "overbought": 70})
    signals = []
    lookback = strategy.required_lookback()
    for i in range(lookback, len(df) + 1):
        result = strategy.generate_signal(df.iloc[:i])
        if result.signal != Signal.HOLD:
            signals.append(result.signal)

    assert Signal.BUY in signals


def test_build_strategy_registry():
    strategy = build_strategy("ma_crossover", {"fast_period": 3, "slow_period": 8})
    assert isinstance(strategy, MACrossoverStrategy)

    with pytest.raises(ValueError):
        build_strategy("not_a_real_strategy")
