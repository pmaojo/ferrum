/**
 * Service Manager for Lazy Loading Optional Services
 * Implements graceful degradation when services are unavailable
 */

export interface ServiceConfig {
  name: string;
  url: string;
  healthEndpoint: string;
  timeout: number;
  retries: number;
  optional: boolean;
  fallbackEnabled: boolean;
}

export interface ServiceStatus {
  name: string;
  available: boolean;
  lastCheck: Date;
  error?: string;
  responseTime?: number;
}

export class ServiceManager {
  private services: Map<string, ServiceConfig> = new Map();
  private serviceStatus: Map<string, ServiceStatus> = new Map();
  private healthCheckInterval: NodeJS.Timeout | null = null;
  private readonly HEALTH_CHECK_INTERVAL = 30000; // 30 seconds

  constructor() {
    this.initializeServices();
    this.startHealthChecks();
  }

  private initializeServices() {
    const services: ServiceConfig[] = [
      {
        name: 'permagraph',
        url: process.env.PERMAGRAPH_API_URL || 'http://permagraph:8080',
        healthEndpoint: '/metrics',
        timeout: 5000,
        retries: 3,
        optional: true,
        fallbackEnabled: true,
      },
      {
        name: 'ferrum-ai',
        url: process.env.FERRUM_AI_URL || 'http://ferrum-ai:8001',
        healthEndpoint: '/healthz',
        timeout: 5000,
        retries: 2,
        optional: true,
        fallbackEnabled: true,
      },
      {
        name: 'mcp-server',
        url: process.env.MCP_SERVER_URL || 'http://mcp-server:8001',
        healthEndpoint: '/health',
        timeout: 3000,
        retries: 2,
        optional: true,
        fallbackEnabled: true,
      },
      {
        name: 'redis',
        url: process.env.REDIS_URL || 'redis://redis:6379',
        healthEndpoint: '/ping',
        timeout: 2000,
        retries: 1,
        optional: true,
        fallbackEnabled: true,
      },
    ];

    services.forEach(service => {
      this.services.set(service.name, service);
      this.serviceStatus.set(service.name, {
        name: service.name,
        available: false,
        lastCheck: new Date(),
      });
    });
  }

  private startHealthChecks() {
    // Initial health check
    this.checkAllServices();

    // Periodic health checks
    this.healthCheckInterval = setInterval(() => {
      this.checkAllServices();
    }, this.HEALTH_CHECK_INTERVAL);
  }

  private async checkAllServices() {
    const promises = Array.from(this.services.values()).map(service =>
      this.checkServiceHealth(service)
    );

    await Promise.allSettled(promises);
  }

  private async checkServiceHealth(service: ServiceConfig): Promise<void> {
    const startTime = Date.now();

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), service.timeout);

      const response = await fetch(`${service.url}${service.healthEndpoint}`, {
        signal: controller.signal,
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      clearTimeout(timeoutId);
      const responseTime = Date.now() - startTime;

      const isHealthy = response.ok || response.status < 500;

      this.serviceStatus.set(service.name, {
        name: service.name,
        available: isHealthy,
        lastCheck: new Date(),
        responseTime,
        error: isHealthy ? undefined : `HTTP ${response.status}`,
      });
    } catch (error) {
      const responseTime = Date.now() - startTime;

      this.serviceStatus.set(service.name, {
        name: service.name,
        available: false,
        lastCheck: new Date(),
        responseTime,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  }

  public async getService<T = any>(serviceName: string): Promise<T | null> {
    const service = this.services.get(serviceName);
    const status = this.serviceStatus.get(serviceName);

    if (!service || !status) {
      throw new Error(`Service ${serviceName} not configured`);
    }

    // If service is not available and not optional, throw error
    if (!status.available && !service.optional) {
      throw new Error(`Required service ${serviceName} is not available`);
    }

    // If service is not available but optional, return null for graceful degradation
    if (!status.available && service.optional) {
      console.warn(
        `Optional service ${serviceName} is not available, using fallback`
      );
      return null;
    }

    // Return service proxy for lazy loading
    return this.createServiceProxy<T>(service);
  }

  private createServiceProxy<T>(service: ServiceConfig): T {
    return new Proxy({} as T, {
      get: (target, prop) => {
        return async (...args: any[]) => {
          const status = this.serviceStatus.get(service.name);

          if (!status?.available) {
            if (service.fallbackEnabled) {
              console.warn(
                `Service ${service.name} unavailable, using fallback for ${String(prop)}`
              );
              return this.getFallbackResponse(service.name, String(prop));
            }
            throw new Error(`Service ${service.name} is not available`);
          }

          // Make actual service call
          try {
            const response = await fetch(`${service.url}/${String(prop)}`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(args),
            });

            if (!response.ok) {
              throw new Error(`Service call failed: ${response.status}`);
            }

            return await response.json();
          } catch (error) {
            if (service.fallbackEnabled) {
              console.warn(
                `Service call failed for ${service.name}.${String(prop)}, using fallback`
              );
              return this.getFallbackResponse(service.name, String(prop));
            }
            throw error;
          }
        };
      },
    });
  }

  private getFallbackResponse(serviceName: string, method: string): any {
    // Define fallback responses for different services and methods
    const fallbacks: Record<string, Record<string, any>> = {
      permagraph: {
        store: {
          success: false,
          message: 'PermaGraph unavailable - data not persisted',
        },
        retrieve: {
          data: null,
          message: 'PermaGraph unavailable - using local data',
        },
        search: {
          results: [],
          message: 'PermaGraph unavailable - search disabled',
        },
      },
      'ferrum-ai': {
        generate: {
          code: '// AI service unavailable',
          message: 'Manual implementation required',
        },
        analyze: { analysis: null, message: 'AI analysis unavailable' },
        suggest: { suggestions: [], message: 'AI suggestions unavailable' },
      },
      'mcp-server': {
        execute: {
          success: false,
          message: 'MCP server unavailable - manual execution required',
        },
        'list-tools': { tools: [], message: 'MCP tools unavailable' },
      },
      redis: {
        get: null,
        set: {
          success: false,
          message: 'Cache unavailable - using memory storage',
        },
        del: { success: false, message: 'Cache unavailable' },
      },
    };

    return (
      fallbacks[serviceName]?.[method] || {
        success: false,
        message: `Service ${serviceName} unavailable`,
      }
    );
  }

  public getServiceStatus(
    serviceName?: string
  ): ServiceStatus | ServiceStatus[] {
    if (serviceName) {
      const status = this.serviceStatus.get(serviceName);
      if (!status) {
        throw new Error(`Service ${serviceName} not found`);
      }
      return status;
    }

    return Array.from(this.serviceStatus.values());
  }

  public getAvailableServices(): string[] {
    return Array.from(this.serviceStatus.entries())
      .filter(([_, status]) => status.available)
      .map(([name, _]) => name);
  }

  public async waitForService(
    serviceName: string,
    timeout: number = 30000
  ): Promise<boolean> {
    const service = this.services.get(serviceName);
    if (!service) {
      throw new Error(`Service ${serviceName} not configured`);
    }

    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const status = this.serviceStatus.get(serviceName);
      if (status?.available) {
        return true;
      }

      // Check service health immediately
      await this.checkServiceHealth(service);

      // Wait before next check
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    return false;
  }

  public destroy() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }
}

// Singleton instance
export const serviceManager = new ServiceManager();

// Graceful shutdown
process.on('SIGTERM', () => {
  serviceManager.destroy();
});

process.on('SIGINT', () => {
  serviceManager.destroy();
});
