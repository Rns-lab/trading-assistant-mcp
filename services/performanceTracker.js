const { RestClientV5 } = require('bybit-api');
const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs').promises;
const path = require('path');

class PerformanceTracker {
    constructor() {
        this.bybitClient = new RestClientV5({
            key: process.env.BYBIT_API_KEY,
            secret: process.env.BYBIT_API_SECRET
        });

        this.telegramBot = new TelegramBot(process.env.TELEGRAM_BOT_TOKEN, { polling: false });
        this.TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;
        
        this.performanceLogPath = path.join(__dirname, '../logs/performance.json');
    }

    async trackTrade(tradeDetails) {
        try {
            const performance = await this.loadPerformanceLog();
            performance.trades.push({
                ...tradeDetails,
                timestamp: new Date().toISOString()
            });
            await this.savePerformanceLog(performance);
        } catch (error) {
            console.error(`Error tracking trade: ${error.message}`);
            throw error;
        }
    }

    async loadPerformanceLog() {
        try {
            const data = await fs.readFile(this.performanceLogPath, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            // If file doesn't exist, create new performance log
            return { trades: [], dailyStats: [], monthlyStats: [] };
        }
    }

    async savePerformanceLog(performance) {
        await fs.writeFile(
            this.performanceLogPath,
            JSON.stringify(performance, null, 2)
        );
    }

    async analyzeDailyPerformance() {
        try {
            const today = new Date().toISOString().split('T')[0];
            const closedPnL = await this.bybitClient.getClosedPnL({
                category: 'linear',
                startTime: new Date(today).getTime()
            });

            const trades = closedPnL.result.list;
            const performance = await this.calculatePerformanceMetrics(trades);

            // Save daily stats
            const currentPerformance = await this.loadPerformanceLog();
            currentPerformance.dailyStats.push({
                date: today,
                ...performance
            });
            await this.savePerformanceLog(currentPerformance);

            await this.sendDailyReport(performance);
            return performance;
        } catch (error) {
            console.error(`Error analyzing daily performance: ${error.message}`);
            throw error;
        }
    }

    async calculatePerformanceMetrics(trades) {
        let totalPnL = 0;
        let winCount = 0;
        let lossCount = 0;
        let largestWin = 0;
        let largestLoss = 0;
        let totalFees = 0;

        trades.forEach(trade => {
            const pnl = parseFloat(trade.closedPnl);
            totalPnL += pnl;
            totalFees += parseFloat(trade.totalFees || 0);

            if (pnl > 0) {
                winCount++;
                largestWin = Math.max(largestWin, pnl);
            } else if (pnl < 0) {
                lossCount++;
                largestLoss = Math.min(largestLoss, pnl);
            }
        });

        const totalTrades = trades.length;
        const winRate = totalTrades > 0 ? (winCount / totalTrades) * 100 : 0;
        const averagePnL = totalTrades > 0 ? totalPnL / totalTrades : 0;
        const profitFactor = Math.abs(largestLoss) > 0 ? Math.abs(largestWin / largestLoss) : 0;

        return {
            totalTrades,
            winCount,
            lossCount,
            winRate,
            totalPnL,
            averagePnL,
            largestWin,
            largestLoss,
            profitFactor,
            totalFees,
            netProfit: totalPnL - totalFees
        };
    }

    async calculateDrawdown() {
        try {
            const balance = await this.bybitClient.getWalletBalance({
                accountType: 'CONTRACT'
            });

            const currentEquity = parseFloat(balance.result.list[0].totalEquity);
            const performance = await this.loadPerformanceLog();
            
            // Find highest equity point
            let highWaterMark = currentEquity;
            performance.dailyStats.forEach(stat => {
                if (stat.totalPnL > highWaterMark) {
                    highWaterMark = stat.totalPnL;
                }
            });

            const drawdown = ((highWaterMark - currentEquity) / highWaterMark) * 100;
            return {
                currentEquity,
                highWaterMark,
                drawdown
            };
        } catch (error) {
            console.error(`Error calculating drawdown: ${error.message}`);
            throw error;
        }
    }

    async sendDailyReport(performance) {
        const drawdown = await this.calculateDrawdown();
        const message = `
📊 Daily Performance Report 📊

Total Trades: ${performance.totalTrades}
Win Rate: ${performance.winRate.toFixed(2)}%
Net Profit: $${performance.netProfit.toFixed(2)}

📈 Wins: ${performance.winCount}
📉 Losses: ${performance.lossCount}
🎯 Average PnL: $${performance.averagePnL.toFixed(2)}

💰 Largest Win: $${performance.largestWin.toFixed(2)}
💸 Largest Loss: $${performance.largestLoss.toFixed(2)}
📊 Profit Factor: ${performance.profitFactor.toFixed(2)}

💵 Total Fees: $${performance.totalFees.toFixed(2)}
📉 Current Drawdown: ${drawdown.drawdown.toFixed(2)}%

High Water Mark: $${drawdown.highWaterMark.toFixed(2)}
Current Equity: $${drawdown.currentEquity.toFixed(2)}
`;

        await this.telegramBot.sendMessage(this.TELEGRAM_CHAT_ID, message);
    }

    async generateMonthlyReport() {
        try {
            const performance = await this.loadPerformanceLog();
            const currentMonth = new Date().toISOString().slice(0, 7); // YYYY-MM
            
            const monthlyTrades = performance.dailyStats.filter(stat => 
                stat.date.startsWith(currentMonth)
            );

            const monthlyMetrics = {
                month: currentMonth,
                totalPnL: monthlyTrades.reduce((sum, day) => sum + day.totalPnL, 0),
                totalTrades: monthlyTrades.reduce((sum, day) => sum + day.totalTrades, 0),
                averageWinRate: monthlyTrades.reduce((sum, day) => sum + day.winRate, 0) / monthlyTrades.length,
                totalFees: monthlyTrades.reduce((sum, day) => sum + day.totalFees, 0)
            };

            // Save monthly stats
            performance.monthlyStats.push(monthlyMetrics);
            await this.savePerformanceLog(performance);

            return monthlyMetrics;
        } catch (error) {
            console.error(`Error generating monthly report: ${error.message}`);
            throw error;
        }
    }
}

module.exports = PerformanceTracker; 