"""
SMCBot — Strategy Utilities
"""

import pandas as pd
import numpy as np


def find_swing_highs(df: pd.DataFrame, lookback: int = 5) -> pd.Series:
    highs = df["high"]
    swing_highs = pd.Series(False, index=df.index)
    for i in range(lookback, len(df) - lookback):
        window_left = highs.iloc[i - lookback:i]
        window_right = highs.iloc[i + 1:i + lookback + 1]
        if highs.iloc[i] > window_left.max() and highs.iloc[i] > window_right.max():
            swing_highs.iloc[i] = True
    return swing_highs


def find_swing_lows(df: pd.DataFrame, lookback: int = 5) -> pd.Series:
    lows = df["low"]
    swing_lows = pd.Series(False, index=df.index)
    for i in range(lookback, len(df) - lookback):
        window_left = lows.iloc[i - lookback:i]
        window_right = lows.iloc[i + 1:i + lookback + 1]
        if lows.iloc[i] < window_left.min() and lows.iloc[i] < window_right.min():
            swing_lows.iloc[i] = True
    return swing_lows


def is_bullish_candle(candle: pd.Series) -> bool:
    return candle["close"] > candle["open"]


def is_bearish_candle(candle: pd.Series) -> bool:
    return candle["close"] < candle["open"]


def candle_body_size(candle: pd.Series) -> float:
    return abs(candle["close"] - candle["open"])


def candle_range(candle: pd.Series) -> float:
    return candle["high"] - candle["low"]


def get_equilibrium(high: float, low: float) -> float:
    return (high + low) / 2


def is_in_discount(price: float, range_high: float, range_low: float) -> bool:
    eq = get_equilibrium(range_high, range_low)
    return price < eq


def is_in_premium(price: float, range_high: float, range_low: float) -> bool:
    eq = get_equilibrium(range_high, range_low)
    return price > eq


def get_recent_high(df: pd.DataFrame, n: int = 20) -> float:
    return df["high"].tail(n).max()


def get_recent_low(df: pd.DataFrame, n: int = 20) -> float:
    return df["low"].tail(n).min()
