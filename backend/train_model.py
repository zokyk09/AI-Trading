import os
import joblib
import MetaTrader5 as mt5
import pandas as pd
import ta

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


def main() -> None:


    # =========================================================
    # CONFIG
    # =========================================================

    SYMBOL = "XAUUSD"
    TIMEFRAME = mt5.TIMEFRAME_M5
    CANDLES = 20000


    # =========================================================
    # PATH MODEL
    # =========================================================

    BASE_DIR = os.path.dirname(
        os.path.abspath(__file__)
    )

    MODEL_DIR = os.path.join(
        BASE_DIR,
        "..",
        "models"
    )

    os.makedirs(
        MODEL_DIR,
        exist_ok=True
    )

    MODEL_PATH = os.path.join(
        MODEL_DIR,
        "xauusd_model.pkl"
    )


    # =========================================================
    # CONNECT MT5
    # =========================================================

    print("Menghubungkan ke MT5...")

    if not mt5.initialize():

        raise RuntimeError(
            f"MT5 gagal terhubung: {mt5.last_error()}"
        )

    print("MT5 berhasil terhubung.")


    # =========================================================
    # CHECK SYMBOL
    # =========================================================

    symbol_info = mt5.symbol_info(
        SYMBOL
    )

    if symbol_info is None:

        mt5.shutdown()

        raise RuntimeError(
            f"{SYMBOL} tidak ditemukan di MT5"
        )


    # =========================================================
    # ACTIVATE SYMBOL
    # =========================================================

    if not symbol_info.visible:

        if not mt5.symbol_select(
            SYMBOL,
            True
        ):

            mt5.shutdown()

            raise RuntimeError(
                f"Gagal mengaktifkan {SYMBOL}"
            )


    # =========================================================
    # DOWNLOAD DATA
    # =========================================================

    print(
        f"Mengambil {CANDLES} candle "
        f"{SYMBOL} M5..."
    )

    rates = mt5.copy_rates_from_pos(
        SYMBOL,
        TIMEFRAME,
        0,
        CANDLES
    )

    if rates is None or len(rates) == 0:

        mt5.shutdown()

        raise RuntimeError(
            f"Gagal mengambil data: "
            f"{mt5.last_error()}"
        )


    df = pd.DataFrame(
        rates
    )

    df["time"] = pd.to_datetime(
        df["time"],
        unit="s"
    )

    print(
        "Data berhasil:",
        len(df),
        "candle"
    )


    # =========================================================
    # FEATURES
    # =========================================================

    close = df["close"]


    # RSI 14

    df["RSI"] = (
        ta.momentum.RSIIndicator(
            close,
            window=14
        ).rsi()
    )


    # EMA20

    df["EMA20"] = (
        ta.trend.EMAIndicator(
            close,
            window=20
        ).ema_indicator()
    )


    # EMA50

    df["EMA50"] = (
        ta.trend.EMAIndicator(
            close,
            window=50
        ).ema_indicator()
    )


    # =========================================================
    # TARGET
    # =========================================================

    # 1 = candle berikutnya naik
    # 0 = candle berikutnya turun

    df["Target"] = (
        df["close"].shift(-1)
        > df["close"]
    ).astype(int)


    # =========================================================
    # CLEAN DATA
    # =========================================================

    df = df.dropna()


    # =========================================================
    # FEATURES / TARGET
    # =========================================================

    X = df[
        [
            "RSI",
            "EMA20",
            "EMA50"
        ]
    ]

    y = df["Target"]


    # =========================================================
    # TARGET DISTRIBUTION
    # =========================================================

    print(
        "\nDistribusi target:"
    )

    print(
        y.value_counts()
    )

    print(
        "\nPersentase target:"
    )

    print(
        (
            y.value_counts(
                normalize=True
            ) * 100
        ).round(2)
    )


    # =========================================================
    # TIME SERIES SPLIT
    # =========================================================

    split_index = int(
        len(df) * 0.8
    )

    X_train = X.iloc[
        :split_index
    ]

    X_test = X.iloc[
        split_index:
    ]

    y_train = y.iloc[
        :split_index
    ]

    y_test = y.iloc[
        split_index:
    ]


    print(
        "\nData training:",
        len(X_train)
    )

    print(
        "Data testing :",
        len(X_test)
    )


    # =========================================================
    # RANDOM FOREST
    # =========================================================

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1
    )


    print(
        "\nTraining Random Forest..."
    )

    model.fit(
        X_train,
        y_train
    )


    # =========================================================
    # TEST
    # =========================================================

    pred = model.predict(
        X_test
    )

    accuracy = accuracy_score(
        y_test,
        pred
    )

    print(
        "\nAccuracy test:",
        round(
            accuracy * 100,
            2
        ),
        "%"
    )


    # =========================================================
    # PREDICTION DISTRIBUTION
    # =========================================================

    print(
        "\nDistribusi prediksi:"
    )

    print(
        pd.Series(
            pred
        ).value_counts()
    )


    # =========================================================
    # SAVE MODEL
    # =========================================================

    joblib.dump(
        model,
        MODEL_PATH
    )

    print(
        "\nModel XAUUSD berhasil disimpan:"
    )

    print(
        MODEL_PATH
    )


    # =========================================================
    # CLOSE MT5
    # =========================================================

    mt5.shutdown()

    print(
        "\nMT5 ditutup."
    )


if __name__ == "__main__":
    main()
