import pandas as pd
from config.logger import logger
from strategy.utils import is_bullish_candle, is_bearish_candle


class IMBDetector:

    def __init__(self, fvg_min_size: float = 5.0, ob_lookback: int = 20):
        self.fvg_min_size = fvg_min_size
        self.ob_lookback = ob_lookback

    def find_fvgs(self, df: pd.DataFrame, bias: str) -> list:
        fvgs = []
        data = df.tail(50).copy()
        current_price = data["close"].iloc[-1]
        for i in range(2, len(data)):
            c1 = data.iloc[i - 2]
            c2 = data.iloc[i - 1]
            c3 = data.iloc[i]
            if bias == "bullish":
                fvg = self._check_bullish_fvg(c1, c2, c3, current_price)
            elif bias == "bearish":
                fvg = self._check_bearish_fvg(c1, c2, c3, current_price)
            else:
                continue
            if fvg:
                fvg["index"] = data.index[i]
                fvgs.append(fvg)
        fvgs.reverse()
        return fvgs

    def _check_bullish_fvg(self, c1, c2, c3, current_price) -> dict:
        gap_bottom = c1["high"]
        gap_top = c3["low"]
        if gap_top <= gap_bottom:
            return None
        gap_size = gap_top - gap_bottom
        if gap_size < self.fvg_min_size:
            return None
        if current_price > gap_top:
            return None
        return {
            "type": "bullish_fvg",
            "top": round(gap_top, 2),
            "bottom": round(gap_bottom, 2),
            "midpoint": round((gap_top + gap_bottom) / 2, 2),
            "size": round(gap_size, 2),
            "price_inside": gap_bottom <= current_price <= gap_top,
            "reason": f"Bullish FVG: {gap_bottom:.2f} — {gap_top:.2f}",
        }

    def _check_bearish_fvg(self, c1, c2, c3, current_price) -> dict:
        gap_top = c1["low"]
        gap_bottom = c3["high"]
        if gap_bottom >= gap_top:
            return None
        gap_size = gap_top - gap_bottom
        if gap_size < self.fvg_min_size:
            return None
        if current_price < gap_bottom:
            return None
        return {
            "type": "bearish_fvg",
            "top": round(gap_top, 2),
            "bottom": round(gap_bottom, 2),
            "midpoint": round((gap_top + gap_bottom) / 2, 2),
            "size": round(gap_size, 2),
            "price_inside": gap_bottom <= current_price <= gap_top,
            "reason": f"Bearish FVG: {gap_bottom:.2f} — {gap_top:.2f}",
        }

    def get_nearest_fvg(self, df: pd.DataFrame, bias: str) -> dict:
        fvgs = self.find_fvgs(df, bias)
        if not fvgs:
            return {"detected": False, "reason": "No FVGs found"}
        current_price = df["close"].iloc[-1]
        nearest = min(fvgs, key=lambda f: abs(f["midpoint"] - current_price))
        nearest["detected"] = True
        return nearest

    def find_order_blocks(self, df: pd.DataFrame, bias: str) -> list:
        obs = []
        data = df.tail(self.ob_lookback + 10).copy()
        current_price = data["close"].iloc[-1]
        for i in range(1, len(data) - 1):
            candle = data.iloc[i]
            next_candle = data.iloc[i + 1]
            if bias == "bullish":
                ob = self._check_bullish_ob(candle, next_candle, current_price, data.index[i])
            elif bias == "bearish":
                ob = self._check_bearish_ob(candle, next_candle, current_price, data.index[i])
            else:
                continue
            if ob:
                obs.append(ob)
        obs.reverse()
        return obs

    def _check_bullish_ob(self, candle, next_candle, current_price, idx) -> dict:
        if not is_bearish_candle(candle):
            return None
        if not is_bullish_candle(next_candle):
            return None
        next_body = abs(next_candle["close"] - next_candle["open"])
        this_body = abs(candle["close"] - candle["open"])
        if next_body < this_body * 0.5:
            return None
        ob_top = candle["open"]
        ob_bottom = candle["low"]
        if current_price < ob_bottom:
            return None
        return {
            "type": "bullish_ob",
            "top": round(ob_top, 2),
            "bottom": round(ob_bottom, 2),
            "midpoint": round((ob_top + ob_bottom) / 2, 2),
            "index": idx,
            "price_inside": ob_bottom <= current_price <= ob_top,
            "reason": f"Bullish OB: {ob_bottom:.2f} — {ob_top:.2f}",
        }

    def _check_bearish_ob(self, candle, next_candle, current_price, idx) -> dict:
        if not is_bullish_candle(candle):
            return None
        if not is_bearish_candle(next_candle):
            return None
        next_body = abs(next_candle["close"] - next_candle["open"])
        this_body = abs(candle["close"] - candle["open"])
        if next_body < this_body * 0.5:
            return None
        ob_top = candle["high"]
        ob_bottom = candle["close"]
        if current_price > ob_top:
            return None
        return {
            "type": "bearish_ob",
            "top": round(ob_top, 2),
            "bottom": round(ob_bottom, 2),
            "midpoint": round((ob_top + ob_bottom) / 2, 2),
            "index": idx,
            "price_inside": ob_bottom <= current_price <= ob_top,
            "reason": f"Bearish OB: {ob_bottom:.2f} — {ob_top:.2f}",
        }

    def get_nearest_ob(self, df: pd.DataFrame, bias: str) -> dict:
        obs = self.find_order_blocks(df, bias)
        if not obs:
            return {"detected": False, "reason": "No order blocks found"}
        current_price = df["close"].iloc[-1]
        nearest = min(obs, key=lambda o: abs(o["midpoint"] - current_price))
        nearest["detected"] = True
        return nearest
