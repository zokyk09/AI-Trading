from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import MetaTrader5 as mt5
import threading
import time
from datetime import datetime, timedelta

from predict import predict_signal
from backend.mt5_connector import (
    initialize_mt5,
    analyze_market,
)

# =========================================================
# CONFIG
# =========================================================

SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M5

MANUAL_VOLUME = 0.01
AUTO_VOLUME = 0.01
AUTO_CONFIDENCE = 55.0
AUTO_MAGIC = 20260810

SL_DOLLAR = 1.00
TP_DOLLAR = 2.00

# =========================================================
# AUTO STATE
# =========================================================

auto_enabled = False
auto_last_candle = None
auto_stop_event = threading.Event()
auto_thread = None

# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="AI Diana Trading API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ORDER HELPER
# =========================================================

def place_demo_order(
    symbol: str,
    side: str,
    volume: float,
    magic: int,
    comment: str,
):
    side = str(side).upper()

    if side not in ["BUY", "SELL"]:
        return {
            "success": False,
            "message": "Side harus BUY atau SELL"
        }

    if volume != 0.01:
        return {
            "success": False,
            "message": "Untuk DEMO testing, volume wajib 0.01 lot"
        }

    account = mt5.account_info()

    if account is None:
        return {
            "success": False,
            "message": "Akun MT5 tidak terhubung"
        }

    # DEMO ONLY
    if account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        return {
            "success": False,
            "message": "Order diblokir: akun bukan DEMO"
        }

    terminal = mt5.terminal_info()

    if terminal is None:
        return {
            "success": False,
            "message": "Terminal MT5 tidak tersedia"
        }

    if not terminal.trade_allowed:
        return {
            "success": False,
            "message": "Trading MT5 tidak diizinkan"
        }

    symbol_info = mt5.symbol_info(symbol)

    if symbol_info is None:
        return {
            "success": False,
            "message": f"Symbol {symbol} tidak ditemukan"
        }

    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            return {
                "success": False,
                "message": f"Gagal mengaktifkan {symbol}"
            }

        symbol_info = mt5.symbol_info(symbol)

        if symbol_info is None:
            return {
                "success": False,
                "message": f"Informasi {symbol} tidak tersedia"
            }

    tick = mt5.symbol_info_tick(symbol)

    if tick is None:
        return {
            "success": False,
            "message": f"Tidak ada tick untuk {symbol}"
        }

    if side == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
    else:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid

    # XAUUSD: $1 SL / $2 TP
    # point=0.01 pada broker user -> 100 points = $1
    point = symbol_info.point

    sl_distance = SL_DOLLAR
    tp_distance = TP_DOLLAR

    if side == "BUY":
        sl = price - sl_distance
        tp = price + tp_distance
    else:
        sl = price + sl_distance
        tp = price - tp_distance

    digits = symbol_info.digits

    price = round(price, digits)
    sl = round(sl, digits)
    tp = round(tp, digits)

    # Broker-supported filling mode
    filling_mode = symbol_info.filling_mode

    if filling_mode & 1:
        type_filling = mt5.ORDER_FILLING_FOK
    elif filling_mode & 2:
        type_filling = mt5.ORDER_FILLING_IOC
    else:
        type_filling = mt5.ORDER_FILLING_RETURN

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": magic,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": type_filling,
    }

    check = mt5.order_check(request)

    if check is None:
        return {
            "success": False,
            "message": "order_check gagal",
            "error": str(mt5.last_error())
        }

    print("ORDER CHECK:", check)

    if check.retcode != 0:
        return {
            "success": False,
            "message": "Order ditolak oleh order_check",
            "retcode": check.retcode,
            "comment": check.comment
        }

    result = mt5.order_send(request)

    if result is None:
        return {
            "success": False,
            "message": "order_send gagal",
            "error": str(mt5.last_error())
        }

    print("ORDER RESULT:", result)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return {
            "success": False,
            "message": "Order gagal dieksekusi",
            "retcode": result.retcode,
            "comment": result.comment
        }

    return {
        "success": True,
        "message": f"{side} {symbol} berhasil dikirim",
        "symbol": symbol,
        "side": side,
        "volume": volume,
        "price": price,
        "sl": sl,
        "tp": tp,
        "order": int(result.order),
        "deal": int(result.deal),
        "retcode": result.retcode,
        "comment": result.comment
    }


# =========================================================
# AUTO WORKER
# =========================================================

def has_open_xau_position():
    positions = mt5.positions_get(
        symbol=SYMBOL
    )

    return positions is not None and len(positions) > 0


def auto_worker():
    global auto_last_candle

    print("AI Diana AUTO worker siap.")

    while not auto_stop_event.is_set():

        try:
            if not auto_enabled:
                time.sleep(1)
                continue

            account = mt5.account_info()

            if account is None:
                time.sleep(5)
                continue

            if account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
                print("AUTO diblokir: akun bukan DEMO.")
                time.sleep(5)
                continue

            terminal = mt5.terminal_info()

            if terminal is None or not terminal.trade_allowed:
                time.sleep(5)
                continue

            # Hanya 1 posisi XAUUSD pada satu waktu
            if has_open_xau_position():
                time.sleep(5)
                continue

            result = analyze_market(SYMBOL)

            ai = result["AI_result"]

            signal = ai["signal"]

            if signal == "BUY":
                confidence = float(
                    ai["buy_probability"]
                )
            else:
                confidence = float(
                    ai["sell_probability"]
                )

            # Candle id dikirim oleh mt5_connector.
            candle_time = result.get(
                "candle_time"
            )

            if candle_time is None:
                time.sleep(5)
                continue

            # Jangan entry dua kali pada candle yang sama.
            if candle_time == auto_last_candle:
                time.sleep(5)
                continue

            auto_last_candle = candle_time

            print(
                f"AUTO SIGNAL: {signal} "
                f"confidence={confidence:.2f}% "
                f"candle={candle_time}"
            )

            if confidence < AUTO_CONFIDENCE:
                time.sleep(5)
                continue

            order = place_demo_order(
                symbol=SYMBOL,
                side=signal,
                volume=AUTO_VOLUME,
                magic=AUTO_MAGIC,
                comment="AI Diana AUTO Demo"
            )

            print(
                "AUTO ORDER:",
                order
            )

        except Exception as e:
            print(
                "AUTO WORKER ERROR:",
                repr(e)
            )

        time.sleep(5)


# =========================================================
# STARTUP
# =========================================================

@app.on_event("startup")
def startup():
    global auto_thread

    try:
        initialize_mt5()

        print(
            "AI Diana API: MT5 siap."
        )

        auto_stop_event.clear()

        auto_thread = threading.Thread(
            target=auto_worker,
            daemon=True,
        )

        auto_thread.start()

    except Exception as e:
        print(
            "AI Diana API: MT5 gagal terhubung:",
            e
        )


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return {
        "status": "Online",
        "message": "AI Diana Trading Ready"
    }


# =========================================================
# STATUS
# =========================================================

@app.get("/api/status")
def api_status():

    terminal = mt5.terminal_info()

    if terminal is None:
        return {
            "connected": False,
            "message": "MT5 tidak terhubung",
            "trade_allowed": False,
            "auto_enabled": auto_enabled,
        }

    return {
        "connected": True,
        "message": "MT5 Connected",
        "trade_allowed": bool(
            terminal.trade_allowed
        ),
        "auto_enabled": auto_enabled,
        "auto_confidence": AUTO_CONFIDENCE,
        "auto_symbol": SYMBOL,
        "auto_volume": AUTO_VOLUME,
    }


# =========================================================
# AUTO CONTROL
# =========================================================

@app.get("/api/auto")
def api_auto_get():
    return {
        "enabled": auto_enabled,
        "symbol": SYMBOL,
        "timeframe": "M5",
        "confidence": AUTO_CONFIDENCE,
        "volume": AUTO_VOLUME,
        "sl": SL_DOLLAR,
        "tp": TP_DOLLAR,
        "mode": "DEMO_ONLY",
    }


@app.post("/api/auto")
def api_auto(data: dict):
    global auto_enabled
    global auto_last_candle

    requested = bool(
        data.get("enabled", False)
    )

    if requested:

        account = mt5.account_info()

        if account is None:
            return {
                "success": False,
                "enabled": False,
                "message": "Akun MT5 tidak terhubung"
            }

        if (
            account.trade_mode
            != mt5.ACCOUNT_TRADE_MODE_DEMO
        ):
            return {
                "success": False,
                "enabled": False,
                "message": "AUTO hanya boleh pada akun DEMO"
            }

        terminal = mt5.terminal_info()

        if terminal is None:
            return {
                "success": False,
                "enabled": False,
                "message": "Terminal MT5 tidak tersedia"
            }

        if not terminal.trade_allowed:
            return {
                "success": False,
                "enabled": False,
                "message": "Trading MT5 tidak diizinkan"
            }

        symbol_info = mt5.symbol_info(SYMBOL)

        if symbol_info is None:
            return {
                "success": False,
                "enabled": False,
                "message": "XAUUSD tidak ditemukan"
            }

        auto_last_candle = None
        auto_enabled = True

        print(
            "AI DIANA AUTO: ON | "
            f"{SYMBOL} M5 | "
            f"confidence >= {AUTO_CONFIDENCE}% | "
            f"lot {AUTO_VOLUME}"
        )

        return {
            "success": True,
            "enabled": True,
            "message": "AUTO TRADING DEMO AKTIF",
            "symbol": SYMBOL,
            "timeframe": "M5",
            "confidence": AUTO_CONFIDENCE,
            "volume": AUTO_VOLUME,
            "sl": SL_DOLLAR,
            "tp": TP_DOLLAR,
        }

    auto_enabled = False
    auto_last_candle = None

    print("AI DIANA AUTO: OFF")

    return {
        "success": True,
        "enabled": False,
        "message": "AUTO TRADING DIMATIKAN"
    }


# =========================================================
# ACCOUNT
# =========================================================

@app.get("/api/account")
def api_account():

    account = mt5.account_info()

    if account is None:
        return {
            "connected": False
        }

    return {
        "connected": True,
        "login": account.login,
        "balance": float(
            account.balance
        ),
        "equity": float(
            account.equity
        ),
        "profit": float(
            account.profit
        ),
        "currency": account.currency
    }


# =========================================================
# MARKET
# =========================================================

@app.get("/api/market")
def api_market():

    return analyze_market(
        SYMBOL
    )


# =========================================================
# AI SIGNAL
# =========================================================

@app.get("/api/signal")
def api_signal():

    result = analyze_market(
        SYMBOL
    )

    ai = result["AI_result"]

    return {
        "symbol": result["symbol"],
        "timeframe": result["timeframe"],
        "price": result["price"],
        "RSI": result["RSI"],
        "EMA20": result["EMA20"],
        "EMA50": result["EMA50"],
        "signal": ai["signal"],
        "buy_probability": ai[
            "buy_probability"
        ],
        "sell_probability": ai[
            "sell_probability"
        ],
        "candle_time": result.get(
            "candle_time"
        ),
    }


# =========================================================
# POSITIONS
# =========================================================

@app.get("/api/positions")
def api_positions():

    positions = mt5.positions_get()

    if positions is None:
        return {
            "total": 0,
            "positions": []
        }

    result = []

    for position in positions:

        result.append({
            "ticket": int(
                position.ticket
            ),
            "symbol":
                position.symbol,
            "type": int(
                position.type
            ),
            "volume": float(
                position.volume
            ),
            "price_open": float(
                position.price_open
            ),
            "sl": float(
                position.sl
            ),
            "tp": float(
                position.tp
            ),
            "profit": float(
                position.profit
            )
        })

    return {
        "total": len(result),
        "positions": result
    }


# =========================================================
# ORIGINAL PREDICT
# =========================================================

@app.post("/predict")
def predict(data: dict):

    return predict_signal(
        data["RSI"],
        data["EMA20"],
        data["EMA50"]
    )


# =========================================================
# ORIGINAL WEBHOOK
# =========================================================

@app.post("/webhook")
def webhook(data: dict):

    result = predict_signal(
        data["RSI"],
        data["EMA20"],
        data["EMA50"]
    )

    return {
        "symbol":
            data.get("symbol"),
        "price":
            data.get("price"),
        "AI_result":
            result
    }


# =========================================================
# MANUAL DEMO ORDER
# =========================================================

@app.post("/api/order")
def api_order(data: dict):

    symbol = data.get(
        "symbol",
        SYMBOL
    )

    side = str(
        data.get("side", "")
    ).upper()

    volume = float(
        data.get(
            "volume",
            MANUAL_VOLUME
        )
    )

    return place_demo_order(
        symbol=symbol,
        side=side,
        volume=volume,
        magic=20260809,
        comment="AI Diana Manual Demo",
    )


# =========================================================
# TRADE HISTORY
# =========================================================

@app.get("/api/history")
def api_history():

    date_to = datetime.now()

    date_from = (
        date_to -
        timedelta(days=30)
    )

    deals = mt5.history_deals_get(
        date_from,
        date_to
    )

    if deals is None:
        return {
            "total": 0,
            "history": []
        }

    result = []

    for deal in deals:

        if deal.type not in [
            mt5.DEAL_TYPE_BUY,
            mt5.DEAL_TYPE_SELL
        ]:
            continue

        result.append({

            "ticket":
                int(deal.ticket),

            "order":
                int(deal.order),

            "time":
                datetime.fromtimestamp(
                    deal.time
                ).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "symbol":
                deal.symbol,

            "type":
                (
                    "BUY"
                    if deal.type
                    == mt5.DEAL_TYPE_BUY
                    else "SELL"
                ),

            "volume":
                float(deal.volume),

            "price":
                float(deal.price),

            "profit":
                float(deal.profit),

            "commission":
                float(deal.commission),

            "swap":
                float(deal.swap),

            "magic":
                int(deal.magic),

            "comment":
                deal.comment
        })

    result.reverse()

    return {
        "total": len(result),
        "history": result
    }


# =========================================================
# SHUTDOWN
# =========================================================

@app.on_event("shutdown")
def shutdown():

    global auto_enabled

    auto_enabled = False

    auto_stop_event.set()

    try:
        mt5.shutdown()

        print(
            "AI Diana API: MT5 disconnected."
        )

    except Exception as e:

        print(
            "MT5 shutdown error:",
            e
        )