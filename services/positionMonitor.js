const { RestClientV5 } = require('bybit-api');
const TelegramBot = require('node-telegram-bot-api');

class PositionMonitor {
    constructor() {
        this.bybitClient = new RestClientV5({
            key: process.env.BYBIT_API_KEY,
            secret: process.env.BYBIT_API_SECRET
        });

        this.telegramBot = new TelegramBot(process.env.TELEGRAM_BOT_TOKEN, { polling: false });
        this.TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;
    }

    async monitorPosition(symbol) {
        try {
            const position = await this.bybitClient.getPositionInfo({
                category: 'linear',
                symbol: symbol
            });

            if (position.result.list.length > 0) {
                const pos = position.result.list[0];
                const unrealizedPnl = parseFloat(pos.unrealisedPnl);
                const entryPrice = parseFloat(pos.entryPrice);
                const currentQty = parseFloat(pos.size);
                const leverage = parseFloat(pos.leverage);
                const liquidationPrice = parseFloat(pos.liqPrice);

                // Calculate current ROE (Return on Equity)
                const roe = (unrealizedPnl / (entryPrice * currentQty / leverage)) * 100;

                // Send position update to Telegram
                await this.sendPositionUpdate({
                    symbol,
                    unrealizedPnl,
                    roe,
                    entryPrice,
                    currentQty,
                    leverage,
                    liquidationPrice
                });

                return {
                    hasPosition: true,
                    details: {
                        unrealizedPnl,
                        roe,
                        entryPrice,
                        currentQty,
                        leverage,
                        liquidationPrice
                    }
                };
            }

            return { hasPosition: false };
        } catch (error) {
            console.error(`Error monitoring position: ${error.message}`);
            throw error;
        }
    }

    async sendPositionUpdate(positionDetails) {
        const message = `
📊 Position Update 📊

Symbol: ${positionDetails.symbol}
Unrealized PnL: $${positionDetails.unrealizedPnl.toFixed(2)}
ROE: ${positionDetails.roe.toFixed(2)}%
Entry Price: $${positionDetails.entryPrice}
Position Size: ${positionDetails.currentQty}
Leverage: ${positionDetails.leverage}x
Liquidation Price: $${positionDetails.liquidationPrice}

⚠️ Liquidation Distance: ${(Math.abs(positionDetails.liquidationPrice - positionDetails.entryPrice) / positionDetails.entryPrice * 100).toFixed(2)}%
`;

        await this.telegramBot.sendMessage(this.TELEGRAM_CHAT_ID, message);
    }
}

module.exports = PositionMonitor; 