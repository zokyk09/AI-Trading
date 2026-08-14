import os
import joblib
import pandas as pd

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "model.pkl"
)

model = joblib.load(MODEL_PATH)


def predict_signal(rsi, ema20, ema50):

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

    prediction = model.predict(sample)[0]

    probability = model.predict_proba(sample)[0]

    return {
        "signal":
            "BUY"
            if prediction == 1
            else "SELL",

        "buy_probability":
            round(
                float(probability[1]) * 100,
                2
            ),

        "sell_probability":
            round(
                float(probability[0]) * 100,
                2
            )
    }
