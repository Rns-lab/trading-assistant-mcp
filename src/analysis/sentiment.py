"""
Sentiment analysis module
"""
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
import praw  # Per Reddit
from tradingview_ta import TA_Handler  # Per TradingView

class SentimentAnalysis:
    def __init__(self):
        self.dino_digest_url = "https://www.dinodigest.news/"
        self.brave_search = None
        
        # Inizializzazione Reddit
        self.reddit = praw.Reddit(
            client_id="YOUR_CLIENT_ID",
            client_secret="YOUR_CLIENT_SECRET",
            user_agent="your_user_agent"
        )
        
        # Inizializzazione TradingView
        self.tv = TA_Handler()
    
    async def analyze_sentiment(self, symbol: str, asset_type: str = 'CRYPTO') -> Dict:
        """
        Analyze sentiment from multiple sources
        asset_type: 'CRYPTO' or 'STOCK'
        """
        results = {
            'news_sentiment': await self._analyze_news(symbol, asset_type),
            'social_sentiment': await self._analyze_social(symbol, asset_type),
            'technical_sentiment': await self._analyze_trading_view(symbol, asset_type),
            'overall_score': 0.0
        }
        
        # Calculate weighted sentiment score
        weights = {
            'news': 0.3,
            'social': 0.3,
            'technical': 0.4
        }
        
        results['overall_score'] = (
            results['news_sentiment']['score'] * weights['news'] +
            results['social_sentiment']['score'] * weights['social'] +
            results['technical_sentiment']['score'] * weights['technical']
        )
        
        return results
    
    async def _analyze_news(self, symbol: str, asset_type: str) -> Dict:
        sources = []
        all_news = []
        
        # DinoDigest (per azioni)
        if asset_type == 'STOCK':
            dino_news = self._get_dino_digest_news(symbol)
            all_news.extend(dino_news)
            sources.append('DinoDigest')
        
        # Coinbase News (per crypto)
        if asset_type == 'CRYPTO':
            coinbase_news = self._get_coinbase_news(symbol)
            all_news.extend(coinbase_news)
            sources.append('Coinbase')
        
        # Brave Search per entrambi
        if self.brave_search:
            search_term = f"{symbol} {'cryptocurrency' if asset_type == 'CRYPTO' else 'stock'} news"
            brave_news = await self.brave_search.search(search_term)
            all_news.extend(brave_news)
            sources.append('Brave Search')
        
        sentiment_score = self._calculate_news_sentiment(all_news)
        
        return {
            'score': sentiment_score,
            'news_count': len(all_news),
            'sources': sources,
            'recent_news': all_news[:5]  # ultimi 5 articoli
        }
    
    async def _analyze_social(self, symbol: str, asset_type: str) -> Dict:
        """
        Analyze sentiment from Reddit and other social platforms
        """
        reddit_sentiment = self._analyze_reddit(symbol, asset_type)
        
        return {
            'score': reddit_sentiment['score'],
            'mentions': reddit_sentiment['mentions'],
            'sources': ['Reddit'],
            'subreddits_analyzed': reddit_sentiment['subreddits']
        }
    
    def _analyze_reddit(self, symbol: str, asset_type: str) -> Dict:
        """
        Analyze Reddit sentiment
        """
        subreddits = []
        if asset_type == 'CRYPTO':
            subreddits = ['cryptocurrency', 'CryptoMarkets', symbol.lower()]
        else:
            subreddits = ['stocks', 'wallstreetbets', 'investing']
        
        mentions = 0
        sentiment_sum = 0
        
        for subreddit_name in subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                for post in subreddit.search(symbol, time_filter='week', limit=100):
                    mentions += 1
                    # Implementa qui la logica del sentiment sui post
                    
            except Exception as e:
                print(f"Error analyzing Reddit {subreddit_name}: {e}")
        
        return {
            'score': sentiment_sum / max(mentions, 1),
            'mentions': mentions,
            'subreddits': subreddits
        }
    
    async def _analyze_trading_view(self, symbol: str, asset_type: str) -> Dict:
        """
        Get technical analysis from TradingView
        """
        try:
            self.tv.symbol = symbol
            self.tv.screener = "crypto" if asset_type == 'CRYPTO' else "america"
            self.tv.exchange = "COINBASE" if asset_type == 'CRYPTO' else "NYSE"
            
            analysis = self.tv.get_analysis()
            
            return {
                'score': self._convert_tv_recommendation(analysis.summary['RECOMMENDATION']),
                'indicators': {
                    'oscillators': analysis.oscillators,
                    'moving_averages': analysis.moving_averages
                }
            }
        except Exception as e:
            print(f"Error getting TradingView analysis: {e}")
            return {'score': 0.0, 'indicators': {}}
    
    def _get_coinbase_news(self, symbol: str) -> List[Dict]:
        """
        Get news from Coinbase API
        """
        try:
            url = f"https://api.coinbase.com/v2/prices/{symbol}-USD/news"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching Coinbase news: {e}")
            return []
    
    def _convert_tv_recommendation(self, recommendation: str) -> float:
        """
        Convert TradingView recommendation to sentiment score
        """
        recommendations = {
            'STRONG_BUY': 1.0,
            'BUY': 0.75,
            'NEUTRAL': 0.5,
            'SELL': 0.25,
            'STRONG_SELL': 0.0
        }
        return recommendations.get(recommendation, 0.5)
    