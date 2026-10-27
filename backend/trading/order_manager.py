"""MT5 order placement with demo-account and fixed-volume guards."""
import logging

from backend.config import settings
from backend.trading.risk_manager import validate_demo_account, validate_order

logger = logging.getLogger(__name__)


class OrderManager:
    def __init__(self, mt5, config=settings):
        self.mt5 = mt5
        self.config = config

    def submit(self, *, symbol: str, side: str, volume: float, magic: int, comment: str) -> dict:
        side = str(side).upper()
        if side not in {"BUY", "SELL"}:
            return {"success": False, "message": "Side must be BUY or SELL"}
        if self.config.mode != "demo":
            return {"success": False, "message": "Only demo mode is enabled"}

        accepted, reason = validate_order(
            mode=self.config.mode,
            risk_percent=1.0,
            volume=volume,
        )
        if not accepted or volume != self.config.order_volume:
            return {"success": False, "message": reason if not accepted else "Configured demo volume mismatch"}
        valid, message = validate_demo_account(self.mt5, symbol=symbol)
        if not valid:
            return {"success": False, "message": message}

        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info is None:
            return {"success": False, "message": f"Symbol {symbol} is unavailable"}
        if not symbol_info.visible and not self.mt5.symbol_select(symbol, True):
            return {"success": False, "message": f"Could not enable {symbol}"}
        symbol_info = self.mt5.symbol_info(symbol)
        tick = self.mt5.symbol_info_tick(symbol)
        if symbol_info is None or tick is None:
            return {"success": False, "message": f"No market data for {symbol}"}

        order_type = self.mt5.ORDER_TYPE_BUY if side == "BUY" else self.mt5.ORDER_TYPE_SELL
        price = tick.ask if side == "BUY" else tick.bid
        direction = 1 if side == "BUY" else -1
        sl = round(price - direction * self.config.stop_loss_distance, symbol_info.digits)
        tp = round(price + direction * self.config.take_profit_distance, symbol_info.digits)
        price = round(price, symbol_info.digits)
        filling_mode = symbol_info.filling_mode
        if filling_mode & 1:
            filling = self.mt5.ORDER_FILLING_FOK
        elif filling_mode & 2:
            filling = self.mt5.ORDER_FILLING_IOC
        else:
            filling = self.mt5.ORDER_FILLING_RETURN

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": magic,
            "comment": comment,
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }
        check = self.mt5.order_check(request)
        if check is None:
            return {"success": False, "message": "order_check failed", "error": str(self.mt5.last_error())}
        if check.retcode != 0:
            return {"success": False, "message": "Order rejected by order_check", "retcode": check.retcode, "comment": check.comment}

        result = self.mt5.order_send(request)
        if result is None:
            return {"success": False, "message": "order_send failed", "error": str(self.mt5.last_error())}
        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            return {"success": False, "message": "Order execution failed", "retcode": result.retcode, "comment": result.comment}

        logger.info("Demo order placed: %s %s %.2f lot ticket=%s", side, symbol, volume, result.order)
        return {
            "success": True,
            "message": f"{side} {symbol} sent",
            "symbol": symbol,
            "side": side,
            "volume": volume,
            "price": price,
            "sl": sl,
            "tp": tp,
            "order": int(result.order),
            "deal": int(result.deal),
            "retcode": result.retcode,
            "comment": result.comment,
        }


