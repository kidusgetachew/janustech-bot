"""
SMCBot Configuration
All parameters controlling bot behavior.
Users set these via the UI — never hardcode API keys here.
"""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class APIConfig:
    """Alpaca API credentials — loaded from .env or set via UI."""
    api_key: str = ""
    secret_key: str = ""
    paper_trading: bool = True

    @property
    def base_url(self) -> str:
        if self.paper_trading:
            return "https://paper-api.alpaca.markets"
        return "https://api.alpaca.markets"

    @property
    def data_url(self) -> str:
        return "https://data.alpaca.markets"


@dataclass
class RiskConfig:
    """Risk management parameters."""
    risk_per_trade: float = 0.01
    max_daily_loss: float = 0.03
    max_open_trades: int = 2
    drawdown_limit: float = 0.05
    tp1_close_pct: float = 0.50
    tp1_r_multiple: float = 1.5
    tp2_r_multiple: float = 3.0
    max_spread_pct: float = 0.001


@dataclass
class StrategyConfig:
    """SMC strategy parameters."""
    tf_bias: str = "1Day"
    tf_structure: str = "4Hour"
    tf_confirmation: str = "1Hour"
    tf_entry: str = "15Min"
    tf_precision: str = "5Min"

    fvg_min_size_pts: float = 5.0
    ob_lookback: int = 20
    bos_lookback: int = 10
    swing_lookback: int = 5
    confluence_min: int = 3
    equilibrium_zone: float = 0.1

    sessions: dict = field(default_factory=lambda: {
        "london": {"start": 7, "end": 12},
        "new_york": {"start": 12, "end": 17},
        "london_open": {"start": 7, "end": 9},
        "ny_open": {"start": 13, "end": 15},
    })
    active_sessions: List[str] = field(
        default_factory=lambda: ["london", "new_york"]
    )


@dataclass
class MarketsConfig:
    """Markets to trade."""
    symbols: List[str] = field(
        default_factory=lambda: ["SPY", "QQQ"]
    )
    asset_type: str = "stock"


@dataclass
class AlertConfig:
    """Notification settings."""
    telegram_token: str = ""
    telegram_chat_id: str = ""
    alert_on_entry: bool = True
    alert_on_exit: bool = True
    alert_on_daily_loss: bool = True
    alert_on_error: bool = True


@dataclass
class BotConfig:
    """Master config — combines all sub-configs."""
    api: APIConfig = field(default_factory=APIConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    markets: MarketsConfig = field(default_factory=MarketsConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)

    is_running: bool = False
    log_level: str = "INFO"
    log_dir: str = "logs"

    def load_from_env(self):
        self.api.api_key = os.getenv("ALPACA_API_KEY", "")
        self.api.secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        self.api.paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
        return self

    def set_api_keys(self, api_key: str, secret_key: str, paper: bool = True):
        self.api.api_key = api_key
        self.api.secret_key = secret_key
        self.api.paper_trading = paper
        return self

    def validate(self) -> tuple[bool, str]:
        if not self.api.api_key or not self.api.secret_key:
            return False, "API keys not set. Go to Setup to connect."
        if self.risk.risk_per_trade > 0.05:
            return False, "Risk per trade too high. Max recommended: 5%"
        if self.risk.max_open_trades > 5:
            return False, "Too many max open trades. Recommended: 2-3"
        return True, "Config valid"


config = BotConfig().load_from_env()