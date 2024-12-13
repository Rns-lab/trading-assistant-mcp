const { RestClientV5 } = require('bybit-api');
const technicalindicators = require('technicalindicators');
const logger = require('./logger');

class TechnicalAnalysis {
    constructor() {
        this.bybitClient = new RestClientV5({
            key: process.env.BYBIT_API_KEY,
            secret: process.env.BYBIT_API_SECRET
        });
    }

    async getKlines(symbol, interval = '15', limit = 200) {
        try {
            logger.info(`Fetching klines for ${symbol}`, {
                context: 'TechnicalAnalysis.getKlines',
                symbol,
                interval,
                limit
            });

            const klines = await this.bybitClient.getKline({
                category: 'linear',
                symbol: symbol,
                interval: interval,
                limit: limit
            });

            logger.debug('Klines response', {
                context: 'TechnicalAnalysis.getKlines',
                response: klines
            });

            if (!klines?.result?.list) {
                throw new Error(`Invalid klines response for ${symbol}: ${JSON.stringify(klines)}`);
            }

            const mappedKlines = klines.result.list.map(k => ({
                timestamp: parseInt(k[0]),
                open: parseFloat(k[1]),
                high: parseFloat(k[2]),
                low: parseFloat(k[3]),
                close: parseFloat(k[4]),
                volume: parseFloat(k[5])
            })).reverse();

            logger.info(`Successfully fetched klines for ${symbol}`, {
                context: 'TechnicalAnalysis.getKlines',
                dataPoints: mappedKlines.length
            });

            return mappedKlines;
        } catch (error) {
            logger.error(`Error fetching klines for ${symbol}`, {
                context: 'TechnicalAnalysis.getKlines',
                error: error.message,
                symbol,
                interval,
                stack: error.stack
            });
            throw error;
        }
    }

    async analyzeMarket(symbol) {
        try {
            const klines = await this.getKlines(symbol);
            
            if (!klines || klines.length === 0) {
                throw new Error(`No klines data available for ${symbol}`);
            }

            // Extract data points
            const closes = klines.map(k => k.close);
            const highs = klines.map(k => k.high);
            const lows = klines.map(k => k.low);
            const volumes = klines.map(k => k.volume);

            // Calculate indicators with null checks
            const rsi = this.calculateRSI(closes) || [];
            const macd = this.calculateMACD(closes) || { MACD: [], signal: [] };
            const bollinger = this.calculateBollingerBands(closes) || { upper: [], middle: [], lower: [] };
            const volume_sma = this.calculateVolumeSMA(volumes) || [];

            // Verify we have enough data
            if (rsi.length === 0 || macd.MACD.length === 0 || bollinger.upper.length === 0) {
                throw new Error(`Insufficient data to calculate indicators for ${symbol}`);
            }

            // Get current values
            const currentPrice = closes[0];
            const currentRSI = rsi[rsi.length - 1];
            const currentMACD = macd.MACD[macd.MACD.length - 1];
            const currentSignal = macd.signal[macd.signal.length - 1];
            const currentBollinger = {
                upper: bollinger.upper[bollinger.upper.length - 1],
                middle: bollinger.middle[bollinger.middle.length - 1],
                lower: bollinger.lower[bollinger.lower.length - 1]
            };

            logger.debug(`Analysis completed for ${symbol}`, {
                price: currentPrice,
                rsi: currentRSI,
                macd: currentMACD,
                signal: currentSignal,
                bollinger: currentBollinger
            });

            return {
                symbol,
                timestamp: new Date(),
                price: currentPrice,
                indicators: {
                    rsi: currentRSI,
                    macd: {
                        macd: currentMACD,
                        signal: currentSignal,
                        histogram: currentMACD - currentSignal
                    },
                    bollinger: currentBollinger,
                    volumeSMA: volume_sma[volume_sma.length - 1]
                },
                signals: this.generateSignals({
                    rsi: currentRSI,
                    macd: currentMACD,
                    signal: currentSignal,
                    bollinger: currentBollinger,
                    price: currentPrice
                })
            };
        } catch (error) {
            logger.error(`Error analyzing market for ${symbol}`, {
                context: 'TechnicalAnalysis.analyzeMarket',
                error: error.message,
                symbol
            });
            throw error;
        }
    }

    calculateRSI(values, period = 14) {
        return technicalindicators.RSI.calculate({
            values: values,
            period: period
        });
    }

    calculateMACD(values) {
        return technicalindicators.MACD.calculate({
            values: values,
            fastPeriod: 12,
            slowPeriod: 26,
            signalPeriod: 9,
            SimpleMAOscillator: false,
            SimpleMASignal: false
        });
    }

    calculateBollingerBands(values, period = 20, stdDev = 2) {
        return technicalindicators.BollingerBands.calculate({
            values: values,
            period: period,
            stdDev: stdDev
        });
    }

    calculateVolumeSMA(volumes, period = 20) {
        return technicalindicators.SMA.calculate({
            values: volumes,
            period: period
        });
    }

    generateSignals(indicators) {
        const signals = [];

        // RSI Signals
        if (indicators.rsi < 30) {
            signals.push({
                type: 'RSI',
                action: 'BUY',
                strength: 'STRONG',
                reason: 'Oversold condition'
            });
        } else if (indicators.rsi > 70) {
            signals.push({
                type: 'RSI',
                action: 'SELL',
                strength: 'STRONG',
                reason: 'Overbought condition'
            });
        }

        // MACD Signals
        if (indicators.macd > indicators.signal) {
            signals.push({
                type: 'MACD',
                action: 'BUY',
                strength: 'MODERATE',
                reason: 'MACD crossed above signal line'
            });
        } else if (indicators.macd < indicators.signal) {
            signals.push({
                type: 'MACD',
                action: 'SELL',
                strength: 'MODERATE',
                reason: 'MACD crossed below signal line'
            });
        }

        // Bollinger Bands Signals
        if (indicators.price <= indicators.bollinger.lower) {
            signals.push({
                type: 'BOLLINGER',
                action: 'BUY',
                strength: 'STRONG',
                reason: 'Price at lower Bollinger Band'
            });
        } else if (indicators.price >= indicators.bollinger.upper) {
            signals.push({
                type: 'BOLLINGER',
                action: 'SELL',
                strength: 'STRONG',
                reason: 'Price at upper Bollinger Band'
            });
        }

        return signals;
    }

    async getFundingRate(symbol) {
        try {
            const fundingRate = await this.bybitClient.getFundingRate({
                category: 'linear',
                symbol: symbol
            });
            return parseFloat(fundingRate.result.list[0].fundingRate);
        } catch (error) {
            console.error(`Error fetching funding rate: ${error.message}`);
            throw error;
        }
    }
}

module.exports = TechnicalAnalysis; 