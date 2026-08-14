import os
import time
import joblib
import MetaTrader5 as mt5
import pandas as pd


# ==========================================
# AI DIANA - LIVE V2 DEMO
# ==========================================

SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M5

LOT = 0.01

SL_PIPS = 10
TP_PIPS = 10

MIN_PROBABILITY = 55.0

# ==========================================
# KEAMANAN
# ==========================================

# True  = hanya membaca sinyal, TIDAK membuka order
# False = boleh mengirim order ke MT5
DRY_RUN = True

# Cek setiap 10 detik
CHECK_SECONDS = 10

MAGIC = 20260808


# ==========================================
# MODEL
# ==========================================

BASE_DIR = os.path.dirname(__file__)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "model.pkl"
)

# Jika model.pkl ada di folder project utama
if not os.path.exists(MODEL_PATH):

    MODEL_PATH = os.path.join(
        BASE_DIR,
        "..",
        "models",
        "model.pkl"
    )


print("Memuat model AI Diana...")

model = joblib.load(
    MODEL_PATH
)

print("Model berhasil dimuat.")


# ==========================================
# PIP
# ==========================================

PIP_SIZE = 0.0001


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

    rs = avg_gain / avg_loss

    df["RSI"] = 100 - (
        100 / (1 + rs)
    )

    return df


# ==========================================
# GET DATA
# ==========================================

def get_data():

    rates = mt5.copy_rates_from_pos(
        SYMBOL,
        TIMEFRAME,
        0,
        200
    )

    if rates is None:

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

    return df


# ==========================================
# AI PREDICTION
# ==========================================

def get_signal():

    df = get_data()

    df = calculate_indicators(
        df
    )

    # Gunakan candle yang SUDAH SELESAI
    current = df.iloc[-2]

    if pd.isna(current["RSI"]):

        return None

    sample = pd.DataFrame(
        [[
            float(current["RSI"]),
            float(current["EMA20"]),
            float(current["EMA50"])
        ]],
        columns=[
            "RSI",
            "EMA20",
            "EMA50"
        ]
    )

    prediction = model.predict(
        sample
    )[0]

    probability = model.predict_proba(
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

    return {

        "time":
            current["time"],

        "signal":
            signal,

        "confidence":
            confidence,

        "buy_probability":
            buy_probability,

        "sell_probability":
            sell_probability,

        "price":
            float(current["close"])
    }


# ==========================================
# CHECK EXISTING POSITION
# ==========================================

def has_position():

    positions = mt5.positions_get(
        symbol=SYMBOL
    )

    if positions is None:

        return False

    return len(positions) > 0


# ==========================================
# SEND ORDER
# ==========================================

def send_order(signal):

    tick = mt5.symbol_info_tick(
        SYMBOL
    )

    if tick is None:

        print(
            "Gagal mendapatkan harga."
        )

        return

    if signal == "BUY":

        order_type = (
            mt5.ORDER_TYPE_BUY
        )

        price = tick.ask

        sl = (
            price -
            SL_PIPS * PIP_SIZE
        )

        tp = (
            price +
            TP_PIPS * PIP_SIZE
        )

    else:

        order_type = (
            mt5.ORDER_TYPE_SELL
        )

        price = tick.bid

        sl = (
            price +
            SL_PIPS * PIP_SIZE
        )

        tp = (
            price -
            TP_PIPS * PIP_SIZE
        )

    digits = mt5.symbol_info(
        SYMBOL
    ).digits

    price = round(
        price,
        digits
    )

    sl = round(
        sl,
        digits
    )

    tp = round(
        tp,
        digits
    )

    request = {

        "action":
            mt5.TRADE_ACTION_DEAL,

        "symbol":
            SYMBOL,

        "volume":
            LOT,

        "type":
            order_type,

        "price":
            price,

        "sl":
            sl,

        "tp":
            tp,

        "deviation":
            20,

        "magic":
            MAGIC,

        "comment":
            "AI DIANA V2",

        "type_time":
            mt5.ORDER_TIME_GTC,

        "type_filling":
            mt5.ORDER_FILLING_RETURN
    }

    # ======================================
    # ORDER CHECK
    # ======================================

    check = mt5.order_check(
        request
    )

    print(
        "\nORDER CHECK:"
    )

    print(
        check
    )

    if check is None:

        print(
            "Order check gagal:",
            mt5.last_error()
        )

        return

    # ======================================
    # SEND
    # ======================================

    result = mt5.order_send(
        request
    )

    print(
        "\nORDER RESULT:"
    )

    print(
        result
    )

    if result is not None:

        print(
            "Retcode:",
            result.retcode
        )


# ==========================================
# MAIN
# ==========================================

print(
    "========================================"
)

print(
    " AI DIANA - LIVE V2 DEMO"
)

print(
    "========================================"
)

print(
    f"Symbol     : {SYMBOL}"
)

print(
    "Timeframe  : M5"
)

print(
    f"Lot        : {LOT}"
)

print(
    f"SL         : {SL_PIPS} pip"
)

print(
    f"TP         : {TP_PIPS} pip"
)

print(
    f"Confidence : >= {MIN_PROBABILITY}%"
)

print(
    f"DRY RUN    : {DRY_RUN}"
)

print(
    "========================================"
)


# ==========================================
# CONNECT MT5
# ==========================================

if not mt5.initialize():

    raise RuntimeError(
        f"MT5 gagal terhubung: "
        f"{mt5.last_error()}"
    )


try:

    print(
        "\nMT5 berhasil terhubung."
    )

    account = mt5.account_info()

    if account is not None:

        print(
            "Account :",
            account.login
        )

        print(
            "Balance :",
            account.balance
        )

        print(
            "Equity  :",
            account.equity
        )

    if not mt5.symbol_select(
        SYMBOL,
        True
    ):

        raise RuntimeError(
            f"Gagal memilih {SYMBOL}"
        )

    last_candle_time = None

    while True:

        try:

            signal_data = get_signal()

            if signal_data is None:

                print(
                    "Data AI belum tersedia."
                )

                time.sleep(
                    CHECK_SECONDS
                )

                continue

            candle_time = (
                signal_data["time"]
            )

            # ==================================
            # HANYA PROSES CANDLE BARU
            # ==================================

            if candle_time == last_candle_time:

                time.sleep(
                    CHECK_SECONDS
                )

                continue

            last_candle_time = (
                candle_time
            )

            print(
                "\n========================================"
            )

            print(
                "CANDLE BARU"
            )

            print(
                "Time       :",
                candle_time
            )

            print(
                "Signal     :",
                signal_data["signal"]
            )

            print(
                "Confidence :",
                round(
                    signal_data["confidence"],
                    2
                ),
                "%"
            )

            print(
                "BUY Prob   :",
                round(
                    signal_data["buy_probability"],
                    2
                ),
                "%"
            )

            print(
                "SELL Prob  :",
                round(
                    signal_data["sell_probability"],
                    2
                ),
                "%"
            )

            print(
                "Price      :",
                signal_data["price"]
            )

            # ==================================
            # CONFIDENCE
            # ==================================

            if (
                signal_data["confidence"]
                < MIN_PROBABILITY
            ):

                print(
                    "STATUS     : HOLD - confidence rendah"
                )

                time.sleep(
                    CHECK_SECONDS
                )

                continue

            # ==================================
            # EXISTING POSITION
            # ==================================

            if has_position():

                print(
                    "STATUS     : HOLD - "
                    "masih ada posisi terbuka"
                )

                time.sleep(
                    CHECK_SECONDS
                )

                continue

            # ==================================
            # SIGNAL VALID
            # ==================================

            print(
                "STATUS     : SIGNAL VALID"
            )

            if DRY_RUN:

                print(
                    "MODE       : DRY RUN"
                )

                print(
                    "ORDER      : TIDAK DIKIRIM"
                )

            else:

                print(
                    "MODE       : LIVE DEMO"
                )

                send_order(
                    signal_data["signal"]
                )

            print(
                "========================================"
            )

        except Exception as e:

            print(
                "\nERROR:"
            )

            print(
                repr(e)
            )

        time.sleep(
            CHECK_SECONDS
        )


finally:

    mt5.shutdown()

    print(
        "\nMT5 ditutup."
    )