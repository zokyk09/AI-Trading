import React, { useEffect, useState } from "react";
import './App.css'

const API = "http://127.0.0.1:8000";

// ==========================================
// TYPES
// ==========================================

type Account = {
  connected: boolean;
  login?: number;
  balance?: number;
  equity?: number;
  profit?: number;
  currency?: string;
};

type Signal = {
  symbol: string;
  timeframe: string;
  price: number;
  RSI: number;
  EMA20: number;
  EMA50: number;
  signal: "BUY" | "SELL";
  buy_probability: number;
  sell_probability: number;
};

type Position = {
  ticket: number;
  symbol: string;
  type: number;
  volume: number;
  price_open: number;
  sl: number;
  tp: number;
  profit: number;
};

type TradeHistory = {
  ticket: number;
  order: number;
  time: string;
  symbol: string;
  type: "BUY" | "SELL";
  volume: number;
  price: number;
  profit: number;
  commission: number;
  swap: number;
  magic: number;
  comment: string;
};

// ==========================================
// HELPERS
// ==========================================

function money(value = 0) {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// ==========================================
// APP
// ==========================================

function App() {
  // ========================================
  // STATE
  // ========================================

  const [account, setAccount] = useState<Account>({
    connected: false,
  });

  const [signal, setSignal] =
    useState<Signal | null>(null);

  const [positions, setPositions] =
    useState<Position[]>([]);

  const [history, setHistory] =
    useState<TradeHistory[]>([]);

  const [mt5Connected, setMt5Connected] =
    useState(false);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [orderLoading, setOrderLoading] =
    useState(false);

  const [orderMessage, setOrderMessage] =
    useState("");

  // ========================================
  // AUTO TRADING
  // ========================================

  const [autoEnabled, setAutoEnabled] =
    useState(false);

  const [autoLoading, setAutoLoading] =
    useState(false);

  const [autoMessage, setAutoMessage] =
    useState("");

  // ========================================
  // LOAD DASHBOARD
  // ========================================

  async function loadDashboard() {
    try {
      const [
        statusResponse,
        accountResponse,
        signalResponse,
        positionsResponse,
        historyResponse,
        autoResponse,
      ] = await Promise.all([
        fetch(`${API}/api/status`),
        fetch(`${API}/api/account`),
        fetch(`${API}/api/signal`),
        fetch(`${API}/api/positions`),
        fetch(`${API}/api/history`),
        fetch(`${API}/api/auto`),
      ]);

      if (!statusResponse.ok) {
        throw new Error("API status gagal");
      }

      if (!accountResponse.ok) {
        throw new Error("API account gagal");
      }

      if (!signalResponse.ok) {
        throw new Error("API signal gagal");
      }

      if (!positionsResponse.ok) {
        throw new Error("API positions gagal");
      }

      if (!historyResponse.ok) {
        throw new Error("API history gagal");
      }

      if (!autoResponse.ok) {
        throw new Error("API auto gagal");
      }

      const status =
        await statusResponse.json();

      const accountData =
        await accountResponse.json();

      const signalData =
        await signalResponse.json();

      const positionsData =
        await positionsResponse.json();

      const historyData =
        await historyResponse.json();

      const autoData =
        await autoResponse.json();

      setMt5Connected(
        Boolean(status.connected)
      );

      setAutoEnabled(
        Boolean(autoData.enabled)
      );

      setAccount(accountData);

      setSignal(signalData);

      setPositions(
        positionsData.positions || []
      );

      setHistory(
        historyData.history || []
      );

      setError("");
      setLoading(false);

    } catch (err) {
      console.error(err);

      setError(
        "Tidak dapat mengambil data dari API."
      );

      setMt5Connected(false);
      setLoading(false);
    }
  }

  // ========================================
  // AUTO REFRESH 5 DETIK
  // ========================================

  useEffect(() => {
    loadDashboard();

    const timer = setInterval(
      loadDashboard,
      5000
    );

    return () => {
      clearInterval(timer);
    };
  }, []);

  // ========================================
  // MANUAL ORDER
  // ========================================

  async function sendOrder(
    side: "BUY" | "SELL"
  ) {
    if (!mt5Connected) {
      setOrderMessage(
        "MT5 belum terhubung."
      );

      return;
    }

    const confirmed =
      window.confirm(
        `${side} XAUUSD 0.01 lot?\n\n` +
        `SL: $1.00\n` +
        `TP: $2.00\n\n` +
        `Akun DEMO`
      );

    if (!confirmed) {
      return;
    }

    try {
      setOrderLoading(true);
      setOrderMessage("");

      const response = await fetch(
        `${API}/api/order`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            symbol: "XAUUSD",
            side,
            volume: 0.01,
          }),
        }
      );

      const result =
        await response.json();

      if (
        !response.ok ||
        !result.success
      ) {
        throw new Error(
          result.message ||
            "Order gagal"
        );
      }

      setOrderMessage(
        `✅ ${side} berhasil dikirim. ` +
        `Ticket: ${result.order || "-"}`
      );

      await loadDashboard();

    } catch (err) {
      console.error(err);

      setOrderMessage(
        err instanceof Error
          ? `❌ ${err.message}`
          : "❌ Order gagal"
      );

    } finally {
      setOrderLoading(false);
    }
  }

  // ========================================
  // AUTO TRADING
  // ========================================

  async function toggleAuto() {

    if (!mt5Connected) {
      setAutoMessage(
        "MT5 belum terhubung."
      );
      return;
    }

    const nextState = !autoEnabled;

    if (nextState) {

      const confirmed =
        window.confirm(
          "AKTIFKAN AUTO TRADING XAUUSD?\\n\\n" +
          "XAUUSD M5\\n" +
          "Lot: 0.01\\n" +
          "Confidence minimum: 55%\\n" +
          "SL: $1.00\\n" +
          "TP: $2.00\\n\\n" +
          "Akun DEMO."
        );

      if (!confirmed) {
        return;
      }
    }

    try {

      setAutoLoading(true);
      setAutoMessage("");

      const response = await fetch(
        `${API}/api/auto`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            enabled: nextState,
          }),
        }
      );

      const result =
        await response.json();

      if (
        !response.ok ||
        result.success === false
      ) {
        throw new Error(
          result.message ||
            "Gagal mengubah AUTO."
        );
      }

      setAutoEnabled(
        Boolean(result.enabled)
      );

      setAutoMessage(
        result.message ||
          (
            result.enabled
              ? "AUTO TRADING aktif."
              : "AUTO TRADING dimatikan."
          )
      );

      await loadDashboard();

    } catch (err) {

      console.error(err);

      setAutoMessage(
        err instanceof Error
          ? `❌ ${err.message}`
          : "❌ Gagal mengubah AUTO."
      );

    } finally {

      setAutoLoading(false);

    }
  }

  // ========================================
  // SIGNAL
  // ========================================

  const isBuy =
    signal?.signal === "BUY";

  // ========================================
  // RENDER
  // ========================================

  return (
    <div className="app">

      {/* ==================================
          SIDEBAR
      ================================== */}

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-icon">
            D
          </div>

          <div>
            <h2>AI DIANA</h2>

            <span>
              Trading System
            </span>
          </div>

        </div>

        <nav className="menu">

          <div className="menu-item active">
            <span>⌂</span>
            Dashboard
          </div>

          <div className="menu-item">
            <span>◈</span>
            Trading
          </div>

          <div className="menu-item">
            <span>◉</span>
            AI Signal
          </div>

          <div className="menu-item">
            <span>▣</span>
            History
          </div>

          <div className="menu-item">
            <span>⚙</span>
            Settings
          </div>

        </nav>

        <div className="sidebar-bottom">

          <div className="system-status">

            <span
              className={
                mt5Connected
                  ? "status-dot"
                  : "status-dot offline"
              }
            />

            <div>

              <strong>
                {mt5Connected
                  ? "MT5 Connected"
                  : "MT5 Offline"}
              </strong>

              <small>
                {account.login
                  ? `Account ${account.login}`
                  : "Checking connection"}
              </small>

            </div>

          </div>

        </div>

      </aside>

      {/* ==================================
          MAIN
      ================================== */}

      <main className="main">

        {/* TOPBAR */}

        <header className="topbar">

          <div>

            <h1>
              Dashboard
            </h1>

            <p>
              AI Diana market monitoring
            </p>

          </div>

          <div className="top-status">

            <span
              className={
                mt5Connected
                  ? "online-dot"
                  : "online-dot offline"
              }
            />

            {mt5Connected
              ? "Market Monitor Active"
              : "MT5 Offline"}

          </div>

        </header>

        {/* ERROR */}

        {error && (
          <div className="error-box">
            ⚠ {error}
          </div>
        )}

        {/* ==================================
            ACCOUNT CARDS
        ================================== */}

        <section className="cards">

          <div className="card">

            <div className="card-label">
              Balance
            </div>

            <div className="card-value">

              {loading
                ? "Loading..."
                : `$${money(
                    account.balance
                  )}`}

            </div>

            <div className="card-sub positive">
              Demo Account
            </div>

          </div>

          <div className="card">

            <div className="card-label">
              Equity
            </div>

            <div className="card-value">

              {loading
                ? "Loading..."
                : `$${money(
                    account.equity
                  )}`}

            </div>

            <div className="card-sub">
              Floating P/L: $
              {money(account.profit)}
            </div>

          </div>

          <div className="card">

            <div className="card-label">
              Current P/L
            </div>

            <div
              className={
                `card-value ${
                  (account.profit || 0) >= 0
                    ? "positive"
                    : "negative"
                }`
              }
            >

              {account.profit !==
              undefined
                ? `$${money(
                    account.profit
                  )}`
                : "$0.00"}

            </div>

            <div className="card-sub">
              Live MT5
            </div>

          </div>

          <div className="card">

            <div className="card-label">
              Open Positions
            </div>

            <div className="card-value">
              {positions.length}
            </div>

            <div className="card-sub">
              Active MT5 positions
            </div>

          </div>

        </section>

        {/* ==================================
            AI + MARKET
        ================================== */}

        <section className="dashboard-grid">

          {/* AI SIGNAL */}

          <div className="panel">

            <div className="panel-header">

              <div>

                <h2>
                  AI Diana Signal
                </h2>

                <span>
                  {signal
                    ? `${signal.symbol} · ${signal.timeframe}`
                    : "Waiting for data"}
                </span>

              </div>

              <span className="live-badge">
                LIVE
              </span>

            </div>

            {signal ? (
              <>

                <div className="signal-main">

                  <div
                    className={
                      `signal-circle ${
                        isBuy
                          ? "signal-buy"
                          : "signal-sell"
                      }`
                    }
                  >

                    <span>
                      {signal.signal}
                    </span>

                    <strong>
                      {isBuy
                        ? signal.buy_probability
                        : signal.sell_probability}
                      %
                    </strong>

                  </div>

                  <div className="signal-info">

                    <div className="signal-row">

                      <span>
                        Signal
                      </span>

                      <strong
                        className={
                          isBuy
                            ? "buy-text"
                            : "sell-text"
                        }
                      >
                        {signal.signal}
                      </strong>

                    </div>

                    <div className="signal-row">

                      <span>
                        Confidence
                      </span>

                      <strong>
                        {isBuy
                          ? signal.buy_probability
                          : signal.sell_probability}
                        %
                      </strong>

                    </div>

                    <div className="signal-row">

                      <span>
                        Price
                      </span>

                      <strong>
                        {signal.price}
                      </strong>

                    </div>

                  </div>

                </div>

                {/* BUY PROBABILITY */}

                <div className="probability">

                  <div className="prob-title">

                    <span>
                      BUY Probability
                    </span>

                    <strong>
                      {signal.buy_probability}%
                    </strong>

                  </div>

                  <div className="progress">

                    <div
                      className="progress-buy"
                      style={{
                        width:
                          `${signal.buy_probability}%`,
                      }}
                    />

                  </div>

                  {/* SELL */}

                  <div className="prob-title">

                    <span>
                      SELL Probability
                    </span>

                    <strong>
                      {signal.sell_probability}%
                    </strong>

                  </div>

                  <div className="progress">

                    <div
                      className="progress-sell"
                      style={{
                        width:
                          `${signal.sell_probability}%`,
                      }}
                    />

                  </div>

                </div>

              </>
            ) : (

              <div className="waiting">
                Menunggu data AI Diana...
              </div>

            )}

          </div>

          {/* MARKET DATA */}

          <div className="panel">

            <div className="panel-header">

              <div>

                <h2>
                  Market Data
                </h2>

                <span>
                  Live MT5 indicators
                </span>

              </div>

            </div>

            <div className="indicator-grid">

              <div className="indicator">

                <span>
                  RSI 14
                </span>

                <strong>
                  {signal
                    ? signal.RSI
                    : "—"}
                </strong>

                <small>
                  Live
                </small>

              </div>

              <div className="indicator">

                <span>
                  EMA 20
                </span>

                <strong>
                  {signal
                    ? signal.EMA20
                    : "—"}
                </strong>

                <small>
                  Live
                </small>

              </div>

              <div className="indicator">

                <span>
                  EMA 50
                </span>

                <strong>
                  {signal
                    ? signal.EMA50
                    : "—"}
                </strong>

                <small>
                  Live
                </small>

              </div>

              <div className="indicator">

                <span>
                  Price
                </span>

                <strong>
                  {signal
                    ? signal.price
                    : "—"}
                </strong>

                <small>
                  XAUUSD
                </small>

              </div>

            </div>

            <div className="market-status">

              <span
                className={
                  mt5Connected
                    ? "status-dot"
                    : "status-dot offline"
                }
              />

              {mt5Connected
                ? "Live data connected to MT5"
                : "Waiting for MT5"}

            </div>

          </div>

        </section>

        {/* ==================================
            AUTO TRADING
        ================================== */}

        <section className="dashboard-grid">

          <div className="panel">

            <div className="panel-header">

              <div>

                <h2>
                  AI Diana Auto Trading
                </h2>

                <span>
                  XAUUSD · M5 · Demo Only
                </span>

              </div>

              <span
                className={
                  autoEnabled
                    ? "live-badge auto-on"
                    : "live-badge"
                }
              >
                {autoEnabled
                  ? "AUTO ON"
                  : "AUTO OFF"}
              </span>

            </div>

            <div className="manual-info">

              <div>
                <span>Symbol</span>
                <strong>XAUUSD</strong>
              </div>

              <div>
                <span>Volume</span>
                <strong>0.01 Lot</strong>
              </div>

              <div>
                <span>Confidence</span>
                <strong>≥ 55%</strong>
              </div>

              <div>
                <span>SL / TP</span>
                <strong>$1 / $2</strong>
              </div>

            </div>

            <button
              className={
                autoEnabled
                  ? "order-sell"
                  : "order-buy"
              }
              disabled={
                !mt5Connected ||
                autoLoading
              }
              onClick={toggleAuto}
            >
              {autoLoading
                ? "PROCESSING..."
                : autoEnabled
                  ? "MATIKAN AUTO TRADING"
                  : "AKTIFKAN AUTO TRADING"}
            </button>

            {autoMessage && (
              <div className="order-message">
                {autoMessage}
              </div>
            )}

            <div className="manual-warning">
              ⚠ AUTO hanya untuk akun DEMO.
              Maksimal 1 posisi XAUUSD.
            </div>

          </div>

        </section>

        {/* ==================================
            MANUAL TRADING
        ================================== */}

        <section className="dashboard-grid">

          <div className="panel">

            <div className="panel-header">

              <div>

                <h2>
                  Manual Trading
                </h2>

                <span>
                  Demo account only
                </span>

              </div>

              <span className="live-badge">
                DEMO
              </span>

            </div>

            <div className="manual-info">

              <div>
                <span>Symbol</span>
                <strong>XAUUSD</strong>
              </div>

              <div>
                <span>Volume</span>
                <strong>0.01 Lot</strong>
              </div>

              <div>
                <span>SL</span>
                <strong>$1.00</strong>
              </div>

              <div>
                <span>TP</span>
                <strong>$2.00</strong>
              </div>

            </div>

            <div className="order-buttons">

              <button
                className="order-buy"
                disabled={
                  !mt5Connected ||
                  orderLoading
                }
                onClick={() =>
                  sendOrder("BUY")
                }
              >

                {orderLoading
                  ? "PROCESSING..."
                  : "BUY 0.01"}

              </button>

              <button
                className="order-sell"
                disabled={
                  !mt5Connected ||
                  orderLoading
                }
                onClick={() =>
                  sendOrder("SELL")
                }
              >

                {orderLoading
                  ? "PROCESSING..."
                  : "SELL 0.01"}

              </button>

            </div>

            {orderMessage && (
              <div className="order-message">
                {orderMessage}
              </div>
            )}

            <div className="manual-warning">
              ⚠ Order akan dikirim ke akun DEMO
              MT5 setelah konfirmasi.
            </div>

          </div>

        </section>

        {/* ==================================
            CONFIG + POSITIONS
        ================================== */}

        <section className="dashboard-grid">

          {/* CONFIG */}

          <div className="panel">

            <div className="panel-header">

              <div>

                <h2>
                  Trading Configuration
                </h2>

                <span>
                  AI Diana V2
                </span>

              </div>

            </div>

            <div className="config-grid">

              <div>
                <span>Symbol</span>
                <strong>XAUUSD</strong>
              </div>

              <div>
                <span>Timeframe</span>
                <strong>M5</strong>
              </div>

              <div>
                <span>Mode</span>
                <strong>DEMO</strong>
              </div>

              <div>
                <span>AI</span>
                <strong>RandomForest</strong>
              </div>

              <div>
                <span>Risk</span>
                <strong>1.0%</strong>
              </div>

              <div>
                <span>Status</span>
                <strong>
                  {mt5Connected
                    ? "CONNECTED"
                    : "OFFLINE"}
                </strong>
              </div>

            </div>

          </div>

          {/* POSITIONS */}

          <div className="panel">

            <div className="panel-header">

              <div>

                <h2>
                  Open Positions
                </h2>

                <span>
                  Real-time MT5 positions
                </span>

              </div>

            </div>

            {positions.length === 0 ? (

              <div className="waiting">
                Tidak ada posisi terbuka.
              </div>

            ) : (

              <div className="positions">

                {positions.map(
                  (position) => (

                    <div
                      className="position"
                      key={position.ticket}
                    >

                      <div>

                        <strong>
                          {position.symbol}
                        </strong>

                        <small>
                          Ticket #{position.ticket}
                        </small>

                      </div>

                      <div>

                        <strong>
                          {position.volume}
                        </strong>

                        <small>
                          Lot
                        </small>

                      </div>

                      <div>

                        <strong
                          className={
                            position.profit >= 0
                              ? "positive"
                              : "negative"
                          }
                        >
                          {position.profit >= 0
                            ? "+"
                            : ""}
                          $
                          {money(
                            position.profit
                          )}
                        </strong>

                        <small>
                          P/L
                        </small>

                      </div>

                    </div>

                  )
                )}

              </div>

            )}

          </div>

        </section>

        {/* ==================================
            TRADE HISTORY
        ================================== */}

        <section className="panel history-panel">

          <div className="panel-header">

            <div>

              <h2>
                Trade History
              </h2>

              <span>
                Riwayat transaksi MT5
              </span>

            </div>

            <span className="live-badge">
              {history.length} DEAL
            </span>

          </div>

          {history.length === 0 ? (

            <div className="waiting">
              Belum ada transaksi.
            </div>

          ) : (

            <div className="history-table-wrapper">

              <table className="history-table">

                <thead>

                  <tr>
                    <th>Waktu</th>
                    <th>Symbol</th>
                    <th>Type</th>
                    <th>Lot</th>
                    <th>Price</th>
                    <th>Profit</th>
                  </tr>

                </thead>

                <tbody>

                  {history.map(
                    (trade) => (

                      <tr
                        key={trade.ticket}
                      >

                        <td>
                          {trade.time}
                        </td>

                        <td>
                          {trade.symbol}
                        </td>

                        <td>

                          <span
                            className={
                              trade.type === "BUY"
                                ? "history-buy"
                                : "history-sell"
                            }
                          >
                            {trade.type}
                          </span>

                        </td>

                        <td>
                          {trade.volume}
                        </td>

                        <td>
                          {trade.price}
                        </td>

                        <td
                          className={
                            trade.profit >= 0
                              ? "positive"
                              : "negative"
                          }
                        >
                          {trade.profit >= 0
                            ? "+"
                            : ""}
                          $
                          {money(
                            trade.profit
                          )}
                        </td>

                      </tr>

                    )
                  )}

                </tbody>

              </table>

            </div>

          )}

        </section>

        {/* ==================================
            FOOTER
        ================================== */}

        <footer>

          <span>
            AI Diana Trading System
          </span>

          <span>
            MT5 Demo · Live API · V2
          </span>

        </footer>

      </main>

    </div>
  );
}

export default App;