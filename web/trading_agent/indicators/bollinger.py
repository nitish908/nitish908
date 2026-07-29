import pandas as pd

from .moving_average import sma


def bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    if period <= 0:
        raise ValueError("period must be positive")

    middle = sma(series, period)
    std = series.rolling(window=period, min_periods=period).std(ddof=0)
    upper = middle + num_std * std
    lower = middle - num_std * std

    return pd.DataFrame(
        {
            "upper": upper,
            "middle": middle,
            "lower": lower,
        },
        index=series.index,
    )
