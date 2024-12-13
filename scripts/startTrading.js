require('dotenv').config();
const TradingOrchestrator = require('../services/tradingOrchestrator');
const logger = require('../services/logger');

let orchestrator = null;

async function startTrading() {
    console.log('Application starting...');
    logger.info('Application starting...');

    // Check environment variables first
    logger.info('Environment check', {
        hasBybitKey: !!process.env.BYBIT_API_KEY,
        hasBybitSecret: !!process.env.BYBIT_API_SECRET,
        hasTelegramToken: !!process.env.TELEGRAM_BOT_TOKEN,
        hasTelegramChatId: !!process.env.TELEGRAM_CHAT_ID
    });

    try {
        console.log('Creating orchestrator...');
        orchestrator = new TradingOrchestrator();
        
        console.log('Running system tests...');
        logger.info('Running system tests...');
        const testsPass = await orchestrator.testConnections();
        
        if (!testsPass) {
            throw new Error('System tests failed');
        }

        await orchestrator.initialize();
        logger.info('Trading system started successfully');
    } catch (error) {
        console.error('Startup error:', error);
        logger.error('Error starting trading system', { 
            context: 'startTrading',
            error: error.message,
            stack: error.stack
        });
        if (orchestrator) {
            await orchestrator.cleanup();
        }
        process.exit(1);
    }
}

// Handle process termination
process.on('SIGINT', async () => {
    console.log('Shutting down...');
    if (orchestrator) {
        await orchestrator.cleanup();
    }
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('Shutting down...');
    if (orchestrator) {
        await orchestrator.cleanup();
    }
    process.exit(0);
});

console.log('Starting trading system...');
startTrading(); 