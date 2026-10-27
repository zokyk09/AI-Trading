"""MetaTrader 5 desktop-terminal lifecycle adapter."""
import MetaTrader5 as mt5
from backend.config import settings


class MT5Broker:
    def __init__(self, terminal=mt5, config=settings):
        self.client = terminal
        self.config = config
        self.connected = False

    def connect(self) -> bool:
        options = {}
        if self.config.mt5_login is not None:
            options["login"] = self.config.mt5_login
        if self.config.mt5_password:
            options["password"] = self.config.mt5_password
        if self.config.mt5_server:
            options["server"] = self.config.mt5_server
        if self.config.mt5_path:
            self.connected = bool(self.client.initialize(self.config.mt5_path, **options))
        else:
            self.connected = bool(self.client.initialize(**options))
        if not self.connected:
            raise RuntimeError(f"MT5 initialize failed: {self.client.last_error()}")
        return True

    def status(self) -> dict:
        terminal = self.client.terminal_info()
        return {
            "connected": terminal is not None,
            "trade_allowed": bool(terminal.trade_allowed) if terminal else False,
        }

    def shutdown(self) -> None:
        if self.connected:
            self.client.shutdown()
            self.connected = False


broker = MT5Broker()
