import yfinance as yf
from strategy import analyze




def main() -> None:
    # ambil data BTC 3 bulan
    data = yf.download(
        "BTC-USD",
        period="3mo",
        interval="1h"
    )


    # rapikan data
    if len(data["Close"].shape) > 1:
        data["Close"] = data["Close"].iloc[:,0]


    balance = 1000
    position = 0

    buy_price = 0

    wins = 0
    losses = 0


    for i in range(50, len(data)):

        current = data.iloc[:i]

        result = analyze(current)

        price = result["price"]
        signal = result["signal"]


        # beli
        if signal == "BUY" and position == 0:

            position = balance / price
            buy_price = price

            print("BUY at:", price)



        # jual
        elif signal == "SELL" and position > 0:

            balance = position * price

            profit = price - buy_price

            if profit > 0:
                wins += 1
            else:
                losses += 1

            print("SELL at:", price)

            position = 0



    # hitung nilai akhir

    if position > 0:
        balance = position * data["Close"].iloc[-1]


    total_trade = wins + losses


    print("\n=== BACKTEST RESULT ===")
    print("Modal awal : $1000")
    print("Saldo akhir:", round(balance,2))

    if total_trade > 0:
        winrate = wins / total_trade * 100
    else:
        winrate = 0


    print("Trade :", total_trade)
    print("Win   :", wins)
    print("Loss  :", losses)
    print("Winrate:", round(winrate,2), "%")


if __name__ == "__main__":
    main()
