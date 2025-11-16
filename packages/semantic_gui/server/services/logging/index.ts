// Export all logging functionality
export {
  LoggerService,
  loggerService,
} from './LoggerService';
export type {
  ILogger,
  LogLevel,
  LoggerConfig,
  LogEntry,
} from './LoggerService';
export {
  LoggerFactory,
  expressLogger,
  databaseLogger,
  websocketLogger,
  templateLogger,
  authLogger,
  validationLogger,
} from './LoggerFactory';
export const createLogger = (component: string) =>
  LoggerFactory.createLogger(component);
