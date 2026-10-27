"""Single model loader for the legacy tabular prediction endpoint."""
from pathlib import Path
import joblib
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "model.pkl"
if not MODEL_PATH.is_file():
    raise FileNotFoundError(f"Prediction model not found: {MODEL_PATH}")
_model = joblib.load(MODEL_PATH)


def predict_signal(rsi: float, ema20: float, ema50: float) -> dict:
    sample = pd.DataFrame([[rsi, ema20, ema50]], columns=["RSI", "EMA20", "EMA50"])
    prediction = _model.predict(sample)[0]
    probabilities = _model.predict_proba(sample)[0]
    return {
        "signal": "BUY" if prediction == 1 else "SELL",
        "buy_probability": round(float(probabilities[1]) * 100, 2),
        "sell_probability": round(float(probabilities[0]) * 100, 2),
    }
