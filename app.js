require('dotenv').config();
const TradingOrchestrator = require('./services/tradingOrchestrator');

async function main() {
    const tradingOrchestrator = new TradingOrchestrator();
    
    try {
        // Test connections first
        const connectionsOk = await tradingOrchestrator.testConnections();
        if (!connectionsOk) {
            console.error('Connection tests failed. Exiting...');
            process.exit(1);
        }

        // Initialize the trading orchestrator
        await tradingOrchestrator.initialize();
        
        console.log('Trading bot started successfully');
    } catch (error) {
        console.error('Failed to start trading bot:', error);
        process.exit(1);
    }
}

main();
