"""
SMCBot — Trailing Stop Loss Manager
Locks in profits as price moves in favor of the trade.
"""

from config.logger import logger


class TrailingStopManager:
    """
    Manages trailing stops for open positions.

    How it works:
    - On entry, SL is fixed at the original stop loss
    - As price moves in profit, SL trails behind by a fixed % or R-multiple
    - If price reverses and hits the trailing SL, trade closes at profit
    - The SL only moves in the profitable direction — never backward
    """

    def __init__(self, trail_pct: float = 0.01, activate_at_r: float = 1.0):
        """
        trail_pct: How far behind price the stop trails (e.g. 0.01 = 1%)
        activate_at_r: Only start trailing after reaching this R-multiple (e.g. 1.0 = 1R)
        """
        self.trail_pct = trail_pct
        self.activate_at_r = activate_at_r
        self.active_trails: dict = {}  # symbol -> trail state

    def register_trade(self, order_id: str, symbol: str, side: str, entry: float, original_sl: float):
        """Register a new trade for trailing stop management."""
        risk = abs(entry - original_sl)
        activate_price = entry + (risk * self.activate_at_r) if side == "buy" else entry - (risk * self.activate_at_r)

        self.active_trails[order_id] = {
            "symbol": symbol,
            "side": side,
            "entry": entry,
            "original_sl": original_sl,
            "current_sl": original_sl,
            "best_price": entry,
            "activate_price": activate_price,
            "activated": False,
            "risk": risk,
        }
        logger.info(f"Trailing stop registered | {symbol} | Activates at: {activate_price:.2f}")

    def update(self, order_id: str, current_price: float) -> dict:
        """
        Update trailing stop for a position.
        Returns dict with new_sl and whether to close the trade.
        """
        if order_id not in self.active_trails:
            return {"close": False, "new_sl": None}

        trail = self.active_trails[order_id]
        side = trail["side"]
        current_sl = trail["current_sl"]

        # Check if trailing is activated
        if not trail["activated"]:
            if side == "buy" and current_price >= trail["activate_price"]:
                trail["activated"] = True
                logger.info(f"Trailing stop ACTIVATED | {trail['symbol']} | Price: {current_price:.2f}")
            elif side == "sell" and current_price <= trail["activate_price"]:
                trail["activated"] = True
                logger.info(f"Trailing stop ACTIVATED | {trail['symbol']} | Price: {current_price:.2f}")

        if not trail["activated"]:
            return {"close": False, "new_sl": current_sl}

        # Update trailing stop
        new_sl = current_sl
        if side == "buy":
            # Trail below current price
            trail_level = current_price * (1 - self.trail_pct)
            if trail_level > current_sl:
                new_sl = trail_level
                trail["current_sl"] = new_sl
                trail["best_price"] = max(trail["best_price"], current_price)
                logger.debug(f"Trail updated | {trail['symbol']} | New SL: {new_sl:.2f}")

            # Check if hit
            if current_price <= new_sl:
                logger.info(f"Trailing stop HIT | {trail['symbol']} | Close at: {current_price:.2f}")
                del self.active_trails[order_id]
                return {"close": True, "new_sl": new_sl, "exit_price": current_price}

        else:  # sell
            trail_level = current_price * (1 + self.trail_pct)
            if trail_level < current_sl:
                new_sl = trail_level
                trail["current_sl"] = new_sl
                trail["best_price"] = min(trail["best_price"], current_price)

            if current_price >= new_sl:
                logger.info(f"Trailing stop HIT | {trail['symbol']} | Close at: {current_price:.2f}")
                del self.active_trails[order_id]
                return {"close": True, "new_sl": new_sl, "exit_price": current_price}

        return {"close": False, "new_sl": new_sl}

    def remove(self, order_id: str):
        """Remove a trade from trailing stop management."""
        if order_id in self.active_trails:
            del self.active_trails[order_id]

    def get_all_stops(self) -> dict:
        """Get current stop levels for all active trails."""
        return {
            oid: {
                "symbol": t["symbol"],
                "current_sl": t["current_sl"],
                "activated": t["activated"],
                "best_price": t["best_price"],
            }
            for oid, t in self.active_trails.items()
        }