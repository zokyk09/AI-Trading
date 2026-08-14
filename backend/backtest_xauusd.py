import os
import joblib
import MetaTrader5 as mt5
import pandas as pd


# =========================================================
# CONFIG
# =========================================================

SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
CANDLES = 20000

CONFIDENCE = 55.0

LOT = 0.01

SL_DISTANCE = 1.00
TP_DISTANCE = 2.00


# =========================================================
# PATH MODEL
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

print("Model:")
print(MODEL_PATH)

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model tidak ditemukan: {MODEL_PATH}"
    )


# =========================================================
# LOAD MODEL
# =========================================================

print("\nMemuat model XAUUSD...")

model = joblib.load(
    MODEL_PATH
)

print("Model berhasil dimuat.")


# =========================================================
# CONNECT MT5
# =========================================================

print("\nMenghubungkan ke MT5...")

if not mt5.initialize():
    raise RuntimeError(
        f"MT5 gagal terhubung: {mt5.last_error()}"
    )

print("MT5 berhasil terhubung.")


# =========================================================
# SYMBOL INFO
# =========================================================

symbol_info = mt5.symbol_info(SYMBOL)

if symbol_info is None:
    mt5.shutdown()
    raise RuntimeError(
        f"{SYMBOL} tidak ditemukan."
    )

if not symbol_info.visible:
    if not mt5.symbol_select(SYMBOL, True):
        mt5.shutdown()
        raise RuntimeError(
            f"Gagal mengaktifkan {SYMBOL}."
        )


# =========================================================
# BROKER SPECIFICATION
# =========================================================

POINT = symbol_info.point
TICK_SIZE = symbol_info.trade_tick_size
TICK_VALUE = symbol_info.trade_tick_value

SPREAD_POINTS = symbol_info.spread
SPREAD_PRICE = SPREAD_POINTS * POINT

print("\n================================")
print("SPESIFIKASI BROKER")
print("================================")

print("Point          :", POINT)
print("Tick size      :", TICK_SIZE)
print("Tick value     :", TICK_VALUE)
print("Contract size  :", symbol_info.trade_contract_size)
print("Spread points  :", SPREAD_POINTS)
print("Spread price   :", SPREAD_PRICE)
print("Lot            :", LOT)

print("================================")


if TICK_SIZE <= 0 or TICK_VALUE <= 0:
    mt5.shutdown()
    raise RuntimeError(
        "Tick size / tick value broker tidak valid."
    )


# =========================================================
# DATA
# =========================================================

print(
    f"\nMengambil {CANDLES} candle "
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
        f"Gagal mengambil data: {mt5.last_error()}"
    )

df = pd.DataFrame(rates)

df["time"] = pd.to_datetime(
    df["time"],
    unit="s"
)

print(
    "Data:",
    len(df),
    "candle"
)


# =========================================================
# INDICATORS
# =========================================================

close = df["close"]

# EMA20
df["EMA20"] = close.ewm(
    span=20,
    adjust=False
).mean()

# EMA50
df["EMA50"] = close.ewm(
    span=50,
    adjust=False
).mean()

# RSI14
delta = close.diff()

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

df["RSI"] = (
    100 -
    (
        100 /
        (1 + rs)
    )
)

df = df.dropna().reset_index(
    drop=True
)


# =========================================================
# AI PREDICTION
# =========================================================

print("\nMenghitung prediction AI...")

features = df[
    [
        "RSI",
        "EMA20",
        "EMA50"
    ]
]

predictions = model.predict(
    features
)

probabilities = model.predict_proba(
    features
)

buy_probability = (
    probabilities[:, 1] * 100
)

sell_probability = (
    probabilities[:, 0] * 100
)

print("Prediction selesai.")


# =========================================================
# BACKTEST
# =========================================================

START_BALANCE = 1000.0

balance = START_BALANCE

wins = 0
losses = 0

buy_count = 0
sell_count = 0

gross_profit = 0.0
gross_loss = 0.0

trades = []


# =========================================================
# P/L FUNCTION
# =========================================================

def calculate_pnl(
    price_difference,
    volume
):
    """
    Menghitung P/L berdasarkan
    tick size dan tick value broker.
    """

    ticks = (
        price_difference /
        TICK_SIZE
    )

    return (
        ticks *
        TICK_VALUE *
        volume
    )


# =========================================================
# HEADER
# =========================================================

print("\n================================")
print("AI DIANA XAUUSD REALISTIC BACKTEST")
print("================================")

print(
    "Confidence :",
    CONFIDENCE,
    "%"
)

print(
    "Lot        :",
    LOT
)

print(
    "SL         : $",
    SL_DISTANCE
)

print(
    "TP         : $",
    TP_DISTANCE
)

print(
    "Spread     :",
    SPREAD_PRICE
)

print("================================")


# =========================================================
# LOOP
# =========================================================

i = 0

while i < len(df) - 2:

    prediction = predictions[i]

    if prediction == 1:

        signal = "BUY"

        confidence = float(
            buy_probability[i]
        )

    else:

        signal = "SELL"

        confidence = float(
            sell_probability[i]
        )


    # -----------------------------------------------------
    # CONFIDENCE FILTER
    # -----------------------------------------------------

    if confidence < CONFIDENCE:
        i += 1
        continue


    # -----------------------------------------------------
    # ENTRY CANDLE
    # -----------------------------------------------------

    entry_index = i + 1

    candle = df.iloc[
        entry_index
    ]

    market_open = float(
        candle["open"]
    )


    # -----------------------------------------------------
    # ENTRY + SPREAD
    # -----------------------------------------------------

    if signal == "BUY":

        # BUY masuk di ASK
        entry_price = (
            market_open +
            SPREAD_PRICE
        )

        sl = (
            entry_price -
            SL_DISTANCE
        )

        tp = (
            entry_price +
            TP_DISTANCE
        )

        buy_count += 1

    else:

        # SELL masuk di BID
        entry_price = market_open

        sl = (
            entry_price +
            SL_DISTANCE
        )

        tp = (
            entry_price -
            TP_DISTANCE
        )

        sell_count += 1


    # -----------------------------------------------------
    # SEARCH EXIT
    # -----------------------------------------------------

    exit_index = None
    exit_price = None
    result = None

    for j in range(
        entry_index + 1,
        len(df)
    ):

        current = df.iloc[j]

        high = float(
            current["high"]
        )

        low = float(
            current["low"]
        )


        if signal == "BUY":

            # Conservative:
            # jika SL dan TP sama-sama tersentuh
            # dalam candle yang sama,
            # anggap SL kena terlebih dahulu.

            if low <= sl:

                exit_index = j
                exit_price = sl
                result = "LOSS"

                break

            if high >= tp:

                exit_index = j
                exit_price = tp
                result = "WIN"

                break


        else:

            if high >= sl:

                exit_index = j
                exit_price = sl
                result = "LOSS"

                break

            if low <= tp:

                exit_index = j
                exit_price = tp
                result = "WIN"

                break


    # -----------------------------------------------------
    # TIDAK ADA EXIT
    # -----------------------------------------------------

    if result is None:
        break


    # -----------------------------------------------------
    # PRICE DIFFERENCE
    # -----------------------------------------------------

    if signal == "BUY":

        price_difference = (
            exit_price -
            entry_price
        )

    else:

        price_difference = (
            entry_price -
            exit_price
        )


    # -----------------------------------------------------
    # P/L
    # -----------------------------------------------------

    pnl = calculate_pnl(
        price_difference,
        LOT
    )


    balance += pnl


    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    if result == "WIN":

        wins += 1
        gross_profit += pnl

    else:

        losses += 1
        gross_loss += abs(pnl)


    trades.append({

        "time":
            str(candle["time"]),

        "signal":
            signal,

        "confidence":
            round(
                confidence,
                2
            ),

        "entry":
            round(
                entry_price,
                2
            ),

        "sl":
            round(
                sl,
                2
            ),

        "tp":
            round(
                tp,
                2
            ),

        "exit":
            round(
                exit_price,
                2
            ),

        "result":
            result,

        "pnl":
            round(
                pnl,
                4
            )
    })


    # -----------------------------------------------------
    # LOMPAT KE SETELAH POSISI
    # -----------------------------------------------------

    i = exit_index + 1


# =========================================================
# STATISTICS
# =========================================================

total_trades = (
    wins +
    losses
)

if total_trades > 0:

    winrate = (
        wins /
        total_trades
    ) * 100

else:

    winrate = 0.0


if gross_loss > 0:

    profit_factor = (
        gross_profit /
        gross_loss
    )

else:

    profit_factor = 0.0


net_profit = (
    balance -
    START_BALANCE
)


# =========================================================
# MAX DRAWDOWN
# =========================================================

equity = START_BALANCE
peak = equity
max_drawdown = 0.0

for trade in trades:

    equity += trade["pnl"]

    if equity > peak:
        peak = equity

    drawdown = (
        peak -
        equity
    )

    if drawdown > max_drawdown:
        max_drawdown = drawdown


# =========================================================
# RESULT
# =========================================================

print("\n")
print("================================")
print("HASIL BACKTEST XAUUSD REALISTIS")
print("================================")

print(
    "Total Trade :",
    total_trades
)

print(
    "BUY         :",
    buy_count
)

print(
    "SELL        :",
    sell_count
)

print(
    "WIN         :",
    wins
)

print(
    "LOSS        :",
    losses
)

print(
    "Winrate     :",
    round(
        winrate,
        2
    ),
    "%"
)

print(
    "Gross Profit:",
    "$",
    round(
        gross_profit,
        2
    )
)

print(
    "Gross Loss  :",
    "$",
    round(
        gross_loss,
        2
    )
)

print(
    "Profit Factor:",
    round(
        profit_factor,
        2
    )
)

print(
    "Net Profit  :",
    "$",
    round(
        net_profit,
        2
    )
)

print(
    "Max Drawdown:",
    "$",
    round(
        max_drawdown,
        2
    )
)

print(
    "Final Balance:",
    "$",
    round(
        balance,
        2
    )
)

print("================================")


# =========================================================
# SAVE CSV
# =========================================================

if trades:

    trades_df = pd.DataFrame(
        trades
    )

    output_path = os.path.join(
        BASE_DIR,
        "xauusd_realistic_backtest.csv"
    )

    trades_df.to_csv(
        output_path,
        index=False
    )

    print(
        "\nDetail trade disimpan:"
    )

    print(
        output_path
    )


# =========================================================
# CLOSE MT5
# =========================================================

mt5.shutdown()

print(
    "\nMT5 ditutup."
)