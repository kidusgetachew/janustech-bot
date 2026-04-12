"""
SMCBot — Telegram Alerts
Sends instant notifications for trades, errors, daily limits.
"""

import requests
from config.logger import logger


class TelegramAlerter:

    def __init__(self, token: str = "", chat_id: str = ""):
        self.token = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)

    def send(self, message: str) -> bool:
        if not self.enabled:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
            }, timeout=5)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Telegram alert failed: {e}")
            return False

    def trade_opened(self, symbol: str, side: str, entry: float, sl: float, tp1: float, confluence: int):
        emoji = "🟢" if side == "buy" else "🔴"
        msg = (
            f"{emoji} *TRADE OPENED*\n"
            f"Symbol: `{symbol}`\n"
            f"Side: `{side.upper()}`\n"
            f"Entry: `${entry:.2f}`\n"
            f"Stop Loss: `${sl:.2f}`\n"
            f"TP1: `${tp1:.2f}`\n"
            f"Confluence: `{confluence}/6`"
        )
        self.send(msg)

    def trade_closed(self, symbol: str, side: str, entry: float, exit_price: float, pnl: float, reason: str):
        emoji = "✅" if pnl >= 0 else "❌"
        msg = (
            f"{emoji} *TRADE CLOSED*\n"
            f"Symbol: `{symbol}`\n"
            f"Side: `{side.upper()}`\n"
            f"Entry: `${entry:.2f}` → Exit: `${exit_price:.2f}`\n"
            f"P&L: `${pnl:+.2f}`\n"
            f"Reason: `{reason.upper()}`"
        )
        self.send(msg)

    def daily_limit_hit(self, loss_pct: float):
        msg = (
            f"⛔ *DAILY LOSS LIMIT HIT*\n"
            f"Loss: `{loss_pct:.2f}%`\n"
            f"Bot has been halted for today."
        )
        self.send(msg)

    def bot_started(self, symbols: list, mode: str):
        msg = (
            f"🚀 *BOT STARTED*\n"
            f"Mode: `{mode}`\n"
            f"Watching: `{', '.join(symbols)}`"
        )
        self.send(msg)

    def bot_stopped(self, reason: str):
        msg = f"⏹ *BOT STOPPED*\n Reason: `{reason}`"
        self.send(msg)

    def error(self, error_msg: str):
        msg = f"🚨 *ERROR*\n`{error_msg[:200]}`"
        self.send(msg)

    def test(self) -> bool:
        return self.send("✅ *PROJECT JANUSTECH*\nTelegram alerts connected successfully!")