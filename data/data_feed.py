"""
SMCBot — Data Feed
Fetches and caches multi-timeframe OHLCV data.
"""

import pandas as pd
from datetime import datetime, timezone
from typing import Optional

from config.logger import logger
from config.config import StrategyConfig
from execution.alpaca_client import AlpacaClient


class DataFeed:

    def __init__(self, client: AlpacaClient, config: StrategyConfig):
        self.client = client
        self.config = config
        self._cache: dict[str, dict[str, pd.DataFrame]] = {}
        self._last_refresh: dict[str, datetime] = {}
        self._refresh_intervals = {
            "1Day":  3600,
            "4Hour": 900,
            "1Hour": 300,
            "15Min": 60,
            "5Min":  30,
        }

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        cache_key = f"{symbol}_{timeframe}"
        now = datetime.now(timezone.utc)

        if not force_refresh and cache_key in self._last_refresh:
            elapsed = (now - self._last_refresh[cache_key]).seconds
            interval = self._refresh_intervals.get(timeframe, 60)
            if elapsed < interval:
                return self._cache.get(symbol, {}).get(timeframe, pd.DataFrame())

        lookback = self._get_lookback_days(timeframe)
        df = self.client.get_bars(symbol, timeframe, lookback_days=lookback)

        if not df.empty:
            if symbol not in self._cache:
                self._cache[symbol] = {}
            self._cache[symbol][timeframe] = df
            self._last_refresh[cache_key] = now
            logger.debug(f"Data refreshed: {symbol} {timeframe} ({len(df)} bars)")

        return df

    def _get_lookback_days(self, timeframe: str) -> int:
        return {
            "1Day":  365,
            "4Hour": 120,
            "1Hour": 60,
            "15Min": 30,
            "5Min":  14,
        }.get(timeframe, 30)

    def load_all(self, symbols: list[str]) -> bool:
        timeframes = [
            self.config.tf_bias,
            self.config.tf_structure,
            self.config.tf_confirmation,
            self.config.tf_entry,
            self.config.tf_precision,
        ]
        success = True
        for symbol in symbols:
            for tf in timeframes:
                df = self.get_bars(symbol, tf, force_refresh=True)
                if df.empty:
                    logger.warning(f"No data loaded for {symbol} {tf}")
                    success = False
                else:
                    logger.info(f"Loaded {len(df)} bars | {symbol} {tf}")
        return success

    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[pd.Series]:
        df = self.get_bars(symbol, timeframe)
        if df.empty:
            return None
        return df.iloc[-1]

    def get_candles(self, symbol: str, timeframe: str, n: int = 50) -> pd.DataFrame:
        df = self.get_bars(symbol, timeframe)
        if df.empty:
            return pd.DataFrame()
        return df.tail(n).copy()

    def get_current_price(self, symbol: str) -> float:
        candle = self.get_latest_candle(symbol, "5Min")
        if candle is not None:
            return float(candle["close"])
        return 0.0

    def is_in_active_session(self, sessions_config: dict, active_sessions: list) -> bool:
        now_hour = datetime.now(timezone.utc).hour
        for session_name in active_sessions:
            session = sessions_config.get(session_name)
            if not session:
                continue
            if session["start"] <= now_hour < session["end"]:
                logger.debug(f"In active session: {session_name}")
                return True
        logger.debug(f"Outside active sessions. UTC hour: {now_hour}")
        return False

    def get_current_session(self, sessions_config: dict) -> str:
        now_hour = datetime.now(timezone.utc).hour
        for name, times in sessions_config.items():
            if times["start"] <= now_hour < times["end"]:
                return name.replace("_", " ").title()
        return "Off Hours"

    def clear_cache(self):
        self._cache.clear()
        self._last_refresh.clear()
        logger.info("Data cache cleared.")