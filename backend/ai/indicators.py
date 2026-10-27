"""Pure indicator helpers operating on sequences of prices."""
def ema(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    alpha = 2 / (period + 1)
    result = float(values[0])
    for value in values[1:]:
        result = alpha * float(value) + (1 - alpha) * result
    return result

def rsi(values: list[float], period: int = 14) -> float | None:
    if period <= 0 or len(values) <= period:
        return None
    changes = [float(b) - float(a) for a, b in zip(values, values[1:])]
    gains = [max(change, 0) for change in changes[-period:]]
    losses = [max(-change, 0) for change in changes[-period:]]
    avg_gain, avg_loss = sum(gains) / period, sum(losses) / period
    if avg_loss == 0:
        return 100.0 if avg_gain else 50.0
    return 100 - 100 / (1 + avg_gain / avg_loss)
