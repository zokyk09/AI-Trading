import MetaTrader5 as mt5
import pandas as pd

from predict import predict_signal


# ==========================================
# CONFIGURATION
# ==========================================

SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
CANDLES = 20000


# ==========================================
# GET MT5 DATA
# ==========================================

def get_data():

    rates = mt5.copy_rates_from_pos(
        SYMBOL,
        TIMEFRAME,
        0,
        CANDLES
    )

    if rates is None or len(rates) == 0:
        raise RuntimeError(
            f"Gagal mengambil data MT5: {mt5.last_error()}"
        )

    df = pd.DataFrame(rates)

    df["time"] = pd.to_datetime(
        df["time"],
        unit="s"
    )

    return df


# ==========================================
# CALCULATE INDICATORS
# ==========================================

def calculate_indicators(df):

    df = df.copy()

    # --------------------------------------
    # EMA 20
    # --------------------------------------

    df["EMA20"] = df["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    # --------------------------------------
    # EMA 50
    # --------------------------------------

    df["EMA50"] = df["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    # --------------------------------------
    # RSI 14
    # --------------------------------------

    delta = df["close"].diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss

    df["RSI"] = 100 - (
        100 / (1 + rs)
    )

    return df


# ==========================================
# RUN BACKTEST
# ==========================================

def run_backtest(df):

    # --------------------------------------
    # 80% = data sebelumnya
    # 20% = data testing
    # --------------------------------------

    split_index = int(len(df) * 0.8)

    test_df = df.iloc[split_index:].copy()

    print(
        f"\nData sebelumnya : {split_index}"
    )

    print(
        f"Data testing    : {len(test_df)}"
    )

    # --------------------------------------
    # Statistics
    # --------------------------------------

    wins = 0
    losses = 0

    buy_count = 0
    sell_count = 0

    trades = []

    # --------------------------------------
    # LOOP TESTING DATA
    # --------------------------------------

    for i in range(
        50,
        len(test_df) - 1
    ):

        current = test_df.iloc[i]

        next_candle = test_df.iloc[i + 1]

        # ----------------------------------
        # Check indicator
        # ----------------------------------

        if (
            pd.isna(current["RSI"])
            or pd.isna(current["EMA20"])
            or pd.isna(current["EMA50"])
        ):
            continue

        # ----------------------------------
        # AI Prediction
        # ----------------------------------

        result = predict_signal(

            float(current["RSI"]),

            float(current["EMA20"]),

            float(current["EMA50"])

        )

        signal = result["signal"]

        # ----------------------------------
        # Entry
        # ----------------------------------

        entry = float(
            current["close"]
        )

        next_price = float(
            next_candle["close"]
        )

        # ----------------------------------
        # BUY
        # ----------------------------------

        if signal == "BUY":

            buy_count += 1

            correct = (
                next_price > entry
            )

        # ----------------------------------
        # SELL
        # ----------------------------------

        elif signal == "SELL":

            sell_count += 1

            correct = (
                next_price < entry
            )

        # ----------------------------------
        # HOLD / UNKNOWN
        # ----------------------------------

        else:

            continue

        # ----------------------------------
        # WIN / LOSS
        # ----------------------------------

        if correct:

            wins += 1

        else:

            losses += 1

        # ----------------------------------
        # SAVE TRADE
        # ----------------------------------

        trades.append({

            "time":
                current["time"],

            "signal":
                signal,

            "entry":
                entry,

            "next_price":
                next_price,

            "correct":
                correct,

            "buy_probability":
                result.get(
                    "buy_probability",
                    0
                ),

            "sell_probability":
                result.get(
                    "sell_probability",
                    0
                )
        })

    # --------------------------------------
    # RESULT
    # --------------------------------------

    return {

        "total":
            len(trades),

        "wins":
            wins,

        "losses":
            losses,

        "buy":
            buy_count,

        "sell":
            sell_count,

        "trades":
            trades
    }


# ==========================================
# MAIN PROGRAM
# ==========================================

if __name__ == "__main__":

    print(
        "================================"
    )

    print(
        " MT5 RANDOM FOREST BACKTEST"
    )

    print(
        "================================"
    )

    # --------------------------------------
    # CONNECT MT5
    # --------------------------------------

    if not mt5.initialize():

        raise RuntimeError(
            f"MT5 gagal terhubung: {mt5.last_error()}"
        )

    print(
        "MT5 berhasil terhubung."
    )

    # --------------------------------------
    # GET DATA
    # --------------------------------------

    print(
        f"\nMengambil {CANDLES} candle "
        f"{SYMBOL} M5..."
    )

    df = get_data()

    print(
        f"Data berhasil diambil: "
        f"{len(df)} candle"
    )

    # --------------------------------------
    # INDICATORS
    # --------------------------------------

    print(
        "\nMenghitung indikator..."
    )

    df = calculate_indicators(df)

    print(
        "RSI / EMA berhasil dihitung."
    )

    # --------------------------------------
    # BACKTEST
    # --------------------------------------

    print(
        "\nMenjalankan RandomForest "
        "pada data TEST..."
    )

    result = run_backtest(df)

    # --------------------------------------
    # CALCULATE WINRATE
    # --------------------------------------

    total = result["total"]

    wins = result["wins"]

    losses = result["losses"]

    if total > 0:

        winrate = (
            wins / total * 100
        )

    else:

        winrate = 0

    # --------------------------------------
    # DISPLAY RESULT
    # --------------------------------------

    print(
        "\n========== HASIL ML BACKTEST =========="
    )

    print(
        "Symbol      :",
        SYMBOL
    )

    print(
        "Timeframe   : M5"
    )

    print(
        "Total trade :",
        total
    )

    print(
        "BUY         :",
        result["buy"]
    )

    print(
        "SELL        :",
        result["sell"]
    )

    print(
        "Win         :",
        wins
    )

    print(
        "Loss        :",
        losses
    )

    print(
        "Winrate     :",
        round(winrate, 2),
        "%"
    )

    print(
        "========================================"
    )

    # --------------------------------------
    # CLOSE MT5
    # --------------------------------------

    mt5.shutdown()

    print(
        "\nMT5 ditutup."
    )
