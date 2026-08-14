import MetaTrader5 as mt5
import pandas as pd
import ta
from strategy import analyze


SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
CANDLES = 5000

INITIAL_BALANCE = 1000


def get_mt5_data():
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

    # strategy.py kita hanya membutuhkan Close
    df = df[["time", "close"]]

    df.rename(
        columns={"close": "Close"},
        inplace=True
    )

    return df


def run_backtest(data):

    balance = INITIAL_BALANCE
    position = 0
    buy_price = 0

    wins = 0
    losses = 0

    trades = []

    for i in range(50, len(data)):

        current = data.iloc[:i]

        result = analyze(current)

        price = result["price"]
        signal = result["signal"]

        # BUY
        if signal == "BUY" and position == 0:

            position = balance / price
            buy_price = price

            trades.append({
                "type": "BUY",
                "price": price,
                "time": data["time"].iloc[i]
            })

        # SELL
        elif signal == "SELL" and position > 0:

            balance = position * price

            profit = price - buy_price

            if profit > 0:
                wins += 1
            else:
                losses += 1

            trades.append({
                "type": "SELL",
                "price": price,
                "time": data["time"].iloc[i],
                "profit": profit
            })

            position = 0

    # Jika masih ada posisi
    if position > 0:

        final_price = data["Close"].iloc[-1]

        balance = position * final_price

    total_trade = wins + losses

    if total_trade > 0:
        winrate = wins / total_trade * 100
    else:
        winrate = 0

    return {
        "initial_balance": INITIAL_BALANCE,
        "final_balance": balance,
        "profit": balance - INITIAL_BALANCE,
        "trades": total_trade,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "trade_history": trades
    }


if __name__ == "__main__":

    print("================================")
    print(" MT5 STRATEGY BACKTEST")
    print("================================")

    print("\nMenghubungkan ke MT5...")

    if not mt5.initialize():

        raise RuntimeError(
            f"MT5 gagal terhubung: {mt5.last_error()}"
        )

    print("MT5 berhasil terhubung.")

    print(f"\nMengambil data {SYMBOL} M5...")

    data = get_mt5_data()

    print(f"Jumlah candle: {len(data)}")

    print("\nMenjalankan backtest...")

    result = run_backtest(data)

    print("\n========== HASIL BACKTEST ==========")

    print(
        "Modal awal : $",
        round(result["initial_balance"], 2)
    )

    print(
        "Saldo akhir:",
        round(result["final_balance"], 2)
    )

    print(
        "Profit/Loss:",
        round(result["profit"], 2)
    )

    print(
        "Total trade:",
        result["trades"]
    )

    print(
        "Win        :",
        result["wins"]
    )

    print(
        "Loss       :",
        result["losses"]
    )

    print(
        "Winrate    :",
        round(result["winrate"], 2),
        "%"
    )

    mt5.shutdown()

    print("\nMT5 ditutup.")