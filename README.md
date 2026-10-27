# AI Trading — Flutter + Python + MetaTrader 5

The active product is one Flutter Android app at the repository root and one FastAPI backend on the Windows home server. The backend connects the XAUUSD model to the local MT5 terminal. The worker always starts in STOP state and only permits demo trading.

## Main structure

- `lib/`, `android/`, `pubspec.yaml`: Flutter Android app.
- `backend/api/`: request schemas and HTTP routes.
- `backend/ai/`: confidence and signal interpretation.
- `backend/trading/`: MT5 adapter, order manager, risk checks, and worker engine.
- `backend/mt5_connector.py`: candle data, indicators, model inference.
- `models/`: serialized ML models loaded at runtime.
- `tests/`: API and pure-logic checks.
- `backend/mt5_*backtest*.py`, `backend/train_model.py`, `main.py`: research/legacy scripts; not imported by the active API.

The existing `frontend/`, `dashboard/`, `mobile_app/`, and Docker files are legacy scaffolds; the Flutter root project is the supported client. They are kept in the checkout pending your approval to remove those exact folders/files.

## Run backend (Windows home server)

Use Windows with MetaTrader 5 open and logged into a broker DEMO account. The Python MT5 integration needs the desktop terminal on the same machine; run the active backend directly on Windows, not in a Linux container.

```powershell
cd "C:\Users\hp\Desktop\New folder\AI-Trading"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Do not use `--reload` with the trading worker. Check `http://127.0.0.1:8000/api/status`, `/api/account`, and `/api/signal`. If MT5 was not ready when the backend started, log in to MT5 and restart the backend.

For HP access over local Wi-Fi, allow TCP 8000 in Windows Firewall on the Private profile. Do not forward the API port directly from the router to the internet. Cloudflare Access is not yet integrated in the Flutter API client.

## Run Android app

Enable USB debugging, connect the HP, and from the repository root run:

```powershell
flutter devices
flutter run
```

In the app, open **Koneksi home server** and enter `http://SERVER-IPv4:8000`. Phone and server must be on the same Wi-Fi. Broker profiles in the app are labels; switch brokers by logging into that demo account in MT5 on the home server.

## Demo limits

Current strategy: XAUUSD M5, fixed 0.01 lot, minimum confidence 55%, at most one open XAUUSD position, SL price distance 1.00 and TP price distance 2.00. The auto worker can submit orders after START; use demo and monitor MT5. The model does not guarantee profit.

`.env` and credentials are ignored by Git. Training/backtest scripts require separate research runs and do not execute when imported.
