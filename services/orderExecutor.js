const { RestClientV5 } = require('bybit-api');
const { Spot } = require('@binance/connector');

class OrderExecutor {
    constructor() {
        this.bybitClient = new RestClientV5({
            key: process.env.BYBIT_API_KEY,
            secret: process.env.BYBIT_API_SECRET
        });

        this.binanceClient = new Spot(
            process.env.BINANCE_API_KEY,
            process.env.BINANCE_API_SECRET
        );
    }

    async setLeverage(symbol, leverage, exchange = 'BYBIT') {
        try {
            if (exchange === 'BYBIT') {
                await this.bybitClient.setLeverage({
                    category: 'linear',
                    symbol: symbol,
                    buyLeverage: leverage,
                    sellLeverage: leverage
                });
            }
            // Note: Binance leverage setting would go here if needed
        } catch (error) {
            console.error(`Error setting leverage: ${error.message}`);
            throw error;
        }
    }

    async calculatePositionSize(symbol, riskAmount, stopLossPercentage) {
        try {
            // Get account balance
            const balance = await this.bybitClient.getWalletBalance({
                accountType: 'CONTRACT'
            });

            const availableBalance = parseFloat(balance.result.list[0].totalAvailableBalance);
            const maxRiskAmount = availableBalance * (riskAmount / 100);

            // Get current price
            const ticker = await this.bybitClient.getTickers({
                category: 'linear',
                symbol: symbol
            });
            const currentPrice = parseFloat(ticker.result.list[0].lastPrice);

            // Calculate position size based on risk
            const stopLossDistance = currentPrice * (stopLossPercentage / 100);
            const positionSize = maxRiskAmount / stopLossDistance;

            return {
                positionSize: positionSize,
                currentPrice: currentPrice,
                stopLossPrice: currentPrice - stopLossDistance
            };
        } catch (error) {
            console.error(`Error calculating position size: ${error.message}`);
            throw error;
        }
    }

    async executeOrder(orderParams) {
        const {
            symbol,
            exchange,
            side,
            leverage = 1,
            riskPercentage = 1,
            stopLossPercentage = 1,
            takeProfitMultiplier = 2
        } = orderParams;

        try {
            // Set leverage first
            await this.setLeverage(symbol, leverage, exchange);

            // Calculate position size and prices
            const { positionSize, currentPrice, stopLossPrice } = 
                await this.calculatePositionSize(symbol, riskPercentage, stopLossPercentage);

            // Calculate take profit price
            const takeProfitDistance = Math.abs(currentPrice - stopLossPrice) * takeProfitMultiplier;
            const takeProfitPrice = side === 'BUY' 
                ? currentPrice + takeProfitDistance 
                : currentPrice - takeProfitDistance;

            // Place the order
            if (exchange === 'BYBIT') {
                return await this.bybitClient.submitOrder({
                    category: 'linear',
                    symbol: symbol,
                    side: side,
                    orderType: 'Market',
                    qty: positionSize.toFixed(4),
                    stopLoss: stopLossPrice.toFixed(2),
                    takeProfit: takeProfitPrice.toFixed(2),
                    timeInForce: 'GoodTillCancel',
                    positionIdx: 0  // 0 for one-way mode
                });
            } else if (exchange === 'BINANCE') {
                // Implement Binance order execution
                // This would be similar but use binanceClient instead
            }
        } catch (error) {
            console.error(`Error executing order: ${error.message}`);
            throw error;
        }
    }
}

module.exports = OrderExecutor; 