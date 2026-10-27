"""HTTP endpoints consumed by the Flutter client."""
from datetime import datetime, timedelta
import csv
import json
from pathlib import Path
from statistics import median
from fastapi import APIRouter
import MetaTrader5 as mt5

from backend.ai.signal_engine import generate_signal
from backend.api.schemas import AutoControl, OrderRequest, PredictionRequest
from backend.config import settings
from backend.mt5_connector import analyze_market
from backend.predict import predict_signal
from backend.trading.runtime import engine, order_manager

router = APIRouter()
BACKTEST_DIRECTORY = Path(__file__).resolve().parents[1]


def _float_value(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _backtest_report(path: Path) -> dict:
    metadata_path = path.with_suffix(".json")
    metadata = {}
    if metadata_path.is_file():
        try:
            loaded_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata = loaded_metadata if isinstance(loaded_metadata, dict) else {}
        except (OSError, json.JSONDecodeError):
            metadata = {}

    with path.open("r", encoding="utf-8-sig", newline="") as report_file:
        rows = list(csv.DictReader(report_file))

    trades = []
    for row in rows:
        pnl = _float_value(row.get("pnl"))
        result = str(row.get("result", "")).strip().upper()
        if pnl is None and result not in {"WIN", "LOSS"}:
            continue
        trades.append((row, pnl if pnl is not None else (1.0 if result == "WIN" else -1.0)))

    wins = [pnl for _, pnl in trades if pnl > 0]
    losses = [pnl for _, pnl in trades if pnl < 0]
    net_pnl = sum(pnl for _, pnl in trades)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    equity = peak = max_drawdown = 0.0
    for _, pnl in trades:
        equity += pnl
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)

    stop_distances = []
    target_distances = []
    times = []
    for row, _ in trades:
        entry = _float_value(row.get("entry"))
        stop = _float_value(row.get("sl"))
        target = _float_value(row.get("tp"))
        if entry is not None and stop is not None and target is not None:
            stop_distance = abs(entry - stop)
            target_distance = abs(target - entry)
            if stop_distance > 0 and target_distance > 0:
                stop_distances.append(stop_distance)
                target_distances.append(target_distance)
        time_value = row.get("time")
        if time_value:
            times.append(time_value)

    report_id = (
        path.relative_to(BACKTEST_DIRECTORY)
        .as_posix()
        .lower()
        .replace("_", "-")
        .removesuffix(".csv")
        .replace("/", "-")
    )
    ratio = median(target_distances) / median(stop_distances) if stop_distances else None
    ratios = [tp / sl for sl, tp in zip(stop_distances, target_distances) if sl > 0]
    return {
        "id": report_id,
        "name": metadata.get("name") or path.stem.replace("_", " ").title(),
        "symbol": metadata.get("symbol") or "XAUUSD",
        "timeframe": metadata.get("timeframe"),
        "source": path.name,
        "period_start": metadata.get("period_start") or (min(times) if times else None),
        "period_end": metadata.get("period_end") or (max(times) if times else None),
        "trade_count": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_percent": round(len(wins) * 100 / len(trades), 2) if trades else None,
        "expectancy_per_trade": round(net_pnl / len(trades), 4) if trades else None,
        "prediction_accuracy_percent": _float_value(metadata.get("prediction_accuracy_percent")),
        "net_pnl": round(net_pnl, 4) if trades else None,
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else None,
        "max_drawdown": round(max_drawdown, 4) if trades else None,
        "median_sl_distance": round(median(stop_distances), 4) if stop_distances else None,
        "median_tp_distance": round(median(target_distances), 4) if target_distances else None,
        "reward_risk_ratio": round(median(ratios), 2) if ratios else (round(ratio, 2) if ratio is not None else None),
        "confidence_threshold": _float_value(metadata.get("confidence_threshold")),
    }


def _backtest_files() -> list[Path]:
    files = list(BACKTEST_DIRECTORY.glob("*backtest*.csv"))
    extra_directory = BACKTEST_DIRECTORY / "backtests"
    if extra_directory.is_dir():
        files.extend(extra_directory.glob("*.csv"))
    return sorted({path.resolve() for path in files if path.is_file()}, key=lambda item: item.name.lower())


def _active_plan() -> dict:
    return {
        "name": "Strategi aktif",
        "symbol": settings.symbol,
        "timeframe": settings.timeframe_name,
        "mode": "DEMO_ONLY",
        "position_sizing": "Fixed lot",
        "volume": settings.order_volume,
        "risk_per_trade_percent": None,
        "daily_loss_limit_percent": None,
        "max_open_positions": settings.max_open_positions,
        "sl_distance": settings.stop_loss_distance,
        "tp_distance": settings.take_profit_distance,
        "reward_risk_ratio": round(settings.take_profit_distance / settings.stop_loss_distance, 2),
        "confidence_threshold": settings.min_confidence,
        "risk_note": "Lot masih tetap; risiko % saldo dan batas rugi harian belum dikonfigurasi.",
    }


@router.get("/")
@router.get("/api/health")
def health():
    return {"status": "Online", "message": "AI Trading API ready"}


@router.get("/api/backtests")
def backtests():
    reports = []
    for path in _backtest_files():
        try:
            reports.append(_backtest_report(path))
        except (OSError, csv.Error, UnicodeError):
            continue
    return {"reports": reports, "active_plan": _active_plan()}


@router.get("/api/status")
def status():
    terminal = mt5.terminal_info()
    connected = terminal is not None
    return {
        "connected": connected,
        "message": "MT5 Connected" if connected else "MT5 not connected",
        "trade_allowed": bool(terminal.trade_allowed) if connected else False,
        "auto_enabled": engine.enabled,
        "auto_confidence": settings.min_confidence,
        "auto_symbol": settings.symbol,
        "auto_volume": settings.order_volume,
    }


@router.get("/api/auto")
def auto_status():
    return {
        "enabled": engine.enabled,
        "symbol": settings.symbol,
        "timeframe": settings.timeframe_name,
        "confidence": settings.min_confidence,
        "volume": settings.order_volume,
        "sl": settings.stop_loss_distance,
        "tp": settings.take_profit_distance,
        "mode": "DEMO_ONLY",
    }


@router.post("/api/auto")
def auto_control(command: AutoControl):
    return engine.start() if command.enabled else engine.stop()


@router.get("/api/account")
def account_status():
    account = mt5.account_info()
    if account is None:
        return {"connected": False}
    return {
        "connected": True,
        "login": int(account.login),
        "balance": float(account.balance),
        "equity": float(account.equity),
        "profit": float(account.profit),
        "currency": account.currency,
        "server": getattr(account, "server", None),
        "company": getattr(account, "company", None),
        "trade_mode": int(account.trade_mode),
    }


@router.get("/api/market")
def market():
    return analyze_market(settings.symbol)


@router.get("/api/signal")
def signal():
    result = analyze_market(settings.symbol)
    ai = result["AI_result"]
    display_signal = generate_signal({
        "buy_probability": ai["buy_probability"],
        "sell_probability": ai["sell_probability"],
        "min_confidence": settings.min_confidence,
    })["signal"]
    return {
        "symbol": result["symbol"],
        "timeframe": result["timeframe"],
        "price": result["price"],
        "RSI": result["RSI"],
        "EMA20": result["EMA20"],
        "EMA50": result["EMA50"],
        "signal": display_signal,
        "buy_probability": ai["buy_probability"],
        "sell_probability": ai["sell_probability"],
        "candle_time": result["candle_time"],
    }


@router.get("/api/positions")
def positions():
    items = mt5.positions_get() or []
    return {
        "total": len(items),
        "positions": [
            {
                "ticket": int(item.ticket),
                "symbol": item.symbol,
                "type": int(item.type),
                "volume": float(item.volume),
                "price_open": float(item.price_open),
                "sl": float(item.sl),
                "tp": float(item.tp),
                "profit": float(item.profit),
            }
            for item in items
        ],
    }


@router.post("/predict")
def predict(data: PredictionRequest):
    return predict_signal(data.RSI, data.EMA20, data.EMA50)


@router.post("/webhook")
def webhook(data: PredictionRequest):
    result = predict_signal(data.RSI, data.EMA20, data.EMA50)
    return {"symbol": data.symbol, "price": data.price, "AI_result": result}


@router.post("/api/order")
def manual_order(data: OrderRequest):
    return order_manager.submit(
        symbol=data.symbol,
        side=data.side,
        volume=data.volume,
        magic=settings.manual_magic,
        comment="AI Trading manual demo",
    )


@router.get("/api/history")
def trade_history():
    end = datetime.now()
    start = end - timedelta(days=30)
    deals = mt5.history_deals_get(start, end) or []
    relevant = [d for d in deals if d.type in {mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL}]
    result = [
        {
            "ticket": int(d.ticket),
            "order": int(d.order),
            "time": datetime.fromtimestamp(d.time).strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": d.symbol,
            "type": "BUY" if d.type == mt5.DEAL_TYPE_BUY else "SELL",
            "volume": float(d.volume),
            "price": float(d.price),
            "profit": float(d.profit),
            "commission": float(d.commission),
            "swap": float(d.swap),
            "magic": int(d.magic),
            "comment": d.comment,
        }
        for d in relevant
    ]
    result.reverse()
    return {"total": len(result), "history": result}




