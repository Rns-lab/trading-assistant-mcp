"""
Configuration settings for the trading assistant
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API Keys
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
    
    # Trading Parameters
    RISK_PER_TRADE = 0.02  # 2% risk per trade
    DEFAULT_STOP_LOSS = 0.05  # 5% stop loss
    DEFAULT_TAKE_PROFIT = 0.15  # 15% take profit
    
    # Technical Analysis
    RSI_PERIOD = 14
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # Timeframes
    DEFAULT_TIMEFRAME = '1h'
    AVAILABLE_TIMEFRAMES = ['5m', '15m', '1h', '4h', '1d']
    