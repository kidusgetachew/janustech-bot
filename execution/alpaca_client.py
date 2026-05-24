"""
SMCBot — Alpaca Client
Handles all communication with Alpaca API.
Includes WebSocket real-time price streaming.
"""

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
    GetOrdersRequest,
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    QueryOrderStatus,
)
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import DataFeed

from datetime import datetime, timedelta
from typing import Optional, Callable
import threading
import pandas as pd

from config.logger import logger


class AlpacaClient:

    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper
        self.connected = False
        self._trading_client: Optional[TradingClient] = None
        self._data_client: Optional[StockHistoricalDataClient] = None
        self._stream: Optional[StockDataStream] = None
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_running = False

        # Live price cache — updated by WebSocket
        self.live_prices: dict = {}
        self._price_callbacks: list = []

    def connect(self) -> tuple[bool, str]:
        try:
            self._trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                paper=self.paper
            )
            self._data_client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
            )
            account = self._trading_client.get_account()
            self.connected = True
            mode = "PAPER" if self.paper else "LIVE"
            logger.info(f"Connected to Alpaca [{mode}]. Balance: ${float(account.equity):,.2f}")
            return True, f"Connected. Balance: ${float(account.equity):,.2f}"
        except Exception as e:
            self.connected = False
            logger.error(f"Alpaca connection failed: {e}")
            return False, f"Connection failed: {str(e)}"

    def disconnect(self):
        self.stop_stream()
        self.connected = False
        self._trading_client = None
        self._data_client = None
        logger.info("Disconnected from Alpaca.")

    # ── WebSocket Streaming ────────────────────────────────────────────────

    def start_stream(self, symbols: list):
        """Start WebSocket stream for real-time prices."""
        if self._stream_running:
            return
        if not self.connected:
            return

        try:
            self._stream = StockDataStream(
                api_key=self.api_key,
                secret_key=self.secret_key,
            )

            async def on_bar(bar):
                sym = bar.symbol
                self.live_prices[sym] = {
                    "price": float(bar.close),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "volume": int(bar.volume),
                    "timestamp": str(bar.timestamp),
                    "change_pct": ((float(bar.close) - float(bar.open)) / float(bar.open)) * 100,
                }
                for cb in self._price_callbacks:
                    try:
                        cb(sym, self.live_prices[sym])
                    except Exception:
                        pass

            async def on_trade(trade):
                sym = trade.symbol
                if sym in self.live_prices:
                    self.live_prices[sym]["price"] = float(trade.price)
                else:
                    self.live_prices[sym] = {
                        "price": float(trade.price),
                        "change_pct": 0.0,
                    }

            self._stream.subscribe_bars(on_bar, *symbols)
            self._stream.subscribe_trades(on_trade, *symbols)

            self._stream_running = True
            self._stream_thread = threading.Thread(
                target=self._stream.run,
                daemon=True,
            )
            self._stream_thread.start()
            logger.info(f"WebSocket stream started for: {symbols}")

        except Exception as e:
            logger.error(f"WebSocket stream failed to start: {e}")
            self._stream_running = False

    def stop_stream(self):
        """Stop WebSocket stream."""
        if self._stream and self._stream_running:
            try:
                self._stream.stop()
            except Exception:
                pass
            self._stream_running = False
            logger.info("WebSocket stream stopped.")

    def add_price_callback(self, callback: Callable):
        """Register a callback to be called when a new price arrives."""
        self._price_callbacks.append(callback)

    def get_live_price(self, symbol: str) -> float:
        """Get latest cached live price for a symbol."""
        return self.live_prices.get(symbol, {}).get("price", 0.0)

    def get_live_data(self, symbol: str) -> dict:
        """Get full live data dict for a symbol."""
        return self.live_prices.get(symbol, {})

    # ── Account ────────────────────────────────────────────────────────────

    def get_account(self) -> dict:
        if not self.connected:
            return {}
        try:
            acc = self._trading_client.get_account()
            return {
                "balance": float(acc.cash),
                "equity": float(acc.equity),
                "buying_power": float(acc.buying_power),
                "pnl_today": float(acc.equity) - float(acc.last_equity),
                "pnl_pct": (
                    (float(acc.equity) - float(acc.last_equity))
                    / float(acc.last_equity) * 100
                ),
                "status": acc.status,
            }
        except Exception as e:
            logger.error(f"Failed to get account: {e}")
            return {}

    def get_positions(self) -> list:
        if not self.connected:
            return []
        try:
            positions = self._trading_client.get_all_positions()
            result = []
            for p in positions:
                result.append({
                    "symbol": p.symbol,
                    "qty": float(p.qty),
                    "side": "long" if float(p.qty) > 0 else "short",
                    "entry_price": float(p.avg_entry_price),
                    "current_price": float(p.current_price),
                    "pnl": float(p.unrealized_pl),
                    "pnl_pct": float(p.unrealized_plpc) * 100,
                    "market_value": float(p.market_value),
                })
            return result
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

    def get_open_orders(self) -> list:
        if not self.connected:
            return []
        try:
            req = GetOrdersRequest(status=QueryOrderStatus.OPEN)
            orders = self._trading_client.get_orders(filter=req)
            return [
                {
                    "id": str(o.id),
                    "symbol": o.symbol,
                    "side": o.side.value,
                    "qty": float(o.qty),
                    "type": o.order_type.value,
                    "status": o.status.value,
                    "submitted_at": str(o.submitted_at),
                }
                for o in orders
            ]
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []

    # ── Orders ─────────────────────────────────────────────────────────────

    def place_market_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        stop_loss: float,
        take_profit: float,
    ) -> tuple[bool, str]:
        if not self.connected:
            return False, "Not connected to Alpaca"
        try:
            order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
            order_req = MarketOrderRequest(
                symbol=symbol,
                qty=round(qty, 2),
                side=order_side,
                time_in_force=TimeInForce.DAY,
                order_class="bracket",
                stop_loss=StopLossRequest(stop_price=round(stop_loss, 2)),
                take_profit=TakeProfitRequest(limit_price=round(take_profit, 2)),
            )
            order = self._trading_client.submit_order(order_req)
            logger.info(
                f"ORDER PLACED | {side.upper()} {qty} {symbol} | "
                f"SL: {stop_loss:.2f} | TP: {take_profit:.2f} | ID: {order.id}"
            )
            return True, str(order.id)
        except Exception as e:
            logger.error(f"Order failed [{symbol}]: {e}")
            return False, str(e)

    def place_limit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        limit_price: float,
    ) -> tuple[bool, str]:
        """Place a limit order — used for TP2."""
        if not self.connected:
            return False, "Not connected"
        try:
            order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
            order_req = LimitOrderRequest(
                symbol=symbol,
                qty=round(qty, 2),
                side=order_side,
                time_in_force=TimeInForce.DAY,
                limit_price=round(limit_price, 2),
            )
            order = self._trading_client.submit_order(order_req)
            logger.info(f"LIMIT ORDER | {side.upper()} {qty} {symbol} @ {limit_price:.2f} | ID: {order.id}")
            return True, str(order.id)
        except Exception as e:
            logger.error(f"Limit order failed [{symbol}]: {e}")
            return False, str(e)

    def place_stop_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        stop_price: float,
    ) -> tuple[bool, str]:
        """Place a stop order — used for SL to breakeven."""
        if not self.connected:
            return False, "Not connected"
        try:
            order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
            order_req = StopOrderRequest(
                symbol=symbol,
                qty=round(qty, 2),
                side=order_side,
                time_in_force=TimeInForce.DAY,
                stop_price=round(stop_price, 2),
            )
            order = self._trading_client.submit_order(order_req)
            logger.info(f"STOP ORDER | {side.upper()} {qty} {symbol} @ {stop_price:.2f} | ID: {order.id}")
            return True, str(order.id)
        except Exception as e:
            logger.error(f"Stop order failed [{symbol}]: {e}")
            return False, str(e)

    def close_position(self, symbol: str) -> tuple[bool, str]:
        if not self.connected:
            return False, "Not connected"
        try:
            self._trading_client.close_position(symbol)
            logger.info(f"Position closed: {symbol}")
            return True, f"Closed {symbol}"
        except Exception as e:
            logger.error(f"Failed to close {symbol}: {e}")
            return False, str(e)

    def close_all_positions(self) -> tuple[bool, str]:
        if not self.connected:
            return False, "Not connected"
        try:
            self._trading_client.close_all_positions(cancel_orders=True)
            logger.warning("EMERGENCY CLOSE — All positions liquidated.")
            return True, "All positions closed"
        except Exception as e:
            logger.error(f"Emergency close failed: {e}")
            return False, str(e)

    def cancel_order(self, order_id: str) -> bool:
        try:
            self._trading_client.cancel_order_by_id(order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Cancel order failed: {e}")
            return False

    # ── Data ───────────────────────────────────────────────────────────────

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        lookback_days: int = 60,
    ) -> pd.DataFrame:
        if not self.connected:
            return pd.DataFrame()

        tf_map = {
            "1Day":  TimeFrame(1, TimeFrameUnit.Day),
            "4Hour": TimeFrame(4, TimeFrameUnit.Hour),
            "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
            "15Min": TimeFrame(15, TimeFrameUnit.Minute),
            "5Min":  TimeFrame(5, TimeFrameUnit.Minute),
            "1Min":  TimeFrame(1, TimeFrameUnit.Minute),
        }

        tf = tf_map.get(timeframe)
        if not tf:
            logger.error(f"Unknown timeframe: {timeframe}")
            return pd.DataFrame()

        try:
            end = datetime.utcnow()
            start = end - timedelta(days=lookback_days)
            req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=start,
                end=end,
                feed=DataFeed.IEX,
            )
            bars = self._data_client.get_stock_bars(req)
            df = bars.df
            if isinstance(df.index, pd.MultiIndex):
                df = df.xs(symbol, level="symbol")
            df.index = pd.to_datetime(df.index, utc=True)
            df.columns = [c.lower() for c in df.columns]
            df = df[["open", "high", "low", "close", "volume"]].copy()
            df = df.sort_index()
            logger.debug(f"Fetched {len(df)} {timeframe} bars for {symbol}")
            return df
        except Exception as e:
            logger.error(f"Failed to fetch bars [{symbol} {timeframe}]: {e}")
            return pd.DataFrame()

    def get_latest_price(self, symbol: str) -> float:
        """Get latest price — uses live cache if available, falls back to REST."""
        live = self.get_live_price(symbol)
        if live > 0:
            return live
        try:
            bars = self.get_bars(symbol, "1Min", lookback_days=1)
            if not bars.empty:
                return float(bars["close"].iloc[-1])
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
        return 0.0
