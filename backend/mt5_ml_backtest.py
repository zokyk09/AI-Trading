import os
import joblib
import MetaTrader5 as mt5
import pandas as pd


# ==========================================
# CONFIGURATION
# ==========================================

SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
CANDLES = 20000

BASE_DIR = os.path.dirname(__file__)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "..",
    "models",
    "model.pkl"
)


# ==========================================
# LOAD MODEL
# ==========================================

print("Memuat model RandomForest...")

model = joblib.load(MODEL_PATH)

print("Model berhasil dimuat.")


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

    # EMA 20
    df["EMA20"] = df["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    # EMA 50
    df["EMA50"] = df["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    # RSI 14
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
# RUN FAST BACKTEST
# ==========================================

def run_backtest(df):

    split_index = int(len(df) * 0.8)

    test_df = df.iloc[split_index:].copy()

    print(f"\nData sebelumnya : {split_index}")
    print(f"Data testing    : {len(test_df)}")

    # Buang data indikator yang kosong
    test_df = test_df.dropna(
        subset=["RSI", "EMA20", "EMA50"]
    ).copy()

    # Kita butuh candle berikutnya
    test_df["next_close"] = test_df["close"].shift(-1)

    test_df = test_df.dropna(
        subset=["next_close"]
    ).copy()

    features = test_df[
        ["RSI", "EMA20", "EMA50"]
    ]

    print(
        f"\nMenjalankan batch prediction "
        f"untuk {len(features)} candle..."
    )

    # ======================================
    # PREDICT SEMUA DATA SEKALIGUS
    # ======================================

    predictions = model.predict(features)

    probabilities = model.predict_proba(features)

    test_df["prediction"] = predictions

    # Asumsi class 0 = SELL dan class 1 = BUY
    test_df["sell_probability"] = probabilities[:, 0] * 100
    test_df["buy_probability"] = probabilities[:, 1] * 100

    print("Batch prediction selesai.")

    # ======================================
    # SIGNAL
    # ======================================

    test_df["signal"] = test_df["prediction"].map({
        1: "BUY",
        0: "SELL"
    })

    # ======================================
    # CHECK RESULT
    # ======================================

    buy_correct = (
        (test_df["signal"] == "BUY")
        &
        (test_df["next_close"] > test_df["close"])
    )

    sell_correct = (
        (test_df["signal"] == "SELL")
        &
        (test_df["next_close"] < test_df["close"])
    )

    test_df["correct"] = buy_correct | sell_correct

    wins = int(test_df["correct"].sum())
    total = len(test_df)
    losses = total - wins

    buy_count = int(
        (test_df["signal"] == "BUY").sum()
    )

    sell_count = int(
        (test_df["signal"] == "SELL").sum()
    )

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "buy": buy_count,
        "sell": sell_count
    }


# ==========================================
# MAIN PROGRAM
# ==========================================

if __name__ == "__main__":

    print("================================")
    print(" MT5 RANDOM FOREST FAST BACKTEST")
    print("================================")

    if not mt5.initialize():

        raise RuntimeError(
            f"MT5 gagal terhubung: {mt5.last_error()}"
        )

    try:

        print("MT5 berhasil terhubung.")

        print(
            f"\nMengambil {CANDLES} candle "
            f"{SYMBOL} M5..."
        )

        df = get_data()

        print(
            f"Data berhasil diambil: "
            f"{len(df)} candle"
        )

        print("\nMenghitung indikator...")

        df = calculate_indicators(df)

        print("RSI / EMA berhasil dihitung.")

        result = run_backtest(df)

        total = result["total"]
        wins = result["wins"]
        losses = result["losses"]

        if total > 0:
            winrate = wins / total * 100
        else:
            winrate = 0

        print(
            "\n========== HASIL ML BACKTEST =========="
        )

        print("Symbol      :", SYMBOL)
        print("Timeframe   : M5")
        print("Total trade :", total)
        print("BUY         :", result["buy"])
        print("SELL        :", result["sell"])
        print("Win         :", wins)
        print("Loss        :", losses)
        print(
            "Winrate     :",
            round(winrate, 2),
            "%"
        )

        print(
            "========================================"
        )

    finally:

        mt5.shutdown()

        print("\nMT5 ditutup.")