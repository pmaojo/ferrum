export interface LogContext {
  templateId?: string;
  operation?: string;
  [key: string]: unknown;
}

function log(
  level: 'info' | 'error' | 'warn' | 'debug',
  message: string,
  context: LogContext = {}
) {
  const entry = { level, message, ...context };
  const serialized = JSON.stringify(entry);
  switch (level) {
    case 'error':
      console.error(serialized);
      break;
    case 'warn':
      console.warn(serialized);
      break;
    case 'debug':
      console.debug(serialized);
      break;
    default:
      console.log(serialized);
  }
}

export const logger = {
  info: (message: string, context?: LogContext) =>
    log('info', message, context),
  error: (message: string, context?: LogContext) =>
    log('error', message, context),
  warn: (message: string, context?: LogContext) =>
    log('warn', message, context),
  debug: (message: string, context?: LogContext) =>
    log('debug', message, context),
};
