"""Shared singletons for API routes and the background worker."""
import MetaTrader5 as mt5

from backend.mt5_connector import analyze_market
from backend.trading.broker_mt5 import broker
from backend.trading.order_manager import OrderManager
from backend.trading.trading_engine import TradingEngine

order_manager = OrderManager(mt5)
engine = TradingEngine(mt5, analyze_market, order_manager)
