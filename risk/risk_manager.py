"""
SMCBot — Risk Manager
Position sizing, daily loss limits, drawdown circuit breaker.
"""

from config.logger import logger
from config.config import RiskConfig


class RiskManager:

    def __init__(self, config: RiskConfig):
        self.config = config
        self.daily_start_balance: float = 0.0
        self.daily_pnl: float = 0.0
        self.open_trade_count: int = 0
        self.is_halted: bool = False
        self.halt_reason: str = ""
        self.trade_history: list = []

    def start_day(self, balance: float):
        self.daily_start_balance = balance
        self.daily_pnl = 0.0
        self.is_halted = False
        self.halt_reason = ""
        logger.info(f"New trading day started. Balance: ${balance:,.2f}")

    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss_price: float,
    ) -> float:
        if entry_price <= 0 or stop_loss_price <= 0:
            logger.error("Invalid prices for position sizing")
            return 0.0
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share == 0:
            logger.error("Entry and stop loss are the same price")
            return 0.0
        risk_amount = account_balance * self.config.risk_per_trade
        shares = float(int(risk_amount / risk_per_share))
        logger.info(
            f"Position size | Balance: ${account_balance:,.2f} | "
            f"Risk: ${risk_amount:.2f} | Entry: {entry_price:.2f} | "
            f"SL: {stop_loss_price:.2f} | Shares: {shares}"
        )
        return max(shares, 1.0)

    def calculate_tp_levels(
        self,
        entry_price: float,
        stop_loss_price: float,
        side: str,
    ) -> tuple[float, float]:
        risk = abs(entry_price - stop_loss_price)
        direction = 1 if side == "buy" else -1
        tp1 = entry_price + (direction * risk * self.config.tp1_r_multiple)
        tp2 = entry_price + (direction * risk * self.config.tp2_r_multiple)
        logger.info(f"TP1: {tp1:.2f} | TP2: {tp2:.2f}")
        return round(tp1, 2), round(tp2, 2)

    def check_trade_allowed(
        self,
        account_balance: float,
        current_equity: float,
    ) -> tuple[bool, str]:
        if self.is_halted:
            return False, f"Bot halted: {self.halt_reason}"
        if self.open_trade_count >= self.config.max_open_trades:
            return False, f"Max open trades reached ({self.open_trade_count}/{self.config.max_open_trades})"
        if self.daily_start_balance > 0:
            daily_loss_pct = (self.daily_start_balance - current_equity) / self.daily_start_balance
            if daily_loss_pct >= self.config.max_daily_loss:
                reason = f"Daily loss limit hit: -{daily_loss_pct*100:.2f}%"
                self._halt(reason)
                return False, reason
        if account_balance > 0:
            drawdown_pct = (account_balance - current_equity) / account_balance
            if drawdown_pct >= self.config.drawdown_limit:
                reason = f"Drawdown limit hit: -{drawdown_pct*100:.2f}%"
                self._halt(reason)
                return False, reason
        return True, "Trade allowed"

    def _halt(self, reason: str):
        self.is_halted = True
        self.halt_reason = reason
        logger.warning(f"BOT HALTED — {reason}")

    def resume(self):
        self.is_halted = False
        self.halt_reason = ""
        logger.info("Bot manually resumed.")

    def on_trade_opened(self, trade: dict):
        self.open_trade_count += 1
        logger.info(f"Trade opened | {trade.get('symbol')} | Open: {self.open_trade_count}")

    def on_trade_closed(self, trade: dict, pnl: float):
        self.open_trade_count = max(0, self.open_trade_count - 1)
        self.daily_pnl += pnl
        trade["pnl"] = pnl
        self.trade_history.append(trade)
        logger.info(f"Trade closed | PnL: ${pnl:.2f} | Daily: ${self.daily_pnl:.2f}")

    def get_stats(self) -> dict:
        if not self.trade_history:
            return {
                "total_trades": 0, "win_rate": 0.0,
                "profit_factor": 0.0, "total_pnl": 0.0,
                "open_trades": self.open_trade_count,
                "is_halted": self.is_halted,
                "halt_reason": self.halt_reason,
            }
        wins = [t for t in self.trade_history if t.get("pnl", 0) > 0]
        losses = [t for t in self.trade_history if t.get("pnl", 0) <= 0]
        total_profit = sum(t["pnl"] for t in wins)
        total_loss = abs(sum(t["pnl"] for t in losses))
        return {
            "total_trades": len(self.trade_history),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(self.trade_history) * 100,
            "profit_factor": total_profit / total_loss if total_loss > 0 else 0.0,
            "total_pnl": sum(t["pnl"] for t in self.trade_history),
            "daily_pnl": self.daily_pnl,
            "open_trades": self.open_trade_count,
            "is_halted": self.is_halted,
            "halt_reason": self.halt_reason,
        }