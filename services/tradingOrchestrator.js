const { RestClientV5 } = require('bybit-api');
const TechnicalAnalysis = require('./technicalAnalysis');
const RiskManager = require('./riskManager');
const PerformanceTracker = require('./performanceTracker');
const logger = require('./logger');
const cron = require('node-cron');
const TelegramBot = require('node-telegram-bot-api');
const MarketScanner = require('./marketScanner');
const OrderExecutor = require('./orderExecutor');

class TradingOrchestrator {
    constructor() {
        // Initialize services
        this.bybitClient = new RestClientV5({
            key: process.env.BYBIT_API_KEY,
            secret: process.env.BYBIT_API_SECRET
        });

        this.technicalAnalysis = new TechnicalAnalysis();
        this.riskManager = new RiskManager();
        this.performanceTracker = new PerformanceTracker();
        this.marketScanner = new MarketScanner(this.bybitClient);
        
        this.telegramBot = new TelegramBot(process.env.TELEGRAM_BOT_TOKEN, { 
            polling: false
        });
        this.TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

        this.orderExecutor = new OrderExecutor();

        // Add error handler for polling errors
        this.telegramBot.on('polling_error', (error) => {
            logger.error('Telegram polling error', {
                context: 'TradingOrchestrator.telegramBot',
                error: error.message
            });
            // Optionally restart polling after error
            this.telegramBot.stopPolling().then(() => {
                setTimeout(() => {
                    this.telegramBot.startPolling();
                }, 5000); // Wait 5 seconds before restarting
            });
        });

        // Trading state
        this.activeSymbols = ['BTCUSDT', 'ETHUSDT']; // Add more pairs as needed
        this.pendingSignals = new Map();
        
        this.setupTelegramHandlers();
        this.setupCleanup();
    }

    setupCleanup() {
        // Handle application shutdown
        process.on('SIGINT', async () => {
            await this.cleanup();
            process.exit(0);
        });

        process.on('SIGTERM', async () => {
            await this.cleanup();
            process.exit(0);
        });
    }

    async cleanup() {
        logger.info('Cleaning up resources...');
        if (this.telegramBot) {
            await this.telegramBot.stopPolling();
        }
    }

    async initialize() {
        try {
            logger.info('Initializing Trading Orchestrator');
            
            // First, delete any existing webhook
            await this.telegramBot.deleteWebHook({ drop_pending_updates: true });
            
            // Ensure polling is completely stopped
            try {
                await this.telegramBot.stopPolling();
                // Add a longer delay to ensure complete shutdown
                await new Promise(resolve => setTimeout(resolve, 5000));
            } catch (error) {
                logger.warn('Error stopping existing polling', { error: error.message });
            }
            
            // Start Telegram bot polling with specific options
            await this.telegramBot.startPolling({
                polling: {
                    interval: 300,
                    autoStart: true,
                    params: {
                        timeout: 10,
                        allowed_updates: ['message']
                    }
                }
            });

            // Send a test message to verify bot is working
            await this.telegramBot.sendMessage(
                this.TELEGRAM_CHAT_ID, 
                '🤖 Trading Bot initialized and ready!'
            );
            
            // Start scheduled tasks
            this.startScheduledTasks();
            
            // Start market scanning
            await this.marketScanner.startContinuousScanning(this.activeSymbols);
            
            // Initial market analysis
            await this.analyzeAllMarkets();
            
            logger.info('Trading Orchestrator initialized successfully');
        } catch (error) {
            logger.error('Error initializing Trading Orchestrator', { 
                context: 'TradingOrchestrator.initialize',
                error: error.message,
                stack: error.stack
            });
            await this.cleanup();
            throw error;
        }
    }

    setupTelegramHandlers() {
        this.telegramBot.onText(/\/approve (.+)/, async (msg, match) => {
            if (msg.chat.id.toString() !== this.TELEGRAM_CHAT_ID) return;
            
            const signalId = match[1];
            await this.executeSignal(signalId);
        });

        this.telegramBot.onText(/\/reject (.+)/, async (msg, match) => {
            if (msg.chat.id.toString() !== this.TELEGRAM_CHAT_ID) return;
            
            const signalId = match[1];
            this.pendingSignals.delete(signalId);
            await this.telegramBot.sendMessage(this.TELEGRAM_CHAT_ID, `Signal ${signalId} rejected`);
        });

        this.telegramBot.onText(/\/test/, async (msg) => {
            if (msg.chat.id.toString() !== this.TELEGRAM_CHAT_ID) return;
            await this.telegramBot.sendMessage(
                this.TELEGRAM_CHAT_ID,
                '✅ Bot is working correctly!'
            );
        });
    }

    startScheduledTasks() {
        // Market analysis every hour
        cron.schedule('0 * * * *', () => this.analyzeAllMarkets());
        
        // Daily performance report
        cron.schedule('0 0 * * *', () => this.performanceTracker.analyzeDailyPerformance());
        
        // Monthly performance report
        cron.schedule('0 0 1 * *', () => this.performanceTracker.generateMonthlyReport());
        
        // Risk assessment every 15 minutes
        cron.schedule('*/15 * * * *', () => this.assessRisk());
    }

    async analyzeAllMarkets() {
        logger.info('Starting market analysis for all symbols');
        
        for (const symbol of this.activeSymbols) {
            try {
                // Get technical analysis
                const analysis = await this.technicalAnalysis.analyzeMarket(symbol);
                
                // Check if any signals were generated
                if (analysis.signals.length > 0) {
                    await this.processSignals(symbol, analysis);
                }
                
                logger.debug(`Analysis completed for ${symbol}`, { analysis });
            } catch (error) {
                logger.error(`Error analyzing market for ${symbol}`, { 
                    context: 'analyzeAllMarkets', 
                    symbol,
                    error: error.message,
                    stack: error.stack
                });
            }
        }
    }

    async processSignals(symbol, analysis) {
        const signalId = `${symbol}-${Date.now()}`;
        
        // Store signal for later execution
        this.pendingSignals.set(signalId, {
            symbol,
            analysis,
            timestamp: new Date()
        });

        // Prepare telegram message
        const message = `
🔔 New Trading Signal 🔔

Symbol: ${symbol}
Price: $${analysis.price}

Technical Indicators:
RSI: ${analysis.indicators.rsi.toFixed(2)}
MACD: ${analysis.indicators.macd.macd.toFixed(2)}
BB Position: ${this.getBollingerPosition(analysis)}

Signals:
${analysis.signals.map(s => `- ${s.type}: ${s.action} (${s.strength})`).join('\n')}

To execute this trade:
/approve ${signalId}

To reject:
/reject ${signalId}
`;

        await this.telegramBot.sendMessage(this.TELEGRAM_CHAT_ID, message);
        logger.logSignal({ signalId, symbol, analysis });
    }

    getBollingerPosition(analysis) {
        const { price, indicators } = analysis;
        const { bollinger } = indicators;
        
        if (price >= bollinger.upper) return "Above Upper Band";
        if (price <= bollinger.lower) return "Below Lower Band";
        return "Between Bands";
    }

    async executeSignal(signalId) {
        const signal = this.pendingSignals.get(signalId);
        if (!signal) {
            await this.telegramBot.sendMessage(this.TELEGRAM_CHAT_ID, 'Signal expired or not found');
            return;
        }

        try {
            const { symbol, analysis, exchange = 'BYBIT' } = signal;
            
            // Determine if this is intraday (Bybit with leverage) or swing (Binance spot)
            const isIntraday = exchange === 'BYBIT';
            
            // Prepare order parameters
            const orderParams = {
                symbol: symbol,
                exchange: exchange,
                side: analysis.signals[0].action,
                leverage: isIntraday ? 5 : 1, // Example leverage for intraday
                riskPercentage: isIntraday ? 1 : 0.5, // Lower risk for swing trades
                stopLossPercentage: isIntraday ? 1 : 2, // Tighter stops for intraday
                takeProfitMultiplier: isIntraday ? 2 : 3 // Different R:R for different timeframes
            };

            // Execute the trade using your existing OrderExecutor
            const order = await this.orderExecutor.executeOrder(orderParams);

            // Send confirmation
            await this.telegramBot.sendMessage(
                this.TELEGRAM_CHAT_ID,
                `✅ Trade executed:\n` +
                `Symbol: ${symbol}\n` +
                `Exchange: ${exchange}\n` +
                `Type: ${isIntraday ? 'Intraday (Leveraged)' : 'Swing Trade'}\n` +
                `Action: ${orderParams.side}\n` +
                `Leverage: ${orderParams.leverage}x\n` +
                `Risk: ${orderParams.riskPercentage}%\n` +
                `Order ID: ${order.orderId || order.id}`
            );

            this.pendingSignals.delete(signalId);
        } catch (error) {
            logger.error('Error executing signal', {
                context: 'executeSignal',
                signalId,
                error: error.message
            });
            await this.telegramBot.sendMessage(
                this.TELEGRAM_CHAT_ID,
                `❌ Error executing trade: ${error.message}`
            );
        }
    }

    calculateStopLoss(analysis) {
        // Implement your stop loss calculation logic
        // This is a simple example using Bollinger Bands
        return analysis.indicators.bollinger.lower;
    }

    async executeTrade(symbol, analysis) {
        // Implement your trade execution logic
        // This should interface with your OrderExecutor service
        logger.logTrade({
            symbol,
            action: analysis.signals[0].action,
            price: analysis.price,
            timestamp: new Date()
        });
    }

    async assessRisk() {
        try {
            const riskStatus = await this.riskManager.checkAccountRisk();
            if (!riskStatus.isWithinRiskLimits) {
                await this.telegramBot.sendMessage(
                    this.TELEGRAM_CHAT_ID,
                    `⚠️ Risk limits exceeded:\nMargin Usage: ${riskStatus.marginUtilization}%\nDaily Risk: ${riskStatus.remainingDayRisk}`
                );
            }
        } catch (error) {
            logger.error(error, { context: 'assessRisk' });
        }
    }

    async testConnections() {
        try {
            logger.info('Starting connection tests...');

            // Test 1: Telegram Bot
            logger.info('Testing Telegram connection...');
            await this.telegramBot.getMe()
                .then(botInfo => {
                    logger.info('Telegram connection successful', { botInfo });
                });

            // Test 2: Bybit API
            logger.info('Testing Bybit API connection...');
            const testSymbol = 'BTCUSDT';
            const klines = await this.technicalAnalysis.getKlines(testSymbol, '15', 1);
            logger.info('Bybit API connection successful', { 
                symbol: testSymbol,
                dataPoints: klines.length 
            });

            logger.info('All connection tests passed successfully');
            return true;
        } catch (error) {
            logger.error('Connection test failed', {
                context: 'TradingOrchestrator.testConnections',
                error: error.message,
                stack: error.stack
            });
            return false;
        }
    }
}

module.exports = TradingOrchestrator; 