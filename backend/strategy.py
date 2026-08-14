import ta


def analyze(data):

    # ambil data Close BTC
    close = data["Close"]

    # jika format yfinance terbaru menghasilkan tabel
    if len(close.shape) > 1:
        close = close.iloc[:, 0]


    # RSI
    rsi = ta.momentum.RSIIndicator(
        close,
        window=14
    ).rsi()


    # EMA 20
    ema = ta.trend.EMAIndicator(
        close,
        window=20
    ).ema_indicator()


    # ambil data terakhir
    last_price = float(close.iloc[-1])
    last_rsi = float(rsi.iloc[-1])
    last_ema = float(ema.iloc[-1])


    score = 0


    # Analisa trend
    if last_price > last_ema:
        trend = "BULLISH"
        score += 50
    else:
        trend = "BEARISH"
        score += 10


    # Analisa RSI
    if last_rsi < 35:
        score += 30

    elif last_rsi < 50:
        score += 20

    else:
        score += 0


    # keputusan
    if score >= 70:
        signal = "BUY"

    elif score <= 30:
        signal = "SELL"

    else:
        signal = "HOLD"


    return {
        "price": last_price,
        "rsi": round(last_rsi, 2),
        "ema": round(last_ema, 2),
        "trend": trend,
        "score": score,
        "signal": signal
    }