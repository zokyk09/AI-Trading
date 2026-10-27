# Finex demo + XAUUSD runbook

Flow: HP → Cloudflare Access → Cloudflare Tunnel → Dashboard → Python API → MT5 terminal → Finex Demo → XAUUSD.

Set `TRADING_MODE=demo`, broker credentials, and symbol in a protected secret store. Run MT5 on a supported Windows host; the Linux Docker container in `compose.yaml` cannot run the desktop terminal. Keep the API behind Cloudflare Access and set a strong `API_TOKEN`. Validate connectivity, symbol availability, volume limits, and stop-loss behavior on demo before enabling order submission. This starter intentionally blocks START and all order submission until that adapter and safeguards are implemented.
