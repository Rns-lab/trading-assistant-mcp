const fs = require('fs');
const path = require('path');
const logger = require('../services/logger');

class LogManager {
    constructor() {
        this.logDir = path.join(__dirname, '../logs');
        this.maxLogSize = 100 * 1024 * 1024; // 100MB total log size
    }

    async checkLogSize() {
        try {
            let totalSize = 0;
            const files = await fs.promises.readdir(this.logDir);

            for (const file of files) {
                const stats = await fs.promises.stat(path.join(this.logDir, file));
                totalSize += stats.size;
            }

            if (totalSize > this.maxLogSize) {
                await this.cleanOldLogs();
            }

            return totalSize;
        } catch (error) {
            logger.logError(error, { context: 'LogManager.checkLogSize' });
        }
    }

    async cleanOldLogs() {
        try {
            const files = await fs.promises.readdir(this.logDir);
            const logFiles = files.map(file => ({
                name: file,
                path: path.join(this.logDir, file),
                created: fs.statSync(path.join(this.logDir, file)).birthtime
            }));

            // Sort by creation date
            logFiles.sort((a, b) => a.created - b.created);

            // Keep the most recent logs, delete older ones
            for (let i = 0; i < logFiles.length - 10; i++) {
                await fs.promises.unlink(logFiles[i].path);
                logger.debug(`Deleted old log file: ${logFiles[i].name}`);
            }
        } catch (error) {
            logger.logError(error, { context: 'LogManager.cleanOldLogs' });
        }
    }
}

module.exports = new LogManager(); 