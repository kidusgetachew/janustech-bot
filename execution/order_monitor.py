"""
SMCBot — Order Monitor & Position Reconciler
Tracks order fills, manages TP2, moves SL to breakeven.
"""

import time
import threading
from datetime import datetime, timezone
from config.logger import logger


class OrderMonitor:
    """
    Runs in background, monitoring all open orders and positions.
    Handles: fill confirmation, TP2 placement, SL to breakeven, position reconciliation.
    """

    def __init__(self, client, risk_manager):
        self.client = client
        self.risk_manager = risk_manager
        self.pending_orders = {}    # order_id -> trade details
        self.active_positions = {}  # symbol -> position details
        self.is_running = False
        self._thread = None

    def start(self):
        self.is_running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Order monitor started.")

    def stop(self):
        self.is_running = False
        logger.info("Order monitor stopped.")

    def register_order(self, order_id: str, trade: dict):
        """Register a new order to monitor for fill confirmation."""
        self.pending_orders[order_id] = {
            **trade,
            "order_id": order_id,
            "registered_at": datetime.now(timezone.utc),
            "tp1_hit": False,
            "sl_moved_to_be": False,
            "tp2_order_id": None,
            "tp2_placed": False,
            "sl_moved": False,
        }
        logger.info(f"Monitoring order: {order_id} | {trade.get('symbol')} {trade.get('side')}")

    def _monitor_loop(self):
        """Main monitoring loop — runs every 10 seconds."""
        while self.is_running:
            try:
                self._check_pending_orders()
                self._reconcile_positions()
                self._manage_active_positions()
            except Exception as e:
                logger.error(f"Order monitor error: {e}")
            time.sleep(10)

    def _check_pending_orders(self):
        """Check if pending orders have been filled."""
        if not self.pending_orders:
            return

        filled_ids = []
        for order_id, trade in list(self.pending_orders.items()):
            try:
                orders = self.client.get_open_orders()
                order_ids = [o["id"] for o in orders]

                if order_id not in order_ids:
                    positions = self.client.get_positions()
                    pos_symbols = [p["symbol"] for p in positions]

                    if trade["symbol"] in pos_symbols:
                        logger.info(f"Order FILLED | {trade['symbol']} {trade['side']} | ID: {order_id}")
                        self.active_positions[trade["symbol"]] = {
                            **trade,
                            "filled_at": datetime.now(timezone.utc),
                            "tp1_hit": False,
                            "sl_moved": False,
                            "tp2_placed": False,
                        }
                        self.risk_manager.on_trade_opened(trade)
                        filled_ids.append(order_id)
                    else:
                        logger.warning(f"Order NOT filled (rejected/cancelled) | {trade['symbol']} | ID: {order_id}")
                        filled_ids.append(order_id)

            except Exception as e:
                logger.error(f"Error checking order {order_id}: {e}")

        for oid in filled_ids:
            del self.pending_orders[oid]

    def _reconcile_positions(self):
        """Compare bot's internal state vs actual Alpaca positions."""
        try:
            actual_positions = self.client.get_positions()
            actual_symbols = {p["symbol"] for p in actual_positions}
            bot_symbols = set(self.active_positions.keys())

            closed_by_market = bot_symbols - actual_symbols
            for sym in closed_by_market:
                trade = self.active_positions[sym]
                logger.info(f"Position closed externally: {sym}")
                self.risk_manager.on_trade_closed(trade, 0.0)
                del self.active_positions[sym]

        except Exception as e:
            logger.error(f"Reconciliation error: {e}")

    def _manage_active_positions(self):
        """
        For each active position:
        - Check if TP1 was hit → place TP2, move SL to breakeven
        - Check if TP2 was hit → close fully
        """
        try:
            positions = self.client.get_positions()
            pos_map = {p["symbol"]: p for p in positions}

            for symbol, trade in list(self.active_positions.items()):
                if symbol not in pos_map:
                    continue

                pos = pos_map[symbol]
                current_price = float(pos.get("current_price", 0))
                entry = float(trade.get("entry", trade.get("entry_price", 0)))
                tp1 = float(trade.get("tp1", 0))
                tp2 = float(trade.get("tp2", 0))
                side = trade.get("side", "buy")
                original_qty = float(trade.get("qty", 0))
                current_qty = abs(float(pos.get("qty", 0)))

                # Detect TP1 hit by checking if position qty dropped by ~50%
                if not trade.get("tp1_hit") and original_qty > 0:
                    qty_ratio = current_qty / original_qty
                    if qty_ratio < 0.6:
                        trade["tp1_hit"] = True
                        logger.info(f"TP1 HIT | {symbol} | Moving SL to breakeven")

                        # Move SL to breakeven
                        if not trade.get("sl_moved") and entry > 0:
                            self._move_sl_to_breakeven(symbol, entry, side, current_qty)
                            trade["sl_moved"] = True

                        # Place TP2 for remaining qty
                        if tp2 > 0 and not trade.get("tp2_placed"):
                            self._place_tp2(symbol, current_qty, side, tp2)
                            trade["tp2_placed"] = True

        except Exception as e:
            logger.error(f"Position management error: {e}")

    def _move_sl_to_breakeven(self, symbol: str, entry: float, side: str, qty: float):
        """Move stop loss to entry price (breakeven) via Alpaca API."""
        try:
            logger.info(f"Moving SL to breakeven | {symbol} | Entry: {entry:.2f}")

            # Cancel all open orders for this symbol
            open_orders = self.client.get_open_orders()
            for order in open_orders:
                if order.get("symbol") == symbol and order.get("type") in ["stop", "stop_limit"]:
                    self.client.cancel_order(order["id"])
                    logger.info(f"Cancelled old SL order: {order['id']}")

            # Place new stop order at breakeven
            stop_side = "sell" if side == "buy" else "buy"
            ok, order_id = self.client.place_stop_order(
                symbol=symbol,
                qty=qty,
                side=stop_side,
                stop_price=round(entry, 2),
            )
            if ok:
                logger.info(f"SL moved to breakeven | {symbol} | {entry:.2f} | Order: {order_id}")
            else:
                logger.error(f"Failed to place breakeven SL for {symbol}: {order_id}")

        except Exception as e:
            logger.error(f"Failed to move SL to breakeven for {symbol}: {e}")

    def _place_tp2(self, symbol: str, qty: float, side: str, tp2_price: float):
        """Place TP2 limit order for remaining position via Alpaca API."""
        try:
            logger.info(f"Placing TP2 | {symbol} | Price: {tp2_price:.2f} | Qty: {qty}")

            limit_side = "sell" if side == "buy" else "buy"
            ok, order_id = self.client.place_limit_order(
                symbol=symbol,
                qty=qty,
                side=limit_side,
                limit_price=round(tp2_price, 2),
            )
            if ok:
                logger.info(f"TP2 placed | {symbol} | {tp2_price:.2f} | Order: {order_id}")
            else:
                logger.error(f"Failed to place TP2 for {symbol}: {order_id}")

        except Exception as e:
            logger.error(f"Failed to place TP2 for {symbol}: {e}")

    def get_status(self) -> dict:
        return {
            "is_running": self.is_running,
            "pending_orders": len(self.pending_orders),
            "active_positions": len(self.active_positions),
            "positions": list(self.active_positions.keys()),
        }
