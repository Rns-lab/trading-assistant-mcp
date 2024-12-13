const logger = require('./logger');

class MarketScanner {
    constructor(bybitClient) {
        this.bybitClient = bybitClient;
        this.scanInterval = 15 * 60 * 1000; // 15 minutes in milliseconds
    }

    async scanMarket(symbol) {
        try {
            // Get market data
            const klines = await this.bybitClient.getKline({
                category: 'spot',
                symbol: symbol,
                interval: '15', // 15 minute candles
                limit: 100
            });

            // Calculate price changes
            const priceChange = await this.calculatePriceChanges(klines.result.list);
            
            // Calculate volume analysis
            const volumeAnalysis = await this.analyzeVolume(klines.result.list);
            
            // Detect any significant market movements
            const movements = await this.detectMarketMovements(klines.result.list);

            return {
                symbol,
                timestamp: new Date(),
                priceChange,
                volumeAnalysis,
                movements
            };

        } catch (error) {
            logger.error('Error in market scanning', {
                context: 'MarketScanner.scanMarket',
                symbol,
                error: error.message
            });
            throw error;
        }
    }

    async calculatePriceChanges(klines) {
        const latest = klines[0];
        const previous = klines[1];

        return {
            percentChange: ((latest[4] - previous[4]) / previous[4]) * 100,
            absoluteChange: latest[4] - previous[4],
            currentPrice: latest[4]
        };
    }

    async analyzeVolume(klines) {
        // Calculate average volume
        const volumes = klines.map(k => parseFloat(k[5]));
        const avgVolume = volumes.reduce((a, b) => a + b, 0) / volumes.length;
        const latestVolume = volumes[0];

        return {
            averageVolume: avgVolume,
            currentVolume: latestVolume,
            volumeIncrease: (latestVolume / avgVolume - 1) * 100
        };
    }

    async detectMarketMovements(klines) {
        const movements = [];
        const latestCandle = klines[0];
        
        // Detect large price movements
        const candleSize = Math.abs(latestCandle[1] - latestCandle[4]);
        const averagePrice = (parseFloat(latestCandle[1]) + parseFloat(latestCandle[4])) / 2;
        const movement = (candleSize / averagePrice) * 100;

        if (movement > 1) { // More than 1% movement
            movements.push({
                type: 'LARGE_PRICE_MOVEMENT',
                value: movement,
                direction: latestCandle[1] > latestCandle[4] ? 'DOWN' : 'UP'
            });
        }

        return movements;
    }

    async startContinuousScanning(symbols) {
        setInterval(async () => {
            for (const symbol of symbols) {
                try {
                    const scanResult = await this.scanMarket(symbol);
                    this.processScanResult(scanResult);
                } catch (error) {
                    logger.error('Error in continuous scanning', {
                        context: 'MarketScanner.startContinuousScanning',
                        symbol,
                        error: error.message
                    });
                }
            }
        }, this.scanInterval);
    }

    async processScanResult(result) {
        // Log significant findings
        if (Math.abs(result.priceChange.percentChange) > 2) {
            logger.info('Significant price movement detected', {
                context: 'MarketScanner.processScanResult',
                symbol: result.symbol,
                priceChange: result.priceChange
            });
        }

        if (result.volumeAnalysis.volumeIncrease > 200) {
            logger.info('Unusual volume detected', {
                context: 'MarketScanner.processScanResult',
                symbol: result.symbol,
                volumeAnalysis: result.volumeAnalysis
            });
        }

        return result;
    }
}

module.exports = MarketScanner;
