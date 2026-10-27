# Backtest reports for the mobile dashboard

The backend discovers CSV reports whose names contain `backtest` in this
directory or directly in `backend/`. The mobile dashboard lists each report
in **Analisa & backtest**. Selecting a report only changes the displayed
report; it does not change the live strategy or order settings.

Use these CSV columns when exporting a report:

- `time`
- `result` (`WIN` or `LOSS`)
- `pnl` (the report's own P/L unit)
- `entry`, `sl`, `tp` (optional, used to summarize median stop, target, and R:R)

An optional JSON file with the same base name can provide report metadata. For
example, `xauusd_v2_backtest.csv` can have `xauusd_v2_backtest.json` alongside
it:

```json
{
  "name": "XAUUSD M5 · Model v2",
  "symbol": "XAUUSD",
  "timeframe": "M5",
  "prediction_accuracy_percent": 85.0,
  "confidence_threshold": 60,
  "period_start": "2026-01-01",
  "period_end": "2026-06-30"
}
```

Prediction accuracy is only shown when the report supplies it. The dashboard
calculates trade win rate separately from the CSV outcomes. Net P/L and maximum
drawdown retain the unit used in the CSV; the backend does not assume they are
USD. Backtest figures are simulated results and are not used as live performance
claims.
