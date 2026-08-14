import os
import joblib
import MetaTrader5 as mt5
import pandas as pd


# =========================================================
# CONFIG
# =========================================================

SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
CANDLE_COUNT = 100


# =========================================================
# LOAD XAUUSD MODEL
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MODEL_PATH = os.path.abspath(
    os.path.join(
        BASE_DIR,
        "..",
        "models",
        "xauusd_model.pkl"
    )
)

if not os.path.exists(MODEL_PATH):

    raise FileNotFoundError(
        f"Model XAUUSD tidak ditemukan: {MODEL_PATH}"
    )

print(
    "XAUUSD Model:",
    MODEL_PATH
)

xau_model = joblib.load(
    MODEL_PATH
)


# =========================================================
# INITIALIZE MT5
# =========================================================

def initialize_mt5():

    if not mt5.initialize():

        raise RuntimeError(
            f"MT5 gagal terhubung: "
            f"{mt5.last_error()}"
        )

    print(
        "MT5 berhasil terhubung"
    )


# =========================================================
# GET CANDLES
# =========================================================

def get_candles(
    symbol=SYMBOL,
    timeframe=TIMEFRAME,
    count=CANDLE_COUNT
):

    rates = mt5.copy_rates_from_pos(
        symbol,
        timeframe,
        0,
        count
    )

    if rates is None or len(rates) == 0:

        raise RuntimeError(
            f"Gagal mengambil data "
            f"{symbol}: {mt5.last_error()}"
        )

    df = pd.DataFrame(
        rates
    )

    df["time"] = pd.to_datetime(
        df["time"],
        unit="s"
    )

    return df


# =========================================================
# CALCULATE INDICATORS
# =========================================================

def calculate_indicators(df):

    df = df.copy()


    # -----------------------------------------------------
    # EMA20
    # -----------------------------------------------------

    df["EMA20"] = (
        df["close"].ewm(
            span=20,
            adjust=False
        ).mean()
    )


    # -----------------------------------------------------
    # EMA50
    # -----------------------------------------------------

    df["EMA50"] = (
        df["close"].ewm(
            span=50,
            adjust=False
        ).mean()
    )


    # -----------------------------------------------------
    # RSI14
    # -----------------------------------------------------

    delta = df["close"].diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    rs = (
        avg_gain /
        avg_loss
    )

    df["RSI"] = (
        100 -
        (
            100 /
            (1 + rs)
        )
    )

    return df


# =========================================================
# ANALYZE XAUUSD
# =========================================================

def analyze_market(
    symbol=SYMBOL
):

    df = get_candles(
        symbol,
        TIMEFRAME,
        CANDLE_COUNT
    )

    df = calculate_indicators(
        df
    )

    latest = df.iloc[-1]

    rsi = float(
        latest["RSI"]
    )

    ema20 = float(
        latest["EMA20"]
    )

    ema50 = float(
        latest["EMA50"]
    )

    price = float(
        latest["close"]
    )


    # =====================================================
    # AI PREDICTION
    # =====================================================

    sample = pd.DataFrame(
        [[
            rsi,
            ema20,
            ema50
        ]],
        columns=[
            "RSI",
            "EMA20",
            "EMA50"
        ]
    )


    prediction = xau_model.predict(
        sample
    )[0]


    probability = xau_model.predict_proba(
        sample
    )[0]


    sell_probability = (
        float(probability[0]) *
        100
    )

    buy_probability = (
        float(probability[1]) *
        100
    )


    if prediction == 1:

        signal = "BUY"
        confidence = buy_probability

    else:

        signal = "SELL"
        confidence = sell_probability


    # =====================================================
    # RESULT
    # =====================================================

    return {

        "symbol":
            symbol,

        "timeframe":
            "M5",

        "price":
            price,

        "RSI":
            round(
                rsi,
                4
            ),

        "EMA20":
            round(
                ema20,
                4
            ),

        "EMA50":
            round(
                ema50,
                4
            ),

        "AI_result": {

            "signal":
                signal,

            "confidence":
                round(
                    confidence,
                    2
                ),

            "buy_probability":
                round(
                    buy_probability,
                    2
                ),

            "sell_probability":
                round(
                    sell_probability,
                    2
                )
        }
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    initialize_mt5()

    result = analyze_market(
        "XAUUSD"
    )

    print(
        "\n=== AI DIANA XAUUSD ==="
    )

    print(
        result
    )

    mt5.shutdown()