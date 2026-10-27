from backend.config import settings
from backend.services.robot_service import robot

def get_status() -> dict:
    return {"running": robot.running, "mode": settings.trading_mode, "symbol": settings.trading_symbol, "signal": "HOLD"}
