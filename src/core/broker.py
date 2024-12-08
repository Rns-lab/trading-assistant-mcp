"""
Base broker interface and implementations
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from binance.client import Client

class BaseBroker(ABC):
    """Abstract base class for broker implementations"""
    
    @abstractmethod
    def get_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, side: str, quantity: float):
        """Place a new order"""
        pass
    
    @abstractmethod
    def get_balance(self) -> Dict[str, float]:
        """Get account balance"""
        pass

class BinanceBroker(BaseBroker):
    """Binance broker implementation"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.client = Client(api_key, api_secret)
    
    def get_price(self, symbol: str) -> float:
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    
    def place_order(self, symbol: str, side: str, quantity: float):
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            return order
        except Exception as e:
            print(f"Error placing order: {e}")
            return None
    
    def get_balance(self) -> Dict[str, float]:
        account = self.client.get_account()
        return {
            b['asset']: float(b['free']) 
            for b in account['balances'] 
            if float(b['free']) > 0
        }
    