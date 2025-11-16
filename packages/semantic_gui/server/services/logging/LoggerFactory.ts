import type { ILogger } from './LoggerService';
import { loggerService } from './LoggerService';

/**
 * Logger factory that provides component-specific loggers
 * This factory ensures consistent logger creation across the application
 */
export class LoggerFactory {
  /**
   * Creates a logger for a specific component
   * @param component - The component name (e.g., 'express', 'database', 'auth')
   * @returns A logger instance configured for the component
   */
  static createLogger(component: string): ILogger {
    return loggerService.getLogger(component);
  }

  /**
   * Creates a logger for Express routes
   * @param routeName - The route name (e.g., 'api', 'auth', 'templates')
   * @returns A logger instance configured for the route
   */
  static createRouteLogger(routeName: string): ILogger {
    return loggerService.getLogger(`route:${routeName}`);
  }

  /**
   * Creates a logger for services
   * @param serviceName - The service name (e.g., 'template', 'database', 'websocket')
   * @returns A logger instance configured for the service
   */
  static createServiceLogger(serviceName: string): ILogger {
    return loggerService.getLogger(`service:${serviceName}`);
  }

  /**
   * Creates a logger for middleware
   * @param middlewareName - The middleware name (e.g., 'auth', 'cors', 'validation')
   * @returns A logger instance configured for the middleware
   */
  static createMiddlewareLogger(middlewareName: string): ILogger {
    return loggerService.getLogger(`middleware:${middlewareName}`);
  }

  /**
   * Creates a logger for utilities
   * @param utilityName - The utility name (e.g., 'ast-parser', 'file-watcher')
   * @returns A logger instance configured for the utility
   */
  static createUtilityLogger(utilityName: string): ILogger {
    return loggerService.getLogger(`util:${utilityName}`);
  }

  /**
   * Creates a logger for client-side components (when logging from server-side rendering)
   * @param componentName - The component name
   * @returns A logger instance configured for the client component
   */
  static createClientLogger(componentName: string): ILogger {
    return loggerService.getLogger(`client:${componentName}`);
  }
}

// Convenience exports for common loggers
export const expressLogger = LoggerFactory.createLogger('express');
export const databaseLogger = LoggerFactory.createServiceLogger('database');
export const websocketLogger = LoggerFactory.createServiceLogger('websocket');
export const templateLogger = LoggerFactory.createServiceLogger('template');
export const authLogger = LoggerFactory.createMiddlewareLogger('auth');
export const validationLogger =
  LoggerFactory.createMiddlewareLogger('validation');
