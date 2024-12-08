"""
Risk management module
"""
from typing import Dict, Tuple, Optional, List
import numpy as np

class RiskManager:
    def __init__(self, settings: dict):
        # Configurazione generale
        self.risk_per_trade = settings.get('risk_per_trade', 0.02)  # 2% per trade
        self.max_portfolio_risk = settings.get('max_portfolio_risk', 0.06)  # 6% totale
        self.max_correlation = settings.get('max_correlation', 0.7)  # 70% correlazione massima
        self.stop_loss_atr_multiplier = settings.get('stop_loss_atr_multiplier', 2)
    
    def calculate_position_size(self, 
                              account_balance: float,
                              entry_price: float,
                              stop_loss_price: float) -> Dict:
        """Calcola la dimensione della posizione basata sul rischio"""
        max_risk_amount = account_balance * self.risk_per_trade
        price_risk = abs(entry_price - stop_loss_price)
        position_size = max_risk_amount / price_risk
        position_value = position_size * entry_price
        
        return {
            'position_size': position_size,
            'position_value': position_value,
            'risk_amount': max_risk_amount,
            'risk_percent': self.risk_per_trade * 100
        }

    def get_broker_risk_limits(self, broker_name: str) -> Dict:
        """Ottiene i limiti di rischio specifici del broker"""
        broker_limits = {
            'binance': {
                'max_leverage': 20,
                'min_notional': 10,  # USDT
                'max_orders': 100
            },
            'interactive_brokers': {
                'max_leverage': 4,
                'min_notional': 100,  # USD
                'pattern_day_trading': True
            }
        }
        return broker_limits.get(broker_name, {})

    def calculate_safe_leverage(self, 
                              account_balance: float,
                              position_value: float,
                              volatility: float) -> Dict:
        """Calcola il leverage sicuro basato sulla volatilità"""
        max_safe_leverage = min(3.0, 1.0 / volatility)
        current_leverage = position_value / account_balance
        
        return {
            'max_safe_leverage': max_safe_leverage,
            'current_leverage': current_leverage,
            'is_safe': current_leverage <= max_safe_leverage
        }

    def detect_market_regime(self, 
                            price_data: np.ndarray,
                            volume_data: np.ndarray) -> Dict:
        """Identifica il regime di mercato per adattare il risk management"""
        volatility = np.std(price_data)
        avg_volume = np.mean(volume_data)
        recent_volume = volume_data[-1]
        
        is_high_volatility = volatility > np.mean(volatility) + np.std(volatility)
        is_high_volume = recent_volume > avg_volume * 1.5
        
        if is_high_volatility and is_high_volume:
            regime = 'high_risk'
            risk_multiplier = 0.5
        elif is_high_volatility:
            regime = 'volatile'
            risk_multiplier = 0.7
        elif is_high_volume:
            regime = 'high_volume'
            risk_multiplier = 0.8
        else:
            regime = 'normal'
            risk_multiplier = 1.0
        
        return {
            'regime': regime,
            'risk_multiplier': risk_multiplier,
            'volatility': volatility,
            'volume_ratio': recent_volume / avg_volume
        }

    def generate_portfolio_heat_map(self, positions: Dict) -> Dict:
        """Genera una heat map del rischio del portafoglio"""
        risk_map = {
            'high_risk': [],
            'medium_risk': [],
            'low_risk': []
        }
        
        total_exposure = sum(pos['value'] for pos in positions.values())
        
        for symbol, pos in positions.items():
            risk_ratio = pos['value'] / total_exposure
            if risk_ratio > 0.2:  # Più del 20% del portafoglio
                risk_map['high_risk'].append(symbol)
            elif risk_ratio > 0.1:  # Tra 10% e 20%
                risk_map['medium_risk'].append(symbol)
            else:
                risk_map['low_risk'].append(symbol)
        
        return risk_map

    def adjust_risk_by_sentiment(self, 
                               base_risk: float,
                               sentiment_data: Dict) -> Dict:
        """Adatta il rischio base ai dati del sentiment"""
        weights = {
            'news': 0.3,
            'social': 0.3,
            'technical': 0.4
        }
        
        weighted_score = (
            sentiment_data['news_sentiment']['score'] * weights['news'] +
            sentiment_data['social_sentiment']['score'] * weights['social'] +
            sentiment_data['technical_sentiment']['score'] * weights['technical']
        )
        
        if weighted_score > 0.8:
            risk_multiplier = 1.2
        elif weighted_score < 0.2:
            risk_multiplier = 0.6
        else:
            risk_multiplier = 1.0
        
        adjusted_risk = base_risk * risk_multiplier
        
        return {
            'original_risk': base_risk,
            'adjusted_risk': adjusted_risk,
            'sentiment_score': weighted_score,
            'risk_multiplier': risk_multiplier
        }

    def calculate_risk_score(self,
                            market_data: Dict,
                            sentiment_data: Dict,
                            portfolio_data: Dict) -> Dict:
        """Sistema di scoring per combinare diversi fattori di rischio"""
        scores = {}
        
        # Market Regime Score (0-100)
        market_regime = self.detect_market_regime(
            market_data['prices'],
            market_data['volumes']
        )
        scores['market_regime'] = {
            'high_risk': 20,
            'volatile': 40,
            'high_volume': 60,
            'normal': 80
        }.get(market_regime['regime'], 50)
        
        # Sentiment Score (0-100)
        sentiment_score = self.adjust_risk_by_sentiment(
            1.0,
            sentiment_data
        )
        scores['sentiment'] = sentiment_score['sentiment_score'] * 100
        
        # Portfolio Concentration Score (0-100)
        heat_map = self.generate_portfolio_heat_map(portfolio_data['positions'])
        concentration_risk = len(heat_map['high_risk']) * 20
        scores['concentration'] = max(0, 100 - concentration_risk)
        
        # Correlation Score (0-100)
        correlation_data = self.calculate_correlation_risk(portfolio_data['returns'])
        correlation_risk = len(correlation_data['high_correlation_pairs']) * 15
        scores['correlation'] = max(0, 100 - correlation_risk)
        
        weights = {
            'market_regime': 0.3,
            'sentiment': 0.2,
            'concentration': 0.25,
            'correlation': 0.25
        }
        
        final_score = sum(score * weights[component] 
                         for component, score in scores.items())
        
        return {
            'score': final_score,
            'level': 'high' if final_score < 40 else 'medium' if final_score < 70 else 'low',
            'components': scores
        }

    def backtest_risk_strategy(self,
                              historical_data: Dict,
                              strategy_params: Dict) -> Dict:
        """Backtesting delle strategie di risk management"""
        results = {
            'trades': [],
            'metrics': {},
            'risk_adjustments': []
        }
        
        initial_capital = strategy_params.get('initial_capital', 10000)
        capital = initial_capital
        
        for date, data in historical_data.items():
            # Calcola risk score per il periodo
            risk_score = self.calculate_risk_score(
                data['market'],
                data['sentiment'],
                data['portfolio']
            )
            
            # Simula trade con risk management
            position_size = self.calculate_position_size(
                capital,
                data['price'],
                data['price'] * 0.95
            )
            
            # Adatta position size al risk score
            adjusted_size = position_size['position_size'] * (risk_score['score'] / 100)
            
            # Simula risultato del trade
            pnl = data['next_price'] - data['price']
            trade_result = adjusted_size * pnl
            
            # Aggiorna capitale
            capital += trade_result
            
            results['trades'].append({
                'date': date,
                'risk_score': risk_score,
                'position_size': adjusted_size,
                'pnl': trade_result,
                'capital': capital
            })
            
            results['risk_adjustments'].append({
                'date': date,
                'original_size': position_size['position_size'],
                'adjusted_size': adjusted_size,
                'risk_score': risk_score
            })
        
        results['metrics'] = {
            'final_capital': capital,
            'total_return': (capital - initial_capital) / initial_capital * 100,
            'max_drawdown': self._calculate_max_drawdown(results['trades']),
            'sharpe_ratio': self._calculate_sharpe_ratio(results['trades']),
            'risk_adjusted_return': self._calculate_risk_adjusted_return(results['trades'])
        }
        
        return results

    def _calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """Calcola il maximum drawdown dalla serie di trades"""
        capitals = [t['capital'] for t in trades]
        peak = capitals[0]
        max_dd = 0
        
        for capital in capitals:
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak
            if dd > max_dd:
                max_dd = dd
        
        return max_dd * 100

    def _calculate_sharpe_ratio(self, trades: List[Dict]) -> float:
        """Calcola lo Sharpe Ratio dei trades"""
        returns = [(t['capital'] - prev['capital']) / prev['capital'] 
                  for t, prev in zip(trades[1:], trades[:-1])]
        
        if not returns:
            return 0
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0
            
        return (avg_return / std_return) * np.sqrt(252)

    def _calculate_risk_adjusted_return(self, trades: List[Dict]) -> float:
        """Calcola il rendimento aggiustato per il rischio"""
        total_return = (trades[-1]['capital'] - trades[0]['capital']) / trades[0]['capital']
        max_dd = self._calculate_max_drawdown(trades)
        
        if max_dd == 0:
            return 0
            
        return total_return / (max_dd / 100)

    def calculate_correlation_risk(self, asset_returns: Dict[str, np.ndarray]) -> Dict:
        """Calcola il rischio di correlazione tra asset"""
        correlations = {}
        high_corr_pairs = []
        
        assets = list(asset_returns.keys())
        for i in range(len(assets)):
            for j in range(i+1, len(assets)):
                asset1, asset2 = assets[i], assets[j]
                corr = np.corrcoef(asset_returns[asset1], asset_returns[asset2])[0,1]
                correlations[f"{asset1}-{asset2}"] = corr
                
                if abs(corr) > self.max_correlation:
                    high_corr_pairs.append((asset1, asset2, corr))
        
        return {
            'correlations': correlations,
            'high_correlation_pairs': high_corr_pairs,
            'max_correlation': self.max_correlation
        }
    