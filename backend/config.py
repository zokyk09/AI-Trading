"""Runtime configuration for the Windows MT5 backend."""
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


def _optional_int(name: str) -> int | None:
    value = os.getenv(name, "").strip()
    return int(value) if value else None


@dataclass(frozen=True)
class Settings:
    symbol: str = os.getenv("TRADING_SYMBOL", "XAUUSD").upper()
    timeframe_name: str = os.getenv("TRADING_TIMEFRAME", "M5").upper()
    mode: str = os.getenv("TRADING_MODE", "demo").lower()
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    mt5_path: str | None = os.getenv("MT5_PATH") or None
    mt5_login: int | None = _optional_int("MT5_LOGIN")
    mt5_password: str | None = os.getenv("MT5_PASSWORD") or None
    mt5_server: str | None = os.getenv("MT5_SERVER") or None
    order_volume: float = float(os.getenv("ORDER_VOLUME", "0.01"))
    min_confidence: float = float(os.getenv("AUTO_CONFIDENCE", "55"))
    stop_loss_distance: float = float(os.getenv("STOP_LOSS_DISTANCE", "1.00"))
    take_profit_distance: float = float(os.getenv("TAKE_PROFIT_DISTANCE", "2.00"))
    worker_interval_seconds: float = float(os.getenv("WORKER_INTERVAL_SECONDS", "5"))
    auto_magic: int = int(os.getenv("AUTO_MAGIC", "20260810"))
    manual_magic: int = int(os.getenv("MANUAL_MAGIC", "20260809"))

    def __post_init__(self) -> None:
        if self.timeframe_name not in {"M1", "M5", "M15", "M30", "H1", "H4", "D1"}:
            raise ValueError("TRADING_TIMEFRAME must be one of M1, M5, M15, M30, H1, H4, D1")
        if not self.symbol:
            raise ValueError("TRADING_SYMBOL must not be empty")
        if self.mode != "demo":
            raise ValueError("This build only permits TRADING_MODE=demo")
        if self.order_volume != 0.01:
            raise ValueError("ORDER_VOLUME is fixed at 0.01 lot in demo mode")
        if not 0 <= self.min_confidence <= 100:
            raise ValueError("AUTO_CONFIDENCE must be between 0 and 100")
        if self.stop_loss_distance <= 0 or self.take_profit_distance <= 0:
            raise ValueError("Stop loss and take profit distances must be positive")
        if self.worker_interval_seconds <= 0:
            raise ValueError("WORKER_INTERVAL_SECONDS must be positive")


settings = Settings()
