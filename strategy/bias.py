import pandas as pd
from config.logger import logger
from strategy.utils import find_swing_highs, find_swing_lows, get_equilibrium, is_in_discount, is_in_premium


class BiasDetector:

    def __init__(self, lookback: int = 5):
        self.lookback = lookback

    def get_bias(self, daily_df: pd.DataFrame) -> dict:
        if len(daily_df) < 20:
            return {"bias": "neutral", "strength": 0, "reason": "Insufficient data"}
        try:
            return self._analyze_bias(daily_df)
        except Exception as e:
            logger.error(f"Bias detection error: {e}")
            return {"bias": "neutral", "strength": 0, "reason": str(e)}

    def _analyze_bias(self, df: pd.DataFrame) -> dict:
        score = 0
        reasons = []
        recent = df.tail(20).copy()
        last_close = recent["close"].iloc[-1]

        swing_highs = find_swing_highs(recent, self.lookback)
        swing_lows = find_swing_lows(recent, self.lookback)
        sh_prices = recent["high"][swing_highs].values
        sl_prices = recent["low"][swing_lows].values

        if len(sh_prices) >= 2 and len(sl_prices) >= 2:
            if sh_prices[-1] > sh_prices[-2] and sl_prices[-1] > sl_prices[-2]:
                score += 1
                reasons.append("HH+HL structure")
            elif sh_prices[-1] < sh_prices[-2] and sl_prices[-1] < sl_prices[-2]:
                score -= 1
                reasons.append("LH+LL structure")

        range_high = recent["high"].max()
        range_low = recent["low"].min()

        if is_in_premium(last_close, range_high, range_low):
            score -= 1
            reasons.append("Price in premium")
        elif is_in_discount(last_close, range_high, range_low):
            score += 1
            reasons.append("Price in discount")

        last3 = recent.tail(3)
        bullish_candles = sum(1 for _, c in last3.iterrows() if c["close"] > c["open"])
        if bullish_candles >= 2:
            score += 1
            reasons.append("Bullish momentum")
        else:
            score -= 1
            reasons.append("Bearish momentum")

        eq = get_equilibrium(range_high, range_low)
        if last_close > eq:
            score += 1
            reasons.append("Above midpoint")
        else:
            score -= 1
            reasons.append("Below midpoint")

        if score >= 2:
            bias = "bullish"
        elif score <= -2:
            bias = "bearish"
        else:
            bias = "neutral"

        return {
            "bias": bias,
            "strength": abs(score),
            "score": score,
            "reason": " | ".join(reasons),
            "range_high": range_high,
            "range_low": range_low,
            "equilibrium": eq,
            "last_close": last_close,
        }
