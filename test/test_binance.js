// test/test_binance.js
require('dotenv').config();
const { expect } = require('chai');
const BinanceService = require('../src/services/binance-service');

describe('Binance Service', () => {
    let binance;

    before(() => {
        try {
            binance = new BinanceService();
        } catch (error) {
            console.error('Error initializing BinanceService:', error);
            throw error;
        }
    });

    it('should successfully connect and get BTC price', async () => {
        try {
            const price = await binance.client.prices({ symbol: 'BTCUSDT' });
            const btcPrice = parseFloat(price.BTCUSDT);
            console.log('BTC Price:', price.BTCUSDT);
            expect(btcPrice).to.be.a('number');
            expect(btcPrice).to.be.above(0);
        } catch (error) {
            console.error('Error getting BTC price:', error);
            throw error;
        }
    });

    it('should successfully fetch account balance and permissions', async () => {
        const balance = await binance.getBalance();
        expect(balance).to.have.property('makerCommission');
        expect(balance).to.have.property('takerCommission');
        expect(balance).to.have.property('canTrade');
    });
});