const { RestClientV5 } = require('bybit-api');
const { expect } = require('chai');
require('dotenv').config();

describe('Bybit API Tests', () => {
    let client;

    before(() => {
        // Initialize the client before running tests
        client = new RestClientV5({
            key: process.env.BYBIT_API_KEY,
            secret: process.env.BYBIT_API_SECRET
        });
    });

    it('should connect to Bybit API successfully', async () => {
        // Using getServerTime instead of getApiKey to test connection
        const result = await client.getServerTime();
        expect(result.retCode).to.equal(0);
    });

    it('should fetch BTC/USDT ticker', async () => {
        const ticker = await client.getTickers({ category: 'spot', symbol: 'BTCUSDT' });
        expect(ticker.retCode).to.equal(0);
        expect(ticker.result.list).to.be.an('array');
    });

    it('should get wallet balance', async () => {
        const balance = await client.getWalletBalance({ accountType: 'UNIFIED' });
        expect(balance.retCode).to.equal(0);
    });
});
