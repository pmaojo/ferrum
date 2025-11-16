import { LoggerService, LoggerFactory } from '../index';

describe('LoggerService', () => {
  let loggerService: LoggerService;

  beforeEach(() => {
    loggerService = LoggerService.getInstance();
  });

  it('should create a singleton instance', () => {
    const instance1 = LoggerService.getInstance();
    const instance2 = LoggerService.getInstance();
    expect(instance1).toBe(instance2);
  });

  it('should create component-specific loggers', () => {
    const logger1 = loggerService.getLogger('test-component');
    const logger2 = loggerService.getLogger('test-component');
    const logger3 = loggerService.getLogger('different-component');

    expect(logger1).toBe(logger2); // Same component should return same logger
    expect(logger1).not.toBe(logger3); // Different components should have different loggers
  });

  it('should provide all required logging methods', () => {
    const logger = loggerService.getLogger('test');

    expect(typeof logger.debug).toBe('function');
    expect(typeof logger.info).toBe('function');
    expect(typeof logger.warn).toBe('function');
    expect(typeof logger.error).toBe('function');
  });

  it('should handle safe logging without throwing errors', () => {
    expect(() => {
      loggerService.safeLog('test', 'info', 'Test message', { key: 'value' });
    }).not.toThrow();
  });
});

describe('LoggerFactory', () => {
  it('should create loggers with proper component names', () => {
    const routeLogger = LoggerFactory.createRouteLogger('api');
    const serviceLogger = LoggerFactory.createServiceLogger('database');
    const middlewareLogger = LoggerFactory.createMiddlewareLogger('auth');
    const utilityLogger = LoggerFactory.createUtilityLogger('parser');
    const clientLogger = LoggerFactory.createClientLogger('dashboard');

    // These should not throw and should return logger instances
    expect(routeLogger).toBeDefined();
    expect(serviceLogger).toBeDefined();
    expect(middlewareLogger).toBeDefined();
    expect(utilityLogger).toBeDefined();
    expect(clientLogger).toBeDefined();
  });

  it('should provide convenience logger exports', () => {
    const {
      expressLogger,
      databaseLogger,
      websocketLogger,
      templateLogger,
      authLogger,
      validationLogger,
    } = require('../LoggerFactory');

    expect(expressLogger).toBeDefined();
    expect(databaseLogger).toBeDefined();
    expect(websocketLogger).toBeDefined();
    expect(templateLogger).toBeDefined();
    expect(authLogger).toBeDefined();
    expect(validationLogger).toBeDefined();
  });
});
