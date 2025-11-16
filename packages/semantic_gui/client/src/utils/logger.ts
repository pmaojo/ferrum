export type LogLevel = 'debug' | 'info' | 'warn' | 'error';
type NonErrorLevel = Exclude<LogLevel, 'error'>;

export interface ILogger {
  debug(message: string, context?: object): void;
  info(message: string, context?: object): void;
  warn(message: string, context?: object): void;
  error(message: string, error?: Error, context?: object): void;
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
  private logs: LogEntry[] = [];
  private maxLogs = 1000;

  constructor(private component: string) {}

  private createLogEntry(
    level: LogLevel,
    message: string,
    error?: Error,
    context?: object
  ): LogEntry {
    const entry: LogEntry = {
      timestamp: new Date(),
      level,
      message,
      component: this.component,
      context: context ? { ...context } : undefined,
    };

    if (error) {
      entry.error = {
        name: error.name,
        message: error.message,
        stack: error.stack,
      };
    }

    return entry;
  }

  private addLogEntry(entry: LogEntry): void {
    this.logs.push(entry);
    
    // Keep only the most recent logs
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }
  }

  private shouldLog(level: LogLevel): boolean {
    const isDevelopment = process.env.NODE_ENV === 'development';
    const logLevel = (import.meta.env?.VITE_LOG_LEVEL as LogLevel) || (isDevelopment ? 'debug' : 'info');
    
    const levels: Record<LogLevel, number> = {
      debug: 0,
      info: 1,
      warn: 2,
      error: 3,
    };

    return levels[level] >= levels[logLevel];
  }

  private formatLogMessage(entry: LogEntry): string {
    const timestamp = entry.timestamp.toISOString();
    const contextStr = entry.context ? ` ${JSON.stringify(entry.context)}` : '';
    const errorStr = entry.error ? ` Error: ${entry.error.message}` : '';
    return `${timestamp} [${entry.component}] ${entry.message}${contextStr}${errorStr}`;
  }

  debug(message: string, context?: object): void {
    const entry = this.createLogEntry('debug', message, undefined, context);
    this.addLogEntry(entry);

    if (this.shouldLog('debug')) {
      console.debug(this.formatLogMessage(entry));
    }
  }

  info(message: string, context?: object): void {
    const entry = this.createLogEntry('info', message, undefined, context);
    this.addLogEntry(entry);

    if (this.shouldLog('info')) {
      console.info(this.formatLogMessage(entry));
    }
  }

  warn(message: string, context?: object): void {
    const entry = this.createLogEntry('warn', message, undefined, context);
    this.addLogEntry(entry);

    if (this.shouldLog('warn')) {
      console.warn(this.formatLogMessage(entry));
    }
  }

  error(message: string, error?: Error, context?: object): void {
    const entry = this.createLogEntry('error', message, error, context);
    this.addLogEntry(entry);

    if (this.shouldLog('error')) {
      console.error(this.formatLogMessage(entry));
      if (error?.stack) {
        console.error(error.stack);
      }
    }
  }

  getLogs(): LogEntry[] {
    return [...this.logs];
  }

  clearLogs(): void {
    this.logs = [];
  }
}

export class ClientLoggerService {
  private static instance: ClientLoggerService;
  private loggers: Map<string, ComponentLogger> = new Map();

  private constructor() {}

  static getInstance(): ClientLoggerService {
    if (!ClientLoggerService.instance) {
      ClientLoggerService.instance = new ClientLoggerService();
    }
    return ClientLoggerService.instance;
  }

  getLogger(component: string): ILogger {
    if (!this.loggers.has(component)) {
      this.loggers.set(component, new ComponentLogger(component));
    }
    return this.loggers.get(component)!;
  }

  // Safe logging method that won't break application flow
  safeLog(
    component: string,
    level: LogLevel,
    message: string,
    context?: object,
    error?: Error
  ): void {
    try {
      const logger = this.getLogger(component);
      if (level === 'error') {
        logger.error(message, error, context);
      } else {
        const method = logger[level as NonErrorLevel].bind(logger);
        method(message, context);
      }
    } catch (logError) {
      // Fallback to console if logger fails
      const timestamp = new Date().toISOString();
      const contextStr = context ? ` ${JSON.stringify(context)}` : '';
      console.error(`${timestamp} [${component}] LOGGER_ERROR: ${message}${contextStr}`, logError);
    }
  }

  // Get all logs from all components
  getAllLogs(): LogEntry[] {
    const allLogs: LogEntry[] = [];
    for (const logger of this.loggers.values()) {
      allLogs.push(...logger.getLogs());
    }
    return allLogs.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }

  // Clear all logs
  clearAllLogs(): void {
    for (const logger of this.loggers.values()) {
      logger.clearLogs();
    }
  }
}

// Export singleton instance
export const clientLogger = ClientLoggerService.getInstance();

// Convenience function for quick logging
export const createLogger = (component: string): ILogger => {
  return clientLogger.getLogger(component);
};