import * as winston from 'winston';

const { format, transports } = winston;

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface ILogger {
  debug(message: string, context?: object): void;
  info(message: string, context?: object): void;
  warn(message: string, context?: object): void;
  error(message: string, error?: Error, context?: object): void;
}

export interface LoggerConfig {
  level: LogLevel;
  format: 'json' | 'simple';
  transports: winston.transport[];
}

export interface LogEntry {
  timestamp: Date;
  level: LogLevel;
  message: string;
  component: string;
  context?: Record<string, unknown>;
  error?: {
    name: string;
    message: string;
    stack?: string;
  };
}

class ComponentLogger implements ILogger {
  constructor(
    private logger: winston.Logger,
    private component: string
  ) {}

  debug(message: string, context?: object): void {
    this.logger.debug(message, { component: this.component, ...context });
  }

  info(message: string, context?: object): void {
    this.logger.info(message, { component: this.component, ...context });
  }

  warn(message: string, context?: object): void {
    this.logger.warn(message, { component: this.component, ...context });
  }

  error(message: string, error?: Error, context?: object): void {
    const errorInfo = error
      ? {
          name: error.name,
          message: error.message,
          stack: error.stack,
        }
      : undefined;

    this.logger.error(message, {
      component: this.component,
      error: errorInfo,
      ...context,
    });
  }
}

export class LoggerService {
  private static instance: LoggerService;
  private winston: winston.Logger;
  private loggers: Map<string, ComponentLogger> = new Map();

  private constructor() {
    const isDevelopment = process.env.NODE_ENV === 'development';
    const logLevel =
      (process.env.LOG_LEVEL as LogLevel) || (isDevelopment ? 'debug' : 'info');

    // Create Winston logger with environment-based configuration
    this.winston = winston.createLogger({
      level: logLevel,
      format: format.combine(
        format.timestamp(),
        format.errors({ stack: true }),
        isDevelopment
          ? format.combine(
              format.colorize(),
              format.printf(
                ({ timestamp, level, message, component, ...meta }) => {
                  const contextStr =
                    Object.keys(meta).length > 0
                      ? ` ${JSON.stringify(meta)}`
                      : '';
                  const componentStr = component ? `[${component}]` : '';
                  return `${timestamp} ${level} ${componentStr} ${message}${contextStr}`;
                }
              )
            )
          : format.json()
      ),
      transports: [
        new transports.Console({
          handleExceptions: true,
          handleRejections: true,
        }),
      ],
      exitOnError: false,
    });

    // Add file transport in production
    if (!isDevelopment) {
      this.winston.add(
        new transports.File({
          filename: 'logs/error.log',
          level: 'error',
          handleExceptions: true,
        })
      );

      this.winston.add(
        new transports.File({
          filename: 'logs/combined.log',
          handleExceptions: true,
        })
      );
    }
  }

  static getInstance(): LoggerService {
    if (!LoggerService.instance) {
      LoggerService.instance = new LoggerService();
    }
    return LoggerService.instance;
  }

  getLogger(component: string): ILogger {
    if (!this.loggers.has(component)) {
      this.loggers.set(component, new ComponentLogger(this.winston, component));
    }
    return this.loggers.get(component)!;
  }

  // Fallback method for cases where Winston fails
  private fallbackLog(level: string, message: string, context?: object): void {
    const timestamp = new Date().toISOString();
    const contextStr = context ? ` ${JSON.stringify(context)}` : '';
  }

  // Safe logging method that won't break application flow
  safeLog(
    component: string,
    level: LogLevel,
    message: string,
    context?: object
  ): void {
    try {
      const logger = this.getLogger(component);
      if (level === 'error') {
        logger.error(message, undefined, context);
      } else {
        (logger as any)[level](message, context);
      }
    } catch (error) {
      this.fallbackLog(level, `[${component}] ${message}`, context);
    }
  }
}

// Export singleton instance
export const loggerService = LoggerService.getInstance();
