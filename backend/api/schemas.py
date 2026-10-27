"""Request and response models for the public API."""
from typing import Literal
from pydantic import BaseModel, Field


class AutoControl(BaseModel):
    enabled: bool


class OrderRequest(BaseModel):
    symbol: str = "XAUUSD"
    side: Literal["BUY", "SELL"]
    volume: float = Field(default=0.01, gt=0, le=0.01)


class PredictionRequest(BaseModel):
    RSI: float
    EMA20: float
    EMA50: float
    symbol: str | None = None
    price: float | None = None
