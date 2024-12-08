"""
Main entry point for the trading assistant
"""
import os
import asyncio
from config.settings import Settings
from core.broker import BinanceBroker
from analysis.sentiment import SentimentAnalysis
from risk.manager import RiskManager

async def get_market_data(symbol: str) -> dict:
    """
    Recupera i dati di mercato per un simbolo
    """
    # Implementazione placeholder - da completare con dati reali
    return {
        'prices': [],
        'volumes': [],
        'indicators': {}
    }

async def get_portfolio_data() -> dict:
    """
    Recupera i dati correnti del portafoglio
    """
    # Implementazione placeholder - da completare con dati reali
    return {
        'positions': {},
        'returns': {},
        'balance': 0.0
    }

async def analyze_trade_risk(symbol: str):
    """
    Analizza il rischio per un potenziale trade
    """
    # Inizializza i componenti
    settings = {'risk_per_trade': 0.02}  # Esempio di settings
    risk_manager = RiskManager(settings)
    sentiment_analyzer = SentimentAnalysis()
    
    # Ottieni dati
    market_data = await get_market_data(symbol)
    sentiment_data = await sentiment_analyzer.analyze_sentiment(symbol)
    portfolio_data = await get_portfolio_data()
    
    # Analizza rischio
    risk_score = risk_manager.calculate_risk_score(
        market_data,
        sentiment_data,
        portfolio_data
    )
    
    # Calcola risk adjustment basato sul sentiment
    adjusted_risk = risk_manager.adjust_risk_by_sentiment(
        0.02,  # rischio base del 2%
        sentiment_data
    )
    
    return {
        'risk_score': risk_score,
        'adjusted_risk': adjusted_risk,
        'market_regime': risk_manager.detect_market_regime(
            market_data['prices'],
            market_data['volumes']
        )
    }

async def main():
    # Inizializza broker
    broker = BinanceBroker(
        api_key=Settings.BINANCE_API_KEY,
        api_secret=Settings.BINANCE_SECRET_KEY
    )
    
    # Test connessione
    try:
        # Esempio di analisi per BTC
        symbol = 'BTCUSDT'
        
        # Ottieni prezzo corrente
        btc_price = broker.get_price(symbol)
        print(f"\nCurrent BTC Price: {btc_price} USDT")
        
        # Analizza rischio
        risk_analysis = await analyze_trade_risk(symbol)
        print("\nRisk Analysis:")
        print(f"Risk Score: {risk_analysis['risk_score']['score']:.2f}")
        print(f"Risk Level: {risk_analysis['risk_score']['level']}")
        print(f"Market Regime: {risk_analysis['market_regime']['regime']}")
        print(f"Adjusted Risk: {risk_analysis['adjusted_risk']['adjusted_risk']:.2%}")
        
        # Mostra saldi account
        balances = broker.get_balance()
        print("\nAccount Balances:")
        for asset, amount in balances.items():
            print(f"{asset}: {amount}")
            
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    asyncio.run(main())
    