import numpy as np
import pandas as pd


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI, computed via the standard exponential-average-of-gains/losses method."""
    if period <= 0:
        raise ValueError("period must be positive")

    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))
    # where avg_loss is 0 and avg_gain > 0, RSI is 100; where both are 0, RSI is undefined (NaN)
    result = result.where(avg_loss != 0, np.where(avg_gain == 0, np.nan, 100))
    return pd.Series(result, index=series.index, name="rsi")
