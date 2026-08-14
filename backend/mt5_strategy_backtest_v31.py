import os
import joblib
import MetaTrader5 as mt5
import pandas as pd


# ==========================================
# AI DIANA - STRATEGY BACKTEST V3.1
# RISK MANAGEMENT + R:R 1:2
# ==========================================

SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
CANDLES = 20000

# ==========================================
# ACCOUNT
# ==========================================

START_BALANCE = 1000.0
RISK_PERCENT = 1.0

# ==========================================
# STRATEGY
# ==========================================

SL_PIPS = 10
RR_RATIO = 2.0
TP_PIPS = SL_PIPS * RR_RATIO

MIN_PROBABILITY = 55.0

# Maksimal posisi ditahan 20 candle M5
MAX_HOLD_CANDLES = 20

# ==========================================
# EURUSD
# ==========================================

PIP_SIZE = 0.0001
PIP_VALUE_PER_LOT = 10.0


# ==========================================
# MODEL
# ==========================================

BASE_DIR = os.path.dirname(__file__)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "..",
    "models",
    "model.pkl"
)


print("Memuat model RandomForest...")

model = joblib.load(MODEL_PATH)

print("Model berhasil dimuat.")


# ==========================================
# DATA MT5
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
            f"Gagal mengambil data MT5: "
            f"{mt5.last_error()}"
        )

    df = pd.DataFrame(rates)

    df["time"] = pd.to_datetime(
        df["time"],
        unit="s"
    )

    return df


# ==========================================
# INDICATORS
# ==========================================

def calculate_indicators(df):

    df = df.copy()

    df["EMA20"] = df["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    df["EMA50"] = df["close"].ewm(
        span=50,
        adjust=False
    ).mean()

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
# MONEY MANAGEMENT
# ==========================================

def calculate_lot(balance):

    risk_money = (
        balance *
        RISK_PERCENT /
        100
    )

    risk_per_lot = (
        SL_PIPS *
        PIP_VALUE_PER_LOT
    )

    if risk_per_lot <= 0:

        return 0.01

    lot = (
        risk_money /
        risk_per_lot
    )

    # Minimum simulasi
    lot = max(
        lot,
        0.01
    )

    # Maksimum 2 digit
    lot = round(
        lot,
        2
    )

    return lot


# ==========================================
# BACKTEST V3.1
# ==========================================

def run_backtest(df):

    split_index = int(
        len(df) * 0.8
    )

    test_df = df.iloc[
        split_index:
    ].copy()

    test_df = test_df.dropna(
        subset=[
            "RSI",
            "EMA20",
            "EMA50"
        ]
    ).reset_index(
        drop=True
    )

    print(
        f"\nData sebelumnya : {split_index}"
    )

    print(
        f"Data testing    : {len(test_df)}"
    )


    # ======================================
    # BATCH PREDICTION
    # ======================================

    features = test_df[
        [
            "RSI",
            "EMA20",
            "EMA50"
        ]
    ]

    print(
        "\nAI Diana melakukan "
        "batch prediction..."
    )

    predictions = model.predict(
        features
    )

    probabilities = model.predict_proba(
        features
    )

    test_df["prediction"] = predictions

    test_df["sell_probability"] = (
        probabilities[:, 0] * 100
    )

    test_df["buy_probability"] = (
        probabilities[:, 1] * 100
    )

    print(
        "Batch prediction selesai."
    )


    # ======================================
    # ACCOUNT
    # ======================================

    balance = START_BALANCE

    peak_balance = balance

    max_drawdown = 0.0


    # ======================================
    # STATISTICS
    # ======================================

    total_trades = 0

    wins = 0

    losses = 0

    buy_count = 0

    sell_count = 0

    total_profit = 0.0

    total_loss = 0.0

    trades = []


    # ======================================
    # WALK FORWARD
    # ======================================

    i = 0

    while i < len(test_df) - 1:

        row = test_df.iloc[i]

        prediction = int(
            row["prediction"]
        )

        buy_probability = float(
            row["buy_probability"]
        )

        sell_probability = float(
            row["sell_probability"]
        )


        # ==================================
        # SIGNAL
        # ==================================

        if prediction == 1:

            signal = "BUY"

            probability = buy_probability

        else:

            signal = "SELL"

            probability = sell_probability


        # ==================================
        # CONFIDENCE FILTER
        # ==================================

        if probability < MIN_PROBABILITY:

            i += 1

            continue


        # ==================================
        # ENTRY
        # ==================================

        entry = float(
            row["close"]
        )

        lot = calculate_lot(
            balance
        )

        risk_money = (
            balance *
            RISK_PERCENT /
            100
        )


        # ==================================
        # SL / TP
        # ==================================

        if signal == "BUY":

            buy_count += 1

            sl_price = (
                entry -
                SL_PIPS * PIP_SIZE
            )

            tp_price = (
                entry +
                TP_PIPS * PIP_SIZE
            )

        else:

            sell_count += 1

            sl_price = (
                entry +
                SL_PIPS * PIP_SIZE
            )

            tp_price = (
                entry -
                TP_PIPS * PIP_SIZE
            )


        # ==================================
        # SEARCH EXIT
        # ==================================

        result = "TIMEOUT"

        exit_price = entry

        exit_index = min(
            i + MAX_HOLD_CANDLES,
            len(test_df) - 1
        )

        for j in range(
            i + 1,
            exit_index + 1
        ):

            candle = test_df.iloc[j]

            high = float(
                candle["high"]
            )

            low = float(
                candle["low"]
            )


            # ==================================
            # BUY
            # ==================================

            if signal == "BUY":

                # Conservative:
                # jika SL dan TP terkena
                # pada candle yang sama,
                # anggap SL terlebih dahulu.

                if low <= sl_price:

                    result = "LOSS"

                    exit_price = sl_price

                    exit_index = j

                    break

                if high >= tp_price:

                    result = "WIN"

                    exit_price = tp_price

                    exit_index = j

                    break


            # ==================================
            # SELL
            # ==================================

            else:

                if high >= sl_price:

                    result = "LOSS"

                    exit_price = sl_price

                    exit_index = j

                    break

                if low <= tp_price:

                    result = "WIN"

                    exit_price = tp_price

                    exit_index = j

                    break


        # ==================================
        # TIMEOUT
        # ==================================

        if result == "TIMEOUT":

            exit_price = float(
                test_df.iloc[
                    exit_index
                ]["close"]
            )

            if signal == "BUY":

                if exit_price > entry:

                    result = "WIN"

                elif exit_price < entry:

                    result = "LOSS"

                else:

                    result = "BREAKEVEN"

            else:

                if exit_price < entry:

                    result = "WIN"

                elif exit_price > entry:

                    result = "LOSS"

                else:

                    result = "BREAKEVEN"


        # ==================================
        # PROFIT / LOSS
        # ==================================

        if result == "WIN":

            # TP = 2R
            profit = (
                risk_money *
                RR_RATIO
            )

        elif result == "LOSS":

            # SL = -1R
            profit = -risk_money

        else:

            profit = 0.0


        # ==================================
        # ACCOUNT UPDATE
        # ==================================

        balance += profit

        total_trades += 1


        if result == "WIN":

            wins += 1

            total_profit += profit

        elif result == "LOSS":

            losses += 1

            total_loss += abs(
                profit
            )


        # ==================================
        # DRAWDOWN
        # ==================================

        if balance > peak_balance:

            peak_balance = balance

        drawdown = (
            peak_balance -
            balance
        )

        if drawdown > max_drawdown:

            max_drawdown = drawdown


        # ==================================
        # SAVE TRADE
        # ==================================

        trades.append({

            "time":
                row["time"],

            "signal":
                signal,

            "probability":
                round(
                    probability,
                    2
                ),

            "lot":
                lot,

            "entry":
                entry,

            "SL":
                sl_price,

            "TP":
                tp_price,

            "result":
                result,

            "profit":
                round(
                    profit,
                    2
                ),

            "balance":
                round(
                    balance,
                    2
                )
        })


        # ==================================
        # NEXT TRADE
        # ==================================

        i = exit_index + 1


    # ======================================
    # FINAL STATISTICS
    # ======================================

    if total_trades > 0:

        winrate = (
            wins /
            total_trades *
            100
        )

    else:

        winrate = 0


    if total_loss > 0:

        profit_factor = (
            total_profit /
            total_loss
        )

    else:

        profit_factor = 0


    net_profit = (
        balance -
        START_BALANCE
    )


    return {

        "total_trades":
            total_trades,

        "wins":
            wins,

        "losses":
            losses,

        "buy":
            buy_count,

        "sell":
            sell_count,

        "winrate":
            winrate,

        "profit":
            net_profit,

        "profit_factor":
            profit_factor,

        "max_drawdown":
            max_drawdown,

        "balance":
            balance,

        "trades":
            trades
    }


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":

    print(
        "========================================"
    )

    print(
        " MT5 STRATEGY BACKTEST V3.1 - AI DIANA"
    )

    print(
        "========================================"
    )

    print(
        f"Symbol       : {SYMBOL}"
    )

    print(
        "Timeframe    : M5"
    )

    print(
        f"Risk         : {RISK_PERCENT}%"
    )

    print(
        f"SL           : {SL_PIPS} pips"
    )

    print(
        f"TP           : {TP_PIPS} pips"
    )

    print(
        f"R:R          : 1:{RR_RATIO}"
    )

    print(
        f"Confidence   : >= {MIN_PROBABILITY}%"
    )

    print(
        f"Modal awal   : ${START_BALANCE:.2f}"
    )


    # ======================================
    # MT5
    # ======================================

    if not mt5.initialize():

        raise RuntimeError(
            f"MT5 gagal terhubung: "
            f"{mt5.last_error()}"
        )


    try:

        print(
            "\nMT5 berhasil terhubung."
        )


        print(
            f"\nMengambil {CANDLES} candle..."
        )

        df = get_data()

        print(
            f"Data berhasil diambil: "
            f"{len(df)} candle"
        )


        print(
            "\nMenghitung indikator..."
        )

        df = calculate_indicators(
            df
        )

        print(
            "RSI / EMA berhasil dihitung."
        )


        result = run_backtest(
            df
        )


        # ==================================
        # RESULT
        # ==================================

        print(
            "\n========================================"
        )

        print(
            "       HASIL BACKTEST V3.1"
        )

        print(
            "========================================"
        )

        print(
            "Total trade   :",
            result["total_trades"]
        )

        print(
            "BUY           :",
            result["buy"]
        )

        print(
            "SELL          :",
            result["sell"]
        )

        print(
            "WIN           :",
            result["wins"]
        )

        print(
            "LOSS          :",
            result["losses"]
        )

        print(
            "Winrate       :",
            round(
                result["winrate"],
                2
            ),
            "%"
        )

        print(
            "Net Profit    : $",
            round(
                result["profit"],
                2
            )
        )

        print(
            "Profit Factor :",
            round(
                result["profit_factor"],
                2
            )
        )

        print(
            "Max Drawdown  : $",
            round(
                result["max_drawdown"],
                2
            )
        )

        print(
            "Saldo Akhir   : $",
            round(
                result["balance"],
                2
            )
        )

        print(
            "========================================"
        )


    finally:

        mt5.shutdown()

        print(
            "\nMT5 ditutup."
        )