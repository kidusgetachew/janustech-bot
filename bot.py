"""
SMCBot — Main Bot Engine
Full trading loop with order monitoring, alerts, and position management.
"""

import time
import threading
from datetime import datetime, timezone

from config.config import BotConfig
from config.logger import logger, get_recent_logs
from execution.alpaca_client import AlpacaClient
from execution.order_monitor import OrderMonitor
from execution.alerts import TelegramAlerter
from data.data_feed import DataFeed
from risk.risk_manager import RiskManager
from risk.trailing_stop import TrailingStopManager
from risk.drawdown_guard import DrawdownGuard
from strategy.smc_engine import SMCEngine


class SMCBot:

    def __init__(self, config: BotConfig):
        self.config = config
        self.is_running = False
        self._thread = None
        self.client = None
        self.data_feed = None
        self.risk_manager = None
        self.smc_engine = None
        self.order_monitor = None
        self.alerter = None
        self.trailing_stop = None
        self.drawdown_guard = None
        self.account_info = {}
        self.open_positions = []
        self.last_cycle_time = ""
        self.error_count = 0
        self.max_errors = 5
        logger.info("PROJECT JANUSTECH initialized.")

    def connect(self, api_key: str, secret_key: str, paper: bool = True):
        self.config.set_api_keys(api_key, secret_key, paper)
        self.client = AlpacaClient(api_key, secret_key, paper)
        ok, msg = self.client.connect()
        if not ok:
            return False, msg

        self.data_feed = DataFeed(self.client, self.config.strategy)
        self.risk_manager = RiskManager(self.config.risk)
        self.smc_engine = SMCEngine(self.config.strategy)
        self.trailing_stop = TrailingStopManager(trail_pct=0.01, activate_at_r=1.0)
        self.drawdown_guard = DrawdownGuard(
            max_daily_drawdown_pct=self.config.risk.max_daily_loss,
            max_total_drawdown_pct=self.config.risk.drawdown_limit,
        )
        self.order_monitor = OrderMonitor(self.client, self.risk_manager)
        self.alerter = TelegramAlerter(
            token=self.config.alerts.telegram_token,
            chat_id=self.config.alerts.telegram_chat_id,
        )

        self.account_info = self.client.get_account()
        if self.account_info:
            balance = self.account_info.get("balance", 0)
            self.risk_manager.start_day(balance)
            self.drawdown_guard.start_day(self.account_info.get("equity", balance))

        logger.info("All modules initialized. Bot ready.")
        return True, msg

    def start(self):
        valid, reason = self.config.validate()
        if not valid:
            return False, reason
        if not self.client or not self.client.connected:
            return False, "Not connected to Alpaca."
        if self.is_running:
            return False, "Bot already running."

        logger.info("Pre-loading market data...")
        self.data_feed.load_all(self.config.markets.symbols)

        self.is_running = True
        self.order_monitor.start()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        mode = "PAPER" if self.config.api.paper_trading else "LIVE"
        self.alerter.bot_started(self.config.markets.symbols, mode)
        logger.info(f"Bot started. Watching: {self.config.markets.symbols}")
        return True, "Bot started."

    def stop(self, reason: str = "User stopped bot"):
        self.is_running = False
        if self.order_monitor:
            self.order_monitor.stop()
        self.alerter.bot_stopped(reason)
        logger.warning(f"Bot stopped: {reason}")

    def emergency_close(self):
        self.stop("Emergency close triggered")
        if self.client and self.client.connected:
            ok, msg = self.client.close_all_positions()
            logger.warning(f"Emergency close: {msg}")
            return ok, msg
        return False, "Not connected"

    def _run_loop(self):
        logger.info("Trading loop started.")
        while self.is_running:
            try:
                self._cycle()
                self.error_count = 0
                time.sleep(30)
            except Exception as e:
                self.error_count += 1
                logger.error(f"Cycle error ({self.error_count}/{self.max_errors}): {e}")
                if self.config.alerts.alert_on_error:
                    self.alerter.error(str(e))
                if self.error_count >= self.max_errors:
                    self.stop(f"Too many errors: {e}")
                    break
                time.sleep(60)
        logger.info("Trading loop ended.")

    def _cycle(self):
        now = datetime.now(timezone.utc)
        self.last_cycle_time = now.strftime("%H:%M:%S UTC")
        self.account_info = self.client.get_account()
        self.open_positions = self.client.get_positions()
        balance = self.account_info.get("balance", 0)
        equity = self.account_info.get("equity", 0)

        # Check drawdown guard
        killed, kill_reason = self.drawdown_guard.check(equity)
        if killed:
            self.stop(kill_reason)
            self.alerter.daily_limit_hit(self.drawdown_guard.get_status()["daily_drawdown_pct"])
            return

        # Check session
        in_session = self.data_feed.is_in_active_session(
            self.config.strategy.sessions,
            self.config.strategy.active_sessions,
        )
        if not in_session:
            logger.debug("Outside active sessions — skipping.")
            return

        # Check risk limits
        allowed, reason = self.risk_manager.check_trade_allowed(balance, equity)
        if not allowed:
            logger.warning(f"Trade blocked: {reason}")
            return

        # Scan symbols
        for symbol in self.config.markets.symbols:
            try:
                self._scan_symbol(symbol, balance)
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")

    def _scan_symbol(self, symbol: str, account_balance: float):
        logger.debug(f"Scanning {symbol}...")
        daily = self.data_feed.get_candles(symbol, self.config.strategy.tf_bias, n=50)
        h4 = self.data_feed.get_candles(symbol, self.config.strategy.tf_structure, n=50)
        h1 = self.data_feed.get_candles(symbol, self.config.strategy.tf_confirmation, n=50)
        m15 = self.data_feed.get_candles(symbol, self.config.strategy.tf_entry, n=50)
        m5 = self.data_feed.get_candles(symbol, self.config.strategy.tf_precision, n=50)

        if any(df.empty for df in [daily, h4, h1, m15, m5]):
            logger.warning(f"Incomplete data for {symbol} — skipping.")
            return

        signal = self.smc_engine.analyze(
            symbol=symbol,
            daily_df=daily,
            h4_df=h4,
            h1_df=h1,
            m15_df=m15,
            m5_df=m5,
        )

        if signal:
            self._execute_signal(signal, account_balance)

    def _execute_signal(self, signal, account_balance: float):
        equity = self.account_info.get("equity", account_balance)
        allowed, reason = self.risk_manager.check_trade_allowed(account_balance, equity)
        if not allowed:
            logger.warning(f"Signal blocked: {reason}")
            return

        qty = self.risk_manager.calculate_position_size(
            account_balance, signal.entry_price, signal.stop_loss
        )
        if qty <= 0:
            logger.error("Position size returned 0 — skipping")
            return

        # Exponential backoff retry
        max_retries = 3
        for attempt in range(max_retries):
            ok, order_id = self.client.place_market_order(
                symbol=signal.symbol,
                qty=qty,
                side=signal.side,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit_1,
            )

            if ok:
                trade = {
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "entry": signal.entry_price,
                    "entry_price": signal.entry_price,
                    "sl": signal.stop_loss,
                    "tp1": signal.take_profit_1,
                    "tp2": signal.take_profit_2,
                    "qty": qty,
                    "order_id": order_id,
                    "confluence": signal.confluence_score,
                    "confluence_score": signal.confluence_score,
                }
                # Register with order monitor for fill confirmation
                self.order_monitor.register_order(order_id, trade)

                # Register trailing stop
                self.trailing_stop.register_trade(
                    order_id=order_id,
                    symbol=signal.symbol,
                    side=signal.side,
                    entry=signal.entry_price,
                    original_sl=signal.stop_loss,
                )

                # Send Telegram alert
                if self.config.alerts.alert_on_entry:
                    self.alerter.trade_opened(
                        symbol=signal.symbol,
                        side=signal.side,
                        entry=signal.entry_price,
                        sl=signal.stop_loss,
                        tp1=signal.take_profit_1,
                        confluence=signal.confluence_score,
                    )
                break
            else:
                wait = 2 ** attempt
                logger.warning(f"Order attempt {attempt+1} failed. Retrying in {wait}s...")
                time.sleep(wait)

        if not ok:
            logger.error(f"Order failed after {max_retries} attempts: {order_id}")
            if self.config.alerts.alert_on_error:
                self.alerter.error(f"Order failed for {signal.symbol}: {order_id}")

    def get_dashboard_data(self) -> dict:
        stats = self.risk_manager.get_stats() if self.risk_manager else {}
        dd_status = self.drawdown_guard.get_status() if self.drawdown_guard else {}
        return {
            "is_running": self.is_running,
            "last_cycle": self.last_cycle_time,
            "account": self.account_info,
            "positions": self.open_positions,
            "stats": stats,
            "drawdown": dd_status,
            "logs": get_recent_logs(50),
            "session": (
                self.data_feed.get_current_session(self.config.strategy.sessions)
                if self.data_feed else "Not connected"
            ),
            "connected": self.client.connected if self.client else False,
        }