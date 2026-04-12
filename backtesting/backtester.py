"""
SMCBot — Backtesting Engine (Fixed)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from config.logger import logger
from config.config import StrategyConfig, RiskConfig
from strategy.utils import find_swing_highs, find_swing_lows, get_equilibrium, is_in_discount, is_in_premium
from strategy.imbalance import IMBDetector


@dataclass
class BacktestTrade:
    symbol: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    entry_idx: int
    exit_price: float = 0.0
    exit_idx: int = 0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    result: str = ""
    exit_reason: str = ""
    confluence_score: int = 0
    bars_held: int = 0


@dataclass
class BacktestResult:
    symbol: str
    start_date: str
    end_date: str
    initial_balance: float
    final_balance: float
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_rr: float = 0.0
    sharpe_ratio: float = 0.0
    trades: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)


class Backtester:

    def __init__(self, strategy_config: StrategyConfig, risk_config: RiskConfig, initial_balance: float = 100_000):
        self.strategy_config = strategy_config
        self.risk_config = risk_config
        self.initial_balance = initial_balance
        self.imb_detector = IMBDetector(
            fvg_min_size=strategy_config.fvg_min_size_pts,
            ob_lookback=strategy_config.ob_lookback,
        )

    def _get_bias(self, df: pd.DataFrame) -> str:
        """Simple bias detection — less strict than live trading."""
        if len(df) < 10:
            return "neutral"
        recent = df.tail(20)
        close = recent["close"].iloc[-1]
        high = recent["high"].max()
        low = recent["low"].min()
        eq = get_equilibrium(high, low)

        # Count bullish vs bearish candles in last 5
        last5 = recent.tail(5)
        bulls = sum(1 for _, c in last5.iterrows() if c["close"] > c["open"])

        score = 0
        if close > eq:
            score += 1
        else:
            score -= 1
        if bulls >= 3:
            score += 1
        elif bulls <= 2:
            score -= 1

        # Check if making higher highs
        sh = find_swing_highs(recent, 2)
        sl = find_swing_lows(recent, 2)
        sh_prices = recent["high"][sh].values
        sl_prices = recent["low"][sl].values
        if len(sh_prices) >= 2:
            if sh_prices[-1] > sh_prices[-2]:
                score += 1
            else:
                score -= 1

        if score >= 1:
            return "bullish"
        elif score <= -1:
            return "bearish"
        return "neutral"

    def _check_entry(self, df: pd.DataFrame, bias: str, current_price: float) -> Optional[dict]:
        """Check for FVG or OB entry zone."""
        if bias == "neutral":
            return None

        fvg = self.imb_detector.get_nearest_fvg(df, bias)
        ob = self.imb_detector.get_nearest_ob(df, bias)

        entry_zones = []
        if fvg.get("detected"):
            entry_zones.append(("fvg", fvg))
        if ob.get("detected"):
            entry_zones.append(("ob", ob))

        if not entry_zones:
            return None

        # Find closest zone to current price
        best = min(entry_zones, key=lambda x: abs(x[1]["midpoint"] - current_price))
        zone_type, zone = best

        # Price must be inside or very near the zone
        distance = abs(zone["midpoint"] - current_price)
        zone_size = abs(zone["top"] - zone["bottom"])

        if distance > zone_size * 2:
            return None

        side = "buy" if bias == "bullish" else "sell"

        if side == "buy":
            sl = zone["bottom"] * 0.998
            tp = current_price + (current_price - sl) * 1.5
        else:
            sl = zone["top"] * 1.002
            tp = current_price - (sl - current_price) * 1.5

        return {
            "side": side,
            "entry": current_price,
            "sl": sl,
            "tp": tp,
            "zone_type": zone_type,
        }

    def run(self, symbol: str, daily_df: pd.DataFrame, h4_df: pd.DataFrame, h1_df: pd.DataFrame, m15_df: pd.DataFrame) -> BacktestResult:
        logger.info(f"Backtest start | {symbol} | {len(m15_df)} bars")

        balance = self.initial_balance
        equity_curve = [balance]
        trades = []
        open_trade = None
        warmup = 50

        for i in range(warmup, len(m15_df)):
            candle = m15_df.iloc[i]
            current_price = float(candle["close"])
            high = float(candle["high"])
            low = float(candle["low"])

            # Manage open trade
            if open_trade:
                closed = False
                if open_trade["side"] == "buy":
                    if low <= open_trade["sl"]:
                        open_trade["exit"] = open_trade["sl"]
                        open_trade["reason"] = "sl"
                        closed = True
                    elif high >= open_trade["tp"]:
                        open_trade["exit"] = open_trade["tp"]
                        open_trade["reason"] = "tp1"
                        closed = True
                else:
                    if high >= open_trade["sl"]:
                        open_trade["exit"] = open_trade["sl"]
                        open_trade["reason"] = "sl"
                        closed = True
                    elif low <= open_trade["tp"]:
                        open_trade["exit"] = open_trade["tp"]
                        open_trade["reason"] = "tp1"
                        closed = True

                if closed:
                    entry = open_trade["entry"]
                    exit_p = open_trade["exit"]
                    sl = open_trade["sl"]
                    risk = abs(entry - sl)
                    risk_amount = balance * self.risk_config.risk_per_trade
                    qty = risk_amount / risk if risk > 0 else 0

                    if open_trade["side"] == "buy":
                        raw_pnl = exit_p - entry
                    else:
                        raw_pnl = entry - exit_p

                    pnl = raw_pnl * qty
                    balance += pnl

                    trade = BacktestTrade(
                        symbol=symbol,
                        side=open_trade["side"],
                        entry_price=entry,
                        stop_loss=sl,
                        take_profit_1=open_trade["tp"],
                        entry_idx=open_trade["idx"],
                        exit_price=exit_p,
                        exit_idx=i,
                        pnl=pnl,
                        pnl_pct=(raw_pnl / entry) * 100,
                        result="win" if pnl > 0 else "loss",
                        exit_reason=open_trade["reason"],
                        bars_held=i - open_trade["idx"],
                    )
                    trades.append(trade)
                    equity_curve.append(balance)
                    open_trade = None
                continue

            # Only scan every 3 bars
            if i % 3 != 0:
                continue

            # Get data slices
            current_time = m15_df.index[i]
            m15_slice = m15_df.iloc[max(0, i-60):i+1].copy()
            daily_slice = daily_df[daily_df.index <= current_time].tail(30)

            if len(daily_slice) < 10 or len(m15_slice) < 20:
                continue

            # Get bias from daily
            bias = self._get_bias(daily_slice)
            if bias == "neutral":
                continue

            # Check for entry
            signal = self._check_entry(m15_slice, bias, current_price)
            if signal:
                open_trade = {
                    "side": signal["side"],
                    "entry": signal["entry"],
                    "sl": signal["sl"],
                    "tp": signal["tp"],
                    "idx": i,
                }

        # Calculate results
        return self._calculate_results(symbol, trades, equity_curve, balance, str(m15_df.index[warmup])[:10], str(m15_df.index[-1])[:10])

    def _calculate_results(self, symbol, trades, equity_curve, final_balance, start_date, end_date) -> BacktestResult:
        result = BacktestResult(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_balance=self.initial_balance,
            final_balance=final_balance,
            trades=trades,
            equity_curve=equity_curve,
        )

        if not trades:
            return result

        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]

        result.total_trades = len(trades)
        result.wins = len(wins)
        result.losses = len(losses)
        result.win_rate = len(wins) / len(trades) * 100
        result.total_pnl = sum(t.pnl for t in trades)
        result.total_pnl_pct = (result.total_pnl / self.initial_balance) * 100
        result.final_balance = self.initial_balance + result.total_pnl

        total_profit = sum(t.pnl for t in wins)
        total_loss = abs(sum(t.pnl for t in losses))
        result.profit_factor = total_profit / total_loss if total_loss > 0 else 0.0
        result.avg_win = total_profit / len(wins) if wins else 0
        result.avg_loss = total_loss / len(losses) if losses else 0
        result.avg_rr = result.avg_win / result.avg_loss if result.avg_loss > 0 else 0

        # Max drawdown
        peak = self.initial_balance
        max_dd = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = peak - eq
            if dd > max_dd:
                max_dd = dd
        result.max_drawdown = max_dd
        result.max_drawdown_pct = (max_dd / self.initial_balance) * 100

        # Sharpe
        if len(equity_curve) > 1:
            returns = pd.Series(equity_curve).pct_change().dropna()
            if returns.std() > 0:
                result.sharpe_ratio = (returns.mean() / returns.std()) * (252 ** 0.5)

        return result