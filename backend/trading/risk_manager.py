"""Pure risk checks shared by order execution and tests."""


def validate_order(*, mode: str, risk_percent: float, volume: float) -> tuple[bool, str]:
    if mode.lower() != "demo":
        return False, "Only demo mode is permitted"
    if not 0 < risk_percent <= 1:
        return False, "Risk must be greater than 0 and at most 1 percent"
    if volume != 0.01:
        return False, "Demo volume is fixed at 0.01 lot"
    return True, "validated"


def validate_demo_account(mt5, *, symbol: str) -> tuple[bool, str]:
    account = mt5.account_info()
    if account is None:
        return False, "MT5 account is not connected"
    if account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        return False, "Order blocked: account is not DEMO"
    terminal = mt5.terminal_info()
    if terminal is None:
        return False, "MT5 terminal is unavailable"
    if not terminal.trade_allowed:
        return False, "Trading is disabled in the MT5 terminal"
    if mt5.symbol_info(symbol) is None:
        return False, f"Symbol {symbol} is unavailable"
    return True, "validated"
