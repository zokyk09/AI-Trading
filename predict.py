"""Root-level compatibility shim for older backtest scripts."""
from backend.predict import predict_signal

__all__ = ["predict_signal"]
