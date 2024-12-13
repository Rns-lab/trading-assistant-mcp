"""
Sistema di scoring per i segnali di trading
Integra:
- Previsioni del transformer
- Analisi tecnica
- Risk management
- Sentiment analysis
"""
import numpy as np
from typing import Dict, Optional
from src.models.transformer import TradingTransformer
from src.risk.manager import RiskManager

class SignalScorer:
    def __init__(self, 
                 confidence_threshold: float = 0.7,
                 min_risk_reward: float = 2.0,
                 max_portfolio_risk: float = 0.02):  # 2% max risk per trade
        
        self.transformer = TradingTransformer(input_size=10)  # preset features
        self.risk_manager = RiskManager({
            'risk_per_trade': max_portfolio_risk,
            'max_portfolio_risk': max_portfolio_risk * 3
        })
        self.confidence_threshold = confidence_threshold
        self.min_risk_reward = min_risk_reward

    async def generate_signal(self, 
                            symbol: str,
                            price_data: np.ndarray,
                            volume_data: np.ndarray,
                            additional_features: Dict = None) -> Dict:
        """
        Genera un segnale di trading completo
        """
        # 1. Previsione Transformer
        transformer_prediction = self.transformer.forward(price_data)
        predicted_prices = transformer_prediction['price_predictions']
        confidence = transformer_prediction['confidence_scores']
        volatility = transformer_prediction['volatility_estimates']

        # 2. Analisi Tecnica
        technical_score = self._calculate_technical_score(price_data, volume_data)

        # 3. Risk Assessment
        risk_assessment = self.risk_manager.calculate_risk_score(
            market_data={'prices': price_data, 'volumes': volume_data},
            sentiment_data={'score': technical_score},
            portfolio_data={'positions': {}}  # TODO: Add current positions
        )

        # 4. Calcola segnale finale
        signal = self._combine_signals(
            price=price_data[-1],
            predicted_price=predicted_prices[-1],
            confidence=confidence[-1],
            volatility=volatility[-1],
            technical_score=technical_score,
            risk_score=risk_assessment['score']
        )

        return {
            'symbol': symbol,
            'signal': signal['action'],
            'confidence': signal['confidence'],
            'target_price': signal['target_price'],
            'stop_loss': signal['stop_loss'],
            'risk_reward': signal['risk_reward'],
            'position_size': signal['position_size'],
            'analysis': {
                'transformer_confidence': confidence[-1],
                'technical_score': technical_score,
                'risk_score': risk_assessment['score'],
                'volatility': volatility[-1]
            }
        }

    def _calculate_technical_score(self, 
                                 price_data: np.ndarray, 
                                 volume_data: np.ndarray) -> float:
        """
        Calcola score basato su indicatori tecnici
        """
        # RSI
        rsi = self._calculate_rsi(price_data)
        rsi_score = 1.0 if rsi < 30 else 0.0 if rsi > 70 else 0.5

        # Volume Analysis
        vol_avg = np.mean(volume_data[-20:])
        vol_current = volume_data[-1]
        volume_score = 1.0 if vol_current > vol_avg * 1.5 else 0.5

        # Trend Analysis
        trend_score = self._calculate_trend_score(price_data)

        return (rsi_score * 0.3 + volume_score * 0.3 + trend_score * 0.4)

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calcola il RSI"""
        deltas = np.diff(prices)
        gain = np.where(deltas > 0, deltas, 0)
        loss = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gain[-period:])
        avg_loss = np.mean(loss[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calculate_trend_score(self, prices: np.ndarray) -> float:
        """Analizza il trend"""
        sma_20 = np.mean(prices[-20:])
        sma_50 = np.mean(prices[-50:])
        current_price = prices[-1]
        
        if current_price > sma_20 and sma_20 > sma_50:
            return 1.0  # Strong uptrend
        elif current_price < sma_20 and sma_20 < sma_50:
            return 0.0  # Strong downtrend
        return 0.5  # Sideways

    def _combine_signals(self,
                        price: float,
                        predicted_price: float,
                        confidence: float,
                        volatility: float,
                        technical_score: float,
                        risk_score: float) -> Dict:
        """
        Combina tutti i segnali per una decisione finale
        """
        # Calcola la direzione prevista
        price_change = (predicted_price - price) / price
        
        # Se confidence troppo bassa, non tradare
        if confidence < self.confidence_threshold:
            return {
                'action': 'WAIT',
                'confidence': confidence,
                'target_price': None,
                'stop_loss': None,
                'risk_reward': 0,
                'position_size': 0
            }

        # Calcola stop loss basato su volatilità
        stop_loss = price * (1 - volatility) if price_change > 0 else price * (1 + volatility)
        
        # Calcola target basato su R:R minimo
        risk = abs(price - stop_loss)
        target = price + (risk * self.min_risk_reward) if price_change > 0 else price - (risk * self.min_risk_reward)
        
        # Calcola Risk:Reward
        risk_reward = abs(target - price) / abs(stop_loss - price)
        
        # Combina tutti i fattori per lo score finale
        final_score = (
            confidence * 0.3 +
            technical_score * 0.3 +
            (risk_score / 100) * 0.4  # risk_score è 0-100
        )
        
        # Decidi azione
        if price_change > volatility and final_score > 0.7:
            action = 'BUY'
        elif price_change < -volatility and final_score > 0.7:
            action = 'SELL'
        else:
            action = 'WAIT'
        
        return {
            'action': action,
            'confidence': final_score,
            'target_price': target,
            'stop_loss': stop_loss,
            'risk_reward': risk_reward,
            'position_size': self._calculate_position_size(price, stop_loss, risk_score)
        }

    def _calculate_position_size(self,
                               price: float,
                               stop_loss: float,
                               risk_score: float) -> float:
        """
        Calcola la size della posizione basata su risk management
        """
        risk_amount = 100 * (self.risk_manager.risk_per_trade * (risk_score / 100))
        price_risk = abs(price - stop_loss)
        return risk_amount / price_risk
    