const Binance = require('binance-api-node').default;

class BinanceService {
    constructor() {
        this.client = Binance({
            apiKey: process.env.BINANCE_API_KEY,
            apiSecret: process.env.BINANCE_SECRET_KEY
        });
    }

    async getPrice(symbol) {
        try {
            const ticker = await this.client.prices({ symbol });
            return ticker[symbol];
        } catch (error) {
            throw new Error(`Failed to get price: ${error.message}`);
        }
    }

    async getBalance() {
        try {
            return await this.client.accountInfo();
        } catch (error) {
            throw new Error(`Failed to get balance: ${error.message}`);
        }
    }

    async placeOrder(symbol, side, quantity, price = null) {
        try {
            const order = price 
                ? { symbol, side, quantity, price, type: 'LIMIT' }
                : { symbol, side, quantity, type: 'MARKET' };
            return await this.client.order(order);
        } catch (error) {
            throw new Error(`Failed to place order: ${error.message}`);
        }
    }
}

module.exports = BinanceService;