import yfinance as yf
from strategy import analyze




def main() -> None:
    data = yf.download(
        "BTC-USD",
        period="1mo",
        interval="1h"
    )


    result = analyze(data)


    print("=== AI TRADING ===")

    print("Price :", result["price"])
    print("RSI   :", result["rsi"])
    print("EMA   :", result["ema"])
    print("Trend :", result["trend"])
    print("Score :", result["score"], "%")
    print("Signal:", result["signal"])


if __name__ == "__main__":
    main()
