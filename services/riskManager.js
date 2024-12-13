const { RestClientV5 } = require('bybit-api');
const TelegramBot = require('node-telegram-bot-api');

class RiskManager {
    constructor() {
        this.bybitClient = new RestClientV5({
            key: process.env.BYBIT_API_KEY,
            secret: process.env.BYBIT_API_SECRET
        });

        this.telegramBot = new TelegramBot(process.env.TELEGRAM_BOT_TOKEN, { polling: false });
        this.TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

        // Default risk parameters
        this.maxPositionSize = 0.1; // 10% of account
        this.maxDailyLoss = 0.05;   // 5% of account
        this.maxLeverage = 10;      // Maximum leverage
        this.riskPerTrade = 0.01;   // 1% risk per trade
    }

    async checkAccountRisk() {
        try {
            const balance = await this.bybitClient.getWalletBalance({
                accountType: 'CONTRACT'
            });

            const accountValue = parseFloat(balance.result.list[0].totalEquity);
            const availableBalance = parseFloat(balance.result.list[0].availableBalance);
            const usedMargin = parseFloat(balance.result.list[0].totalMarginUsed || 0);

            // Calculate risk metrics
            const marginUtilization = (usedMargin / accountValue) * 100;
            const remainingDayRisk = await this.calculateRemainingDayRisk();

            return {
                accountValue,
                availableBalance,
                usedMargin,
                marginUtilization,
                remainingDayRisk,
                isWithinRiskLimits: this.checkRiskLimits(marginUtilization, remainingDayRisk)
            };
        } catch (error) {
            console.error(`Error checking account risk: ${error.message}`);
            throw error;
        }
    }

    async calculatePositionSize(symbol, entryPrice, stopLoss) {
        try {
            const accountRisk = await this.checkAccountRisk();
            const riskAmount = accountRisk.accountValue * this.riskPerTrade;
            const stopLossDistance = Math.abs(entryPrice - stopLoss);
            const riskPerUnit = stopLossDistance;

            let positionSize = riskAmount / riskPerUnit;

            // Check against maximum position size
            const maxPositionValue = accountRisk.accountValue * this.maxPositionSize;
            const maxPositionSize = maxPositionValue / entryPrice;

            positionSize = Math.min(positionSize, maxPositionSize);

            return {
                positionSize,
                riskAmount,
                maxLeverage: this.calculateSafeLeverage(entryPrice, stopLoss)
            };
        } catch (error) {
            console.error(`Error calculating position size: ${error.message}`);
            throw error;
        }
    }

    calculateSafeLeverage(entryPrice, stopLoss) {
        // Calculate the distance to stopLoss as a percentage
        const stopLossDistance = Math.abs(entryPrice - stopLoss) / entryPrice;
        
        // Use the inverse of the distance as the maximum safe leverage
        let safeLeverage = Math.floor(1 / stopLossDistance);
        
        // Cap at maximum allowed leverage
        return Math.min(safeLeverage, this.maxLeverage);
    }

    async calculateRemainingDayRisk() {
        try {
            // Get today's PnL
            const today = new Date().toISOString().split('T')[0];
            const pnl = await this.bybitClient.getClosedPnL({
                category: 'linear',
                startTime: new Date(today).getTime()
            });

            let dailyPnL = 0;
            pnl.result.list.forEach(trade => {
                dailyPnL += parseFloat(trade.closedPnl);
            });

            const balance = await this.bybitClient.getWalletBalance({
                accountType: 'CONTRACT'
            });
            const accountValue = parseFloat(balance.result.list[0].totalEquity);

            // Calculate remaining risk for the day
            const maxDailyLossAmount = accountValue * this.maxDailyLoss;
            const remainingRisk = maxDailyLossAmount + dailyPnL; // If dailyPnL is negative, this reduces remaining risk

            return remainingRisk;
        } catch (error) {
            console.error(`Error calculating remaining day risk: ${error.message}`);
            throw error;
        }
    }

    checkRiskLimits(marginUtilization, remainingDayRisk) {
        // Define risk thresholds
        const MAX_MARGIN_UTILIZATION = 80; // 80%
        const MIN_REMAINING_RISK = 0; // No more trades if daily loss limit reached

        return marginUtilization < MAX_MARGIN_UTILIZATION && 
               remainingDayRisk > MIN_REMAINING_RISK;
    }

    async validateTrade(symbol, side, entryPrice, stopLoss, leverage) {
        try {
            const accountRisk = await this.checkAccountRisk();
            const { positionSize, maxLeverage } = await this.calculatePositionSize(symbol, entryPrice, stopLoss);

            const validationResults = {
                isValid: true,
                warnings: [],
                errors: []
            };

            // Check leverage
            if (leverage > maxLeverage) {
                validationResults.errors.push(`Leverage ${leverage}x exceeds maximum safe leverage of ${maxLeverage}x`);
                validationResults.isValid = false;
            }

            // Check margin utilization
            if (accountRisk.marginUtilization > 75) {
                validationResults.warnings.push(`High margin utilization: ${accountRisk.marginUtilization.toFixed(2)}%`);
            }

            // Check remaining day risk
            if (accountRisk.remainingDayRisk < 0) {
                validationResults.errors.push('Daily loss limit reached');
                validationResults.isValid = false;
            }

            // If there are any errors, send alert
            if (!validationResults.isValid) {
                await this.sendRiskAlert(validationResults);
            }

            return validationResults;
        } catch (error) {
            console.error(`Error validating trade: ${error.message}`);
            throw error;
        }
    }

    async sendRiskAlert(validationResults) {
        const message = `
⚠️ Risk Alert ⚠️

${validationResults.errors.length > 0 ? '❌ Errors:\n' + validationResults.errors.join('\n') : ''}
${validationResults.warnings.length > 0 ? '⚠️ Warnings:\n' + validationResults.warnings.join('\n') : ''}
`;

        await this.telegramBot.sendMessage(this.TELEGRAM_CHAT_ID, message);
    }
}

module.exports = RiskManager; 