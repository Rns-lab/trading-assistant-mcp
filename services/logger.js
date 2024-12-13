const winston = require('winston');

// Create a custom format
const customFormat = winston.format.combine(
    winston.format.timestamp(),
    winston.format.printf(({ timestamp, level, message, ...meta }) => {
        return JSON.stringify({ timestamp, level, message, ...meta });
    })
);

// Create the logger instance
const logger = winston.createLogger({
    level: 'info',
    format: customFormat,
    transports: [
        new winston.transports.Console(),
        new winston.transports.File({ filename: 'error.log', level: 'error' }),
        new winston.transports.File({ filename: 'combined.log' })
    ]
});

// Add explicit logging methods
const wrapLogger = {
    info: (message, meta = {}) => logger.info(message, meta),
    error: (message, meta = {}) => logger.error(message, meta),
    warn: (message, meta = {}) => logger.warn(message, meta),
    debug: (message, meta = {}) => logger.debug(message, meta)
};

module.exports = wrapLogger; 