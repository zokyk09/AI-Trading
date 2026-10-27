from backend.ai.strategy import decide


def generate_signal(features: dict) -> dict:
    buy = float(features.get("buy_probability", 0.0))
    sell = float(features.get("sell_probability", 0.0))
    return {
        "signal": decide(features),
        "confidence": round(max(buy, sell), 2),
        "buy_probability": buy,
        "sell_probability": sell,
    }
