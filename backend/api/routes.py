"""HTTP endpoints consumed by the Flutter client."""
from datetime import datetime, timedelta
from fastapi import APIRouter
import MetaTrader5 as mt5

from backend.ai.signal_engine import generate_signal
from backend.api.schemas import AutoControl, OrderRequest, PredictionRequest
from backend.config import settings
from backend.mt5_connector import analyze_market
from backend.predict import predict_signal
from backend.trading.runtime import engine, order_manager

router = APIRouter()


@router.get("/")
@router.get("/api/health")
def health():
    return {"status": "Online", "message": "AI Trading API ready"}


@router.get("/api/status")
def status():
    terminal = mt5.terminal_info()
    connected = terminal is not None
    return {
        "connected": connected,
        "message": "MT5 Connected" if connected else "MT5 not connected",
        "trade_allowed": bool(terminal.trade_allowed) if connected else False,
        "auto_enabled": engine.enabled,
        "auto_confidence": settings.min_confidence,
        "auto_symbol": settings.symbol,
        "auto_volume": settings.order_volume,
    }


@router.get("/api/auto")
def auto_status():
    return {
        "enabled": engine.enabled,
        "symbol": settings.symbol,
        "timeframe": settings.timeframe_name,
        "confidence": settings.min_confidence,
        "volume": settings.order_volume,
        "sl": settings.stop_loss_distance,
        "tp": settings.take_profit_distance,
        "mode": "DEMO_ONLY",
    }


@router.post("/api/auto")
def auto_control(command: AutoControl):
    return engine.start() if command.enabled else engine.stop()


@router.get("/api/account")
def account_status():
    account = mt5.account_info()
    if account is None:
        return {"connected": False}
    return {
        "connected": True,
        "login": int(account.login),
        "balance": float(account.balance),
        "equity": float(account.equity),
        "profit": float(account.profit),
        "currency": account.currency,
        "server": getattr(account, "server", None),
        "company": getattr(account, "company", None),
        "trade_mode": int(account.trade_mode),
    }


@router.get("/api/market")
def market():
    return analyze_market(settings.symbol)


@router.get("/api/signal")
def signal():
    result = analyze_market(settings.symbol)
    ai = result["AI_result"]
    display_signal = generate_signal({
        "buy_probability": ai["buy_probability"],
        "sell_probability": ai["sell_probability"],
        "min_confidence": settings.min_confidence,
    })["signal"]
    return {
        "symbol": result["symbol"],
        "timeframe": result["timeframe"],
        "price": result["price"],
        "RSI": result["RSI"],
        "EMA20": result["EMA20"],
        "EMA50": result["EMA50"],
        "signal": display_signal,
        "buy_probability": ai["buy_probability"],
        "sell_probability": ai["sell_probability"],
        "candle_time": result["candle_time"],
    }


@router.get("/api/positions")
def positions():
    items = mt5.positions_get() or []
    return {
        "total": len(items),
        "positions": [
            {
                "ticket": int(item.ticket),
                "symbol": item.symbol,
                "type": int(item.type),
                "volume": float(item.volume),
                "price_open": float(item.price_open),
                "sl": float(item.sl),
                "tp": float(item.tp),
                "profit": float(item.profit),
            }
            for item in items
        ],
    }


@router.post("/predict")
def predict(data: PredictionRequest):
    return predict_signal(data.RSI, data.EMA20, data.EMA50)


@router.post("/webhook")
def webhook(data: PredictionRequest):
    result = predict_signal(data.RSI, data.EMA20, data.EMA50)
    return {"symbol": data.symbol, "price": data.price, "AI_result": result}


@router.post("/api/order")
def manual_order(data: OrderRequest):
    return order_manager.submit(
        symbol=data.symbol,
        side=data.side,
        volume=data.volume,
        magic=settings.manual_magic,
        comment="AI Trading manual demo",
    )


@router.get("/api/history")
def trade_history():
    end = datetime.now()
    start = end - timedelta(days=30)
    deals = mt5.history_deals_get(start, end) or []
    relevant = [d for d in deals if d.type in {mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL}]
    result = [
        {
            "ticket": int(d.ticket),
            "order": int(d.order),
            "time": datetime.fromtimestamp(d.time).strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": d.symbol,
            "type": "BUY" if d.type == mt5.DEAL_TYPE_BUY else "SELL",
            "volume": float(d.volume),
            "price": float(d.price),
            "profit": float(d.profit),
            "commission": float(d.commission),
            "swap": float(d.swap),
            "magic": int(d.magic),
            "comment": d.comment,
        }
        for d in relevant
    ]
    result.reverse()
    return {"total": len(result), "history": result}




