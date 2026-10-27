"""Confidence-gated interpretation of model probabilities."""


def decide(features: dict) -> str:
    buy = float(features.get("buy_probability", 0.0))
    sell = float(features.get("sell_probability", 0.0))
    threshold = float(features.get("min_confidence", 55.0))
    if max(buy, sell) < threshold:
        return "HOLD"
    return "BUY" if buy >= sell else "SELL"
