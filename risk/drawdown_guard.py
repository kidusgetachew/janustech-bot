"""
SMCBot — Max Drawdown Hard Stop
Global kill switch that halts all trading if account
drops by a set % in a single day.
"""

from config.logger import logger


class DrawdownGuard:
    """
    Global drawdown protection.
    Monitors account equity every cycle.
    Kills the bot immediately if max intraday drawdown is breached.
    """

    def __init__(self, max_daily_drawdown_pct: float = 0.05, max_total_drawdown_pct: float = 0.10):
        self.max_daily_dd = max_daily_drawdown_pct
        self.max_total_dd = max_total_drawdown_pct

        self.day_start_equity: float = 0.0
        self.peak_equity: float = 0.0
        self.is_killed: bool = False
        self.kill_reason: str = ""
        self.daily_low: float = float("inf")

    def start_day(self, equity: float):
        """Reset daily tracking at start of each trading day."""
        self.day_start_equity = equity
        self.daily_low = equity
        self.is_killed = False
        self.kill_reason = ""
        if equity > self.peak_equity:
            self.peak_equity = equity
        logger.info(f"Drawdown guard reset | Day start equity: ${equity:,.2f} | Peak: ${self.peak_equity:,.2f}")

    def check(self, current_equity: float) -> tuple[bool, str]:
        """
        Check if drawdown limits are breached.
        Returns (kill: bool, reason: str)
        """
        if self.is_killed:
            return True, self.kill_reason

        # Update peak
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        # Update daily low
        if current_equity < self.daily_low:
            self.daily_low = current_equity

        # Check daily drawdown
        if self.day_start_equity > 0:
            daily_dd = (self.day_start_equity - current_equity) / self.day_start_equity
            if daily_dd >= self.max_daily_dd:
                reason = f"Daily drawdown limit hit: -{daily_dd*100:.2f}% (max: -{self.max_daily_dd*100:.1f}%)"
                self._kill(reason)
                return True, reason

        # Check total drawdown from peak
        if self.peak_equity > 0:
            total_dd = (self.peak_equity - current_equity) / self.peak_equity
            if total_dd >= self.max_total_dd:
                reason = f"Total drawdown limit hit: -{total_dd*100:.2f}% from peak (max: -{self.max_total_dd*100:.1f}%)"
                self._kill(reason)
                return True, reason

        return False, ""

    def _kill(self, reason: str):
        """Kill the bot — requires manual reset."""
        self.is_killed = True
        self.kill_reason = reason
        logger.warning(f"DRAWDOWN GUARD TRIGGERED — {reason}")

    def reset(self):
        """Manually reset after a kill — called from UI."""
        self.is_killed = False
        self.kill_reason = ""
        logger.info("Drawdown guard manually reset.")

    def get_status(self) -> dict:
        """Return current drawdown status for UI display."""
        daily_dd = 0.0
        total_dd = 0.0

        if self.day_start_equity > 0:
            daily_dd = (self.day_start_equity - self.daily_low) / self.day_start_equity * 100

        if self.peak_equity > 0:
            total_dd = (self.peak_equity - self.daily_low) / self.peak_equity * 100

        return {
            "is_killed": self.is_killed,
            "kill_reason": self.kill_reason,
            "daily_drawdown_pct": daily_dd,
            "total_drawdown_pct": total_dd,
            "max_daily_pct": self.max_daily_dd * 100,
            "max_total_pct": self.max_total_dd * 100,
            "day_start": self.day_start_equity,
            "peak": self.peak_equity,
        }