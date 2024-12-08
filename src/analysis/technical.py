"""
Technical analysis module
"""
import pandas as pd
import numpy as np
from ta import momentum, trend, volatility

class TechnicalAnalysis:
    def __init__(self):
        self.indicators = {}
    
    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Perform technical analysis on price data
        """
        results = {}
        
        # Add RSI
        results['rsi'] = momentum.rsi(df['close'])
        
        # Add MACD
        macd = trend.macd_diff(df['close'])
        results['macd'] = macd
        
        # Add Bollinger Bands
        bb = volatility.BollingerBands(df['close'])
        results['bb_upper'] = bb.bollinger_hband()
        results['bb_lower'] = bb.bollinger_lband()
        
        # Add moving averages
        results['sma_20'] = df['close'].rolling(window=20).mean()
        results['sma_50'] = df['close'].rolling(window=50).mean()
        
        return results
    
    def check_signals(self, data: dict) -> list:
        """
        Check for trading signals based on technical indicators
        """
        signals = []
        
        # RSI signals
        last_rsi = data['rsi'].iloc[-1]
        if last_rsi < 30:
            signals.append(('BUY', 'RSI oversold', last_rsi))
        elif last_rsi > 70:
            signals.append(('SELL', 'RSI overbought', last_rsi))
        
        # MACD signals
        if data['macd'].iloc[-1] > 0 and data['macd'].iloc[-2] <= 0:
            signals.append(('BUY', 'MACD crossover', data['macd'].iloc[-1]))
        elif data['macd'].iloc[-1] < 0 and data['macd'].iloc[-2] >= 0:
            signals.append(('SELL', 'MACD crossover', data['macd'].iloc[-1]))
        
        # Bollinger Bands signals
        last_close = data['close'].iloc[-1]
        if last_close < data['bb_lower'].iloc[-1]:
            signals.append(('BUY', 'Price below lower BB', last_close))
        elif last_close > data['bb_upper'].iloc[-1]:
            signals.append(('SELL', 'Price above upper BB', last_close))
        
        return signals
    