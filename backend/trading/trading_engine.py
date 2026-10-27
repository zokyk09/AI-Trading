"""Background strategy worker. Starts in STOP state and only trades demo."""
import logging
import threading

from backend.config import settings
from backend.trading.risk_manager import validate_demo_account

logger = logging.getLogger(__name__)


class TradingEngine:
    def __init__(self, mt5, market_analyzer, order_manager, config=settings):
        self.mt5 = mt5
        self.market_analyzer = market_analyzer
        self.order_manager = order_manager
        self.config = config
        self._enabled = False
        self._last_candle = None
        self._stop_event = threading.Event()
        self._thread = None
        self._lock = threading.RLock()

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def start_worker(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="ai-trading-worker", daemon=True)
        self._thread.start()
        logger.info("Trading worker started in STOP state")

    def start(self) -> dict:
        if self._thread is None or not self._thread.is_alive():
            return {"success": False, "enabled": False, "message": "Trading worker is not ready; restart the backend after MT5 is logged in"}
        if self.config.mode != "demo":
            return {"success": False, "enabled": False, "message": "Only demo mode is enabled"}
        valid, message = validate_demo_account(self.mt5, symbol=self.config.symbol)
        if not valid:
            return {"success": False, "enabled": False, "message": message}
        with self._lock:
            self._last_candle = None
            self._enabled = True
        logger.warning("AUTO DEMO enabled: %s %s, volume %.2f", self.config.symbol, self.config.timeframe_name, self.config.order_volume)
        return {
            "success": True,
            "enabled": True,
            "message": "AUTO TRADING DEMO ACTIVE",
            "symbol": self.config.symbol,
            "timeframe": self.config.timeframe_name,
            "confidence": self.config.min_confidence,
            "volume": self.config.order_volume,
            "sl": self.config.stop_loss_distance,
            "tp": self.config.take_profit_distance,
        }

    def stop(self) -> dict:
        with self._lock:
            self._enabled = False
            self._last_candle = None
        logger.info("AUTO trading stopped")
        return {"success": True, "enabled": False, "message": "AUTO TRADING STOPPED"}

    def shutdown(self) -> None:
        self.stop()
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.config.worker_interval_seconds + 1)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if not self.enabled:
                self._stop_event.wait(1)
                continue
            try:
                valid, message = validate_demo_account(self.mt5, symbol=self.config.symbol)
                if not valid:
                    logger.warning("AUTO paused: %s", message)
                    self.stop()
                    continue
                positions = self.mt5.positions_get(symbol=self.config.symbol)
                if positions:
                    self._stop_event.wait(self.config.worker_interval_seconds)
                    continue
                analysis = self.market_analyzer(self.config.symbol)
                ai = analysis["AI_result"]
                side = str(ai["signal"]).upper()
                if side not in {"BUY", "SELL"}:
                    self._stop_event.wait(self.config.worker_interval_seconds)
                    continue
                confidence_key = "buy_probability" if side == "BUY" else "sell_probability"
                confidence = float(ai[confidence_key])
                candle_time = analysis.get("candle_time")
                if candle_time is None or candle_time == self._last_candle:
                    self._stop_event.wait(self.config.worker_interval_seconds)
                    continue
                self._last_candle = candle_time
                logger.info("Signal %s confidence %.2f%% candle=%s", side, confidence, candle_time)
                if confidence >= self.config.min_confidence:
                    result = self.order_manager.submit(
                        symbol=self.config.symbol,
                        side=side,
                        volume=self.config.order_volume,
                        magic=self.config.auto_magic,
                        comment="AI Trading Demo",
                    )
                    logger.info("AUTO order result: %s", result)
            except Exception:
                logger.exception("Trading worker iteration failed")
            self._stop_event.wait(self.config.worker_interval_seconds)


