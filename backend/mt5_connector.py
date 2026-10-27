"""MT5 market data and model inference adapter."""
import os
import joblib
import MetaTrader5 as mt5
import pandas as pd

from backend.config import settings

SYMBOL = settings.symbol
TIMEFRAME = getattr(mt5, f"TIMEFRAME_{settings.timeframe_name}", mt5.TIMEFRAME_M5)
CANDLE_COUNT = 100
MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "xauusd_model.pkl"))
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"XAUUSD model not found: {MODEL_PATH}")
xau_model = joblib.load(MODEL_PATH)


def initialize_mt5() -> None:
    """Compatibility helper for older scripts; app lifecycle uses MT5Broker."""
    from backend.trading.broker_mt5 import broker
    broker.connect()


def get_candles(symbol=SYMBOL, timeframe=TIMEFRAME, count=CANDLE_COUNT):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"Could not load {symbol} candles: {mt5.last_error()}")
    frame = pd.DataFrame(rates)
    frame["time"] = pd.to_datetime(frame["time"], unit="s")
    return frame


def calculate_indicators(frame):
    result = frame.copy()
    close = result["close"]
    result["EMA20"] = close.ewm(span=20, adjust=False).mean()
    result["EMA50"] = close.ewm(span=50, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1 / 14, adjust=False).mean()
    result["RSI"] = 100 - (100 / (1 + gain / loss))
    return result


def analyze_market(symbol=SYMBOL):
    frame = calculate_indicators(get_candles(symbol, TIMEFRAME, CANDLE_COUNT))
    latest = frame.iloc[-1]
    features = pd.DataFrame(
        [[float(latest["RSI"]), float(latest["EMA20"]), float(latest["EMA50"])]],
        columns=["RSI", "EMA20", "EMA50"],
    )
    prediction = int(xau_model.predict(features)[0])
    probabilities = xau_model.predict_proba(features)[0]
    sell_probability = float(probabilities[0]) * 100
    buy_probability = float(probabilities[1]) * 100
    return {
        "symbol": symbol,
        "timeframe": settings.timeframe_name,
        "price": float(latest["close"]),
        "RSI": round(float(latest["RSI"]), 4),
        "EMA20": round(float(latest["EMA20"]), 4),
        "EMA50": round(float(latest["EMA50"]), 4),
        "candle_time": latest["time"].isoformat(),
        "AI_result": {
            "signal": "BUY" if prediction == 1 else "SELL",
            "confidence": round(max(buy_probability, sell_probability), 2),
            "buy_probability": round(buy_probability, 2),
            "sell_probability": round(sell_probability, 2),
        },
    }
