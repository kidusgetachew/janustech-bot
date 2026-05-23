"""
SMCBot — SMC Engine
"""

import requests
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

from config.logger import logger
from config.config import StrategyConfig
from strategy.bias import BiasDetector
from strategy.structure import StructureDetector
from strategy.imbalance import IMBDetector
from strategy.utils import get_equilibrium, is_in_discount, is_in_premium


@dataclass
class TradeSignal:
    symbol: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    confluence_score: int
    bias: str
    reasons: list = field(default_factory=list)
    fvg: dict = field(default_factory=dict)
    order_block: dict = field(default_factory=dict)

    def __str__(self):
        return (
            f"SIGNAL | {self.side.upper()} {self.symbol} | "
            f"Entry: {self.entry_price:.2f} | "
            f"SL: {self.stop_loss:.2f} | "
            f"TP1: {self.take_profit_1:.2f} | "
            f"TP2: {self.take_profit_2:.2f} | "
            f"Confluence: {self.confluence_score}/6"
        )


class SMCEngine:

    def __init__(self, config: StrategyConfig):
        self.config = config
        self.bias_detector = BiasDetector(lookback=config.swing_lookback)
        self.structure_detector = StructureDetector(
            lookback=config.swing_lookback,
            bos_lookback=config.bos_lookback,
        )
        self.imb_detector = IMBDetector(
            fvg_min_size=config.fvg_min_size_pts,
            ob_lookback=config.ob_lookback,
        )
        self._vix_cache = {"value": None, "timestamp": None}

    def is_trending(self, df: pd.DataFrame) -> bool:
        """Check if market is trending vs choppy. Only trade trending markets."""
        if len(df) < 50:
            return True
        ema20 = df["close"].ewm(span=20).mean().iloc[-1]
        ema50 = df["close"].ewm(span=50).mean().iloc[-1]
        spread = abs(ema20 - ema50) / ema50
        return spread > 0.005

    def has_volume_confirmation(self, df: pd.DataFrame) -> bool:
        """Check if latest candle has above average volume."""
        if len(df) < 20:
            return True
        avg_volume = df["volume"].tail(20).mean()
        latest_volume = df["volume"].iloc[-1]
        return latest_volume > avg_volume * 1.1

    def get_vix(self) -> float:
        """Fetch current VIX level. Returns 0 if unavailable."""
        try:
            import time
            now = time.time()
            # Cache VIX for 5 minutes
            if self._vix_cache["value"] and self._vix_cache["timestamp"]:
                if now - self._vix_cache["timestamp"] < 300:
                    return self._vix_cache["value"]

            url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=5)
            data = resp.json()
            vix = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            self._vix_cache = {"value": vix, "timestamp": now}
            return vix
        except Exception:
            return 0.0

    def has_confirmation_candle(self, df: pd.DataFrame, bias: str) -> bool:
        """
        Check if the most recent closed candle confirms the trade direction.
        Bullish: candle closes green (close > open)
        Bearish: candle closes red (close < open)
        """
        if len(df) < 2:
            return True
        last_candle = df.iloc[-2]  # use the last CLOSED candle
        if bias == "bullish":
            return last_candle["close"] > last_candle["open"]
        elif bias == "bearish":
            return last_candle["close"] < last_candle["open"]
        return False

    def analyze(self, symbol, daily_df, h4_df, h1_df, m15_df, m5_df):
        logger.info(f"Running SMC analysis on {symbol}...")
        score = 0
        reasons = []

        bias_result = self.bias_detector.get_bias(daily_df)
        bias = bias_result.get("bias", "neutral")

        if bias == "neutral":
            logger.info(f"{symbol} | Bias neutral — skipping")
            return None

        # Market condition filter
        if not self.is_trending(daily_df):
            logger.info(f"{symbol} | Market choppy — skipping")
            return None

        # Volume confirmation
        if not self.has_volume_confirmation(m15_df):
            logger.info(f"{symbol} | Low volume — skipping")
            return None

        # VIX volatility filter
        vix_max = getattr(self.config, "vix_max", 35.0)
        vix = self.get_vix()
        if vix > 0 and vix > vix_max:
            logger.info(f"{symbol} | VIX too high ({vix:.1f} > {vix_max}) — skipping")
            return None

        # Confirmation candle filter
        require_confirmation = getattr(self.config, "require_confirmation_candle", True)
        if require_confirmation and not self.has_confirmation_candle(m15_df, bias):
            logger.info(f"{symbol} | No confirmation candle — skipping")
            return None

        score += 1
        reasons.append(f"✓ Bias: {bias.upper()}")

        sweep = self.structure_detector.detect_liquidity_sweep(h4_df, bias)
        if sweep.get("detected"):
            score += 1
            reasons.append(f"✓ Sweep: {sweep.get('reason', '')}")
        else:
            reasons.append(f"✗ No sweep: {sweep.get('reason', '')}")

        bos = self.structure_detector.detect_bos(h4_df, bias, sweep)
        if bos.get("detected"):
            score += 1
            reasons.append(f"✓ BoS: {bos.get('reason', '')}")
        else:
            reasons.append(f"✗ No BoS: {bos.get('reason', '')}")

        current_price = m5_df["close"].iloc[-1]
        range_high = h1_df["high"].tail(20).max()
        range_low = h1_df["low"].tail(20).min()

        if bias == "bullish" and is_in_discount(current_price, range_high, range_low):
            score += 1
            reasons.append(f"✓ Price in discount zone")
        elif bias == "bearish" and is_in_premium(current_price, range_high, range_low):
            score += 1
            reasons.append(f"✓ Price in premium zone")
        else:
            reasons.append(f"✗ Price not in correct zone")

        fvg = self.imb_detector.get_nearest_fvg(m15_df, bias)
        if fvg.get("detected"):
            score += 1
            reasons.append(f"✓ FVG: {fvg.get('reason', '')}")
        else:
            reasons.append(f"✗ No FVG")
            fvg = {}

        ob = self.imb_detector.get_nearest_ob(m15_df, bias)
        if ob.get("detected"):
            score += 1
            reasons.append(f"✓ OB: {ob.get('reason', '')}")
        else:
            reasons.append(f"✗ No OB")
            ob = {}

        logger.info(f"{symbol} | Score: {score}/6 | Min: {self.config.confluence_min}")

        if score < self.config.confluence_min:
            logger.info(f"{symbol} | Score too low — no trade")
            return None

        return self._build_signal(symbol, bias, current_price, fvg, ob, bos, score, reasons)

    def _build_signal(self, symbol, bias, current_price, fvg, ob, bos, score, reasons):
        side = "buy" if bias == "bullish" else "sell"

        entry_candidates = []
        if fvg.get("detected"):
            entry_candidates.append(fvg["midpoint"])
        if ob.get("detected"):
            entry_candidates.append(ob["midpoint"])

        entry_price = (
            min(entry_candidates, key=lambda x: abs(x - current_price))
            if entry_candidates else current_price
        )

        if side == "buy":
            stop_loss = ob["bottom"] * 0.999 if ob.get("detected") else entry_price * 0.99
        else:
            stop_loss = ob["top"] * 1.001 if ob.get("detected") else entry_price * 1.01

        risk = abs(entry_price - stop_loss)
        if risk <= 0:
            logger.error(f"{symbol} | Invalid signal — zero risk")
            return None

        if side == "buy":
            tp1 = round(entry_price + risk * 1.5, 2)
            tp2 = round(entry_price + risk * 3.0, 2)
        else:
            tp1 = round(entry_price - risk * 1.5, 2)
            tp2 = round(entry_price - risk * 3.0, 2)

        return TradeSignal(
            symbol=symbol,
            side=side,
            entry_price=round(entry_price, 2),
            stop_loss=round(stop_loss, 2),
            take_profit_1=tp1,
            take_profit_2=tp2,
            confluence_score=score,
            bias=bias,
            reasons=reasons,
            fvg=fvg,
            order_block=ob,
        )

    def get_checklist(self, symbol, daily_df, h4_df, h1_df, m15_df, m5_df) -> dict:
        bias_result = self.bias_detector.get_bias(daily_df)
        bias = bias_result.get("bias", "neutral")
        current_price = m5_df["close"].iloc[-1] if not m5_df.empty else 0

        sweep = self.structure_detector.detect_liquidity_sweep(h4_df, bias)
        bos = self.structure_detector.detect_bos(h4_df, bias, sweep)
        fvg = self.imb_detector.get_nearest_fvg(m15_df, bias) if bias != "neutral" else {}
        ob = self.imb_detector.get_nearest_ob(m15_df, bias) if bias != "neutral" else {}

        range_high = h1_df["high"].tail(20).max() if not h1_df.empty else 0
        range_low = h1_df["low"].tail(20).min() if not h1_df.empty else 0

        if bias == "bullish":
            in_zone = is_in_discount(current_price, range_high, range_low)
        elif bias == "bearish":
            in_zone = is_in_premium(current_price, range_high, range_low)
        else:
            in_zone = False

        score = sum([
            bias != "neutral",
            sweep.get("detected", False),
            bos.get("detected", False),
            in_zone,
            fvg.get("detected", False),
            ob.get("detected", False),
        ])

        return {
            "symbol": symbol,
            "bias": bias,
            "score": score,
            "checks": {
                "daily_bias": {"active": bias != "neutral", "detail": bias_result.get("reason", "")},
                "liquidity_sweep": {"active": sweep.get("detected", False), "detail": sweep.get("reason", "")},
                "bos": {"active": bos.get("detected", False), "detail": bos.get("reason", "")},
                "price_zone": {"active": in_zone, "detail": f"Price: {current_price:.2f}"},
                "fvg": {"active": fvg.get("detected", False), "detail": fvg.get("reason", "")},
                "order_block": {"active": ob.get("detected", False), "detail": ob.get("reason", "")},
            },
        }
