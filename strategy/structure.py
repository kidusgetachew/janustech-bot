import pandas as pd
from config.logger import logger
from strategy.utils import find_swing_highs, find_swing_lows


class StructureDetector:

    def __init__(self, lookback: int = 5, bos_lookback: int = 10):
        self.lookback = lookback
        self.bos_lookback = bos_lookback

    def detect_liquidity_sweep(self, df: pd.DataFrame, bias: str) -> dict:
        if len(df) < self.lookback * 2 + 3:
            return {"detected": False, "reason": "Not enough candles"}
        recent = df.tail(30).copy()
        if bias == "bullish":
            return self._detect_bullish_sweep(recent)
        elif bias == "bearish":
            return self._detect_bearish_sweep(recent)
        return {"detected": False, "reason": "Neutral bias"}

    def _detect_bullish_sweep(self, df: pd.DataFrame) -> dict:
        swing_lows = find_swing_lows(df, self.lookback)
        sl_indices = df.index[swing_lows].tolist()
        if not sl_indices:
            return {"detected": False, "reason": "No swing lows found"}
        last_sl_idx = sl_indices[-1]
        last_sl_price = df.loc[last_sl_idx, "low"]
        after_sl = df[df.index > last_sl_idx].tail(5)
        for idx, candle in after_sl.iterrows():
            if candle["low"] < last_sl_price and candle["close"] > last_sl_price:
                logger.info(f"Bullish sweep detected | Level: {last_sl_price:.2f}")
                return {
                    "detected": True,
                    "type": "bullish_sweep",
                    "swept_level": last_sl_price,
                    "sweep_candle_idx": idx,
                    "sweep_low": candle["low"],
                    "close": candle["close"],
                    "reason": f"Swept sell-side liquidity at {last_sl_price:.2f}",
                }
        return {"detected": False, "reason": "No bullish sweep found"}

    def _detect_bearish_sweep(self, df: pd.DataFrame) -> dict:
        swing_highs = find_swing_highs(df, self.lookback)
        sh_indices = df.index[swing_highs].tolist()
        if not sh_indices:
            return {"detected": False, "reason": "No swing highs found"}
        last_sh_idx = sh_indices[-1]
        last_sh_price = df.loc[last_sh_idx, "high"]
        after_sh = df[df.index > last_sh_idx].tail(5)
        for idx, candle in after_sh.iterrows():
            if candle["high"] > last_sh_price and candle["close"] < last_sh_price:
                logger.info(f"Bearish sweep detected | Level: {last_sh_price:.2f}")
                return {
                    "detected": True,
                    "type": "bearish_sweep",
                    "swept_level": last_sh_price,
                    "sweep_candle_idx": idx,
                    "sweep_high": candle["high"],
                    "close": candle["close"],
                    "reason": f"Swept buy-side liquidity at {last_sh_price:.2f}",
                }
        return {"detected": False, "reason": "No bearish sweep found"}

    def detect_bos(self, df: pd.DataFrame, bias: str, sweep_result: dict) -> dict:
        if not sweep_result.get("detected"):
            return {"detected": False, "reason": "No sweep — BoS skipped"}
        if len(df) < self.bos_lookback:
            return {"detected": False, "reason": "Not enough candles"}
        recent = df.tail(self.bos_lookback * 2).copy()
        if bias == "bullish":
            return self._detect_bullish_bos(recent, sweep_result)
        elif bias == "bearish":
            return self._detect_bearish_bos(recent, sweep_result)
        return {"detected": False, "reason": "Neutral bias"}

    def _detect_bullish_bos(self, df: pd.DataFrame, sweep: dict) -> dict:
        sweep_idx = sweep.get("sweep_candle_idx")
        if sweep_idx is None:
            return {"detected": False, "reason": "No sweep index"}
        pre_sweep = df[df.index <= sweep_idx]
        if len(pre_sweep) < self.lookback * 2:
            return {"detected": False, "reason": "Not enough pre-sweep candles"}
        swing_highs = find_swing_highs(pre_sweep, self.lookback)
        sh_prices = pre_sweep["high"][swing_highs]
        if sh_prices.empty:
            return {"detected": False, "reason": "No swing highs before sweep"}
        last_sh = sh_prices.iloc[-1]
        post_sweep = df[df.index > sweep_idx]
        for idx, candle in post_sweep.iterrows():
            if candle["close"] > last_sh:
                logger.info(f"Bullish BoS confirmed | Broke: {last_sh:.2f}")
                return {
                    "detected": True,
                    "type": "bullish_bos",
                    "broken_level": last_sh,
                    "bos_candle_idx": idx,
                    "close": candle["close"],
                    "reason": f"Bullish BoS above {last_sh:.2f}",
                }
        return {"detected": False, "reason": "No bullish BoS after sweep"}

    def _detect_bearish_bos(self, df: pd.DataFrame, sweep: dict) -> dict:
        sweep_idx = sweep.get("sweep_candle_idx")
        if sweep_idx is None:
            return {"detected": False, "reason": "No sweep index"}
        pre_sweep = df[df.index <= sweep_idx]
        if len(pre_sweep) < self.lookback * 2:
            return {"detected": False, "reason": "Not enough pre-sweep candles"}
        swing_lows = find_swing_lows(pre_sweep, self.lookback)
        sl_prices = pre_sweep["low"][swing_lows]
        if sl_prices.empty:
            return {"detected": False, "reason": "No swing lows before sweep"}
        last_sl = sl_prices.iloc[-1]
        post_sweep = df[df.index > sweep_idx]
        for idx, candle in post_sweep.iterrows():
            if candle["close"] < last_sl:
                logger.info(f"Bearish BoS confirmed | Broke: {last_sl:.2f}")
                return {
                    "detected": True,
                    "type": "bearish_bos",
                    "broken_level": last_sl,
                    "bos_candle_idx": idx,
                    "close": candle["close"],
                    "reason": f"Bearish BoS below {last_sl:.2f}",
                }
        return {"detected": False, "reason": "No bearish BoS after sweep"}
