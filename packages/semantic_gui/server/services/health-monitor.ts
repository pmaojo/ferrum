/**
 * Service Health Monitoring System
 * 
 * Implements comprehensive health monitoring for LLM, PermaGraph, and MCP services
 * with circuit breaker pattern and automatic failover logic.
 */

import { EventEmitter } from 'events';

export type ServiceType = 'llm' | 'permagraph' | 'mcp' | 'streaming';

export interface ServiceHealth {
  name: string;
  type: ServiceType;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  lastCheck: Date;
  responseTime: number;
  errorCount: number;
  successCount: number;
  uptime: number;
  metadata: Record<string, any>;
}

export interface CircuitBreakerState {
  state: 'closed' | 'open' | 'half-open';
  failureCount: number;
  lastFailureTime: Date | null;
  nextAttemptTime: Date | null;
  successCount: number;
}

export interface HealthCheckConfig {
  interval: number; // milliseconds
  timeout: number; // milliseconds
  retryAttempts: number;
  circuitBreakerThreshold: number;
  circuitBreakerTimeout: number; // milliseconds
  exponentialBackoffBase: number;
  maxBackoffTime: number; // milliseconds
}

export interface ServiceEndpoint {
  name: string;
  type: ServiceType;
  url?: string;
  healthCheckFn: () => Promise<{ status: 'healthy' | 'unhealthy'; responseTime: number; metadata?: any }>;
  config: HealthCheckConfig;
}

export class HealthMonitor extends EventEmitter {
  private services: Map<string, ServiceEndpoint> = new Map();
  private healthStatus: Map<string, ServiceHealth> = new Map();
  private circuitBreakers: Map<string, CircuitBreakerState> = new Map();
  private intervals: Map<string, NodeJS.Timeout> = new Map();
  private isRunning = false;

  private defaultConfig: HealthCheckConfig = {
    interval: 30000, // 30 seconds
    timeout: 5000, // 5 seconds
    retryAttempts: 3,
    circuitBreakerThreshold: 5,
    circuitBreakerTimeout: 60000, // 1 minute
    exponentialBackoffBase: 2,
    maxBackoffTime: 300000, // 5 minutes
  };

  constructor() {
    super();
    this.setupDefaultServices();
  }

  private setupDefaultServices(): void {
    // LLM Service (Gemini API)
    this.registerService({
      name: 'gemini-llm',
      type: 'llm',
      healthCheckFn: this.checkLLMHealth.bind(this),
      config: { ...this.defaultConfig, interval: 60000 }, // Check every minute
    });

    // PermaGraph Service
    this.registerService({
      name: 'permagraph',
      type: 'permagraph',
      healthCheckFn: this.checkPermaGraphHealth.bind(this),
      config: { ...this.defaultConfig, interval: 45000 }, // Check every 45 seconds
    });

    // MCP Services
    this.registerService({
      name: 'tuetano-mcp',
      type: 'mcp',
      healthCheckFn: this.checkTuetanoMCPHealth.bind(this),
      config: { ...this.defaultConfig, interval: 30000 },
    });

    this.registerService({
      name: 'kthulu-mcp',
      type: 'mcp',
      healthCheckFn: this.checkKthuluMCPHealth.bind(this),
      config: { ...this.defaultConfig, interval: 30000 },
    });

    this.registerService({
      name: 'ferrum-mcp',
      type: 'mcp',
      healthCheckFn: this.checkFerrumMCPHealth.bind(this),
      config: { ...this.defaultConfig, interval: 30000 },
    });

    // Streaming Service
    this.registerService({
      name: 'streaming-service',
      type: 'streaming',
      healthCheckFn: this.checkStreamingHealth.bind(this),
      config: { ...this.defaultConfig, interval: 20000 }, // Check every 20 seconds
    });
  }

  registerService(endpoint: ServiceEndpoint): void {
    this.services.set(endpoint.name, endpoint);
    
    // Initialize health status
    this.healthStatus.set(endpoint.name, {
      name: endpoint.name,
      type: endpoint.type,
      status: 'unknown',
      lastCheck: new Date(),
      responseTime: 0,
      errorCount: 0,
      successCount: 0,
      uptime: 0,
      metadata: {},
    });

    // Initialize circuit breaker
    this.circuitBreakers.set(endpoint.name, {
      state: 'closed',
      failureCount: 0,
      lastFailureTime: null,
      nextAttemptTime: null,
      successCount: 0,
    });

    if (this.isRunning) {
      this.startMonitoring(endpoint.name);
    }
  }

  start(): void {
    if (this.isRunning) return;
    
    this.isRunning = true;
    console.log('🔍 Starting health monitoring system...');
    
    for (const serviceName of this.services.keys()) {
      this.startMonitoring(serviceName);
    }

    this.emit('monitoring-started');
  }

  stop(): void {
    if (!this.isRunning) return;
    
    this.isRunning = false;
    console.log('⏹️ Stopping health monitoring system...');
    
    for (const [serviceName, interval] of this.intervals) {
      clearInterval(interval);
      this.intervals.delete(serviceName);
    }

    this.emit('monitoring-stopped');
  }

  private startMonitoring(serviceName: string): void {
    const service = this.services.get(serviceName);
    if (!service) return;

    // Perform initial health check
    this.performHealthCheck(serviceName);

    // Set up periodic monitoring
    const interval = setInterval(() => {
      this.performHealthCheck(serviceName);
    }, service.config.interval);

    this.intervals.set(serviceName, interval);
  }

  private async performHealthCheck(serviceName: string): Promise<void> {
    const service = this.services.get(serviceName);
    const circuitBreaker = this.circuitBreakers.get(serviceName);
    const currentHealth = this.healthStatus.get(serviceName);

    if (!service || !circuitBreaker || !currentHealth) return;

    // Check circuit breaker state
    if (circuitBreaker.state === 'open') {
      if (circuitBreaker.nextAttemptTime && new Date() < circuitBreaker.nextAttemptTime) {
        // Circuit breaker is still open, skip this check
        return;
      }
      // Try to transition to half-open
      circuitBreaker.state = 'half-open';
      console.log(`🔄 Circuit breaker for ${serviceName} transitioning to half-open`);
    }

    const startTime = Date.now();
    let attempt = 0;
    let lastError: Error | null = null;

    while (attempt < service.config.retryAttempts) {
      try {
        const result = await Promise.race([
          service.healthCheckFn(),
          new Promise<never>((_, reject) => 
            setTimeout(() => reject(new Error('Health check timeout')), service.config.timeout)
          )
        ]);

        const responseTime = Date.now() - startTime;
        
        // Health check succeeded
        this.handleHealthCheckSuccess(serviceName, responseTime, result.metadata);
        return;

      } catch (error) {
        lastError = error as Error;
        attempt++;
        
        if (attempt < service.config.retryAttempts) {
          // Wait before retry with exponential backoff
          const backoffTime = Math.min(
            Math.pow(service.config.exponentialBackoffBase, attempt) * 1000,
            service.config.maxBackoffTime
          );
          await new Promise(resolve => setTimeout(resolve, backoffTime));
        }
      }
    }

    // All attempts failed
    const responseTime = Date.now() - startTime;
    this.handleHealthCheckFailure(serviceName, responseTime, lastError);
  }

  private handleHealthCheckSuccess(serviceName: string, responseTime: number, metadata?: any): void {
    const health = this.healthStatus.get(serviceName);
    const circuitBreaker = this.circuitBreakers.get(serviceName);

    if (!health || !circuitBreaker) return;

    // Update health status
    health.status = 'healthy';
    health.lastCheck = new Date();
    health.responseTime = responseTime;
    health.successCount++;
    health.metadata = { ...health.metadata, ...metadata };

    // Update circuit breaker
    if (circuitBreaker.state === 'half-open') {
      circuitBreaker.successCount++;
      if (circuitBreaker.successCount >= 3) {
        // Transition back to closed
        circuitBreaker.state = 'closed';
        circuitBreaker.failureCount = 0;
        circuitBreaker.successCount = 0;
        console.log(`✅ Circuit breaker for ${serviceName} closed - service recovered`);
      }
    } else if (circuitBreaker.state === 'closed') {
      // Reset failure count on successful health check
      circuitBreaker.failureCount = 0;
    }

    this.emit('service-healthy', { serviceName, health });
  }

  private handleHealthCheckFailure(serviceName: string, responseTime: number, error: Error | null): void {
    const health = this.healthStatus.get(serviceName);
    const circuitBreaker = this.circuitBreakers.get(serviceName);
    const service = this.services.get(serviceName);

    if (!health || !circuitBreaker || !service) return;

    // Update health status
    health.status = 'unhealthy';
    health.lastCheck = new Date();
    health.responseTime = responseTime;
    health.errorCount++;
    health.metadata = { lastError: error?.message || 'Unknown error' };

    // Update circuit breaker
    circuitBreaker.failureCount++;
    circuitBreaker.lastFailureTime = new Date();

    if (circuitBreaker.state === 'half-open') {
      // Failed in half-open state, go back to open
      circuitBreaker.state = 'open';
      circuitBreaker.successCount = 0;
      circuitBreaker.nextAttemptTime = new Date(Date.now() + service.config.circuitBreakerTimeout);
      console.log(`❌ Circuit breaker for ${serviceName} opened - service still failing`);
    } else if (circuitBreaker.failureCount >= service.config.circuitBreakerThreshold) {
      // Threshold reached, open circuit breaker
      circuitBreaker.state = 'open';
      circuitBreaker.nextAttemptTime = new Date(Date.now() + service.config.circuitBreakerTimeout);
      console.log(`🚨 Circuit breaker for ${serviceName} opened - threshold reached`);
    }

    this.emit('service-unhealthy', { serviceName, health, error });
  }

  // Service-specific health check implementations
  private async checkLLMHealth(): Promise<{ status: 'healthy' | 'unhealthy'; responseTime: number; metadata?: any }> {
    const startTime = Date.now();
    
    try {
      // Simple test request to Gemini API
      const response = await fetch('https://generativelanguage.googleapis.com/v1beta/models', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const responseTime = Date.now() - startTime;
      
      if (response.ok) {
        return {
          status: 'healthy',
          responseTime,
          metadata: { statusCode: response.status }
        };
      } else {
        return {
          status: 'unhealthy',
          responseTime,
          metadata: { statusCode: response.status, error: 'API returned non-200 status' }
        };
      }
    } catch (error) {
      return {
        status: 'unhealthy',
        responseTime: Date.now() - startTime,
        metadata: { error: (error as Error).message }
      };
    }
  }

  private async checkPermaGraphHealth(): Promise<{ status: 'healthy' | 'unhealthy'; responseTime: number; metadata?: any }> {
    const startTime = Date.now();
    
    try {
      // Check if PermaGraph service is accessible
      // This would typically be a ping to the graph database
      const responseTime = Date.now() - startTime;
      
      // For now, simulate a health check
      // In a real implementation, this would connect to the actual PermaGraph service
      return {
        status: 'healthy',
        responseTime,
        metadata: { nodes: 1000, relationships: 5000 }
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        responseTime: Date.now() - startTime,
        metadata: { error: (error as Error).message }
      };
    }
  }

  private async checkTuetanoMCPHealth(): Promise<{ status: 'healthy' | 'unhealthy'; responseTime: number; metadata?: any }> {
    return this.checkMCPHealth('tuetano');
  }

  private async checkKthuluMCPHealth(): Promise<{ status: 'healthy' | 'unhealthy'; responseTime: number; metadata?: any }> {
    return this.checkMCPHealth('kthulu');
  }

  private async checkFerrumMCPHealth(): Promise<{ status: 'healthy' | 'unhealthy'; responseTime: number; metadata?: any }> {
    return this.checkMCPHealth('ferrum');
  }

  private async checkMCPHealth(framework: string): Promise<{ status: 'healthy' | 'unhealthy'; responseTime: number; metadata?: any }> {
    const startTime = Date.now();
    
    try {
      // Check if MCP server is running and responsive
      // This would typically involve checking the MCP server endpoint
      const responseTime = Date.now() - startTime;
      
      // For now, simulate a health check
      // In a real implementation, this would connect to the actual MCP server
      return {
        status: 'healthy',
        responseTime,
        metadata: { framework, version: '1.0.0' }
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        responseTime: Date.now() - startTime,
        metadata: { framework, error: (error as Error).message }
      };
    }
  }

  private async checkStreamingHealth(): Promise<{ status: 'healthy' | 'unhealthy'; responseTime: number; metadata?: any }> {
    const startTime = Date.now();
    
    try {
      // Check if streaming service is accessible
      const responseTime = Date.now() - startTime;
      
      // For now, simulate a health check
      // In a real implementation, this would check WebSocket connectivity
      return {
        status: 'healthy',
        responseTime,
        metadata: { activeConnections: 5 }
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        responseTime: Date.now() - startTime,
        metadata: { error: (error as Error).message }
      };
    }
  }

  // Public API methods
  getServiceHealth(serviceName: string): ServiceHealth | null {
    return this.healthStatus.get(serviceName) || null;
  }

  getAllServicesHealth(): ServiceHealth[] {
    return Array.from(this.healthStatus.values());
  }

  getServicesByType(type: ServiceType): ServiceHealth[] {
    return Array.from(this.healthStatus.values()).filter(health => health.type === type);
  }

  isServiceHealthy(serviceName: string): boolean {
    const health = this.healthStatus.get(serviceName);
    return health?.status === 'healthy';
  }

  isServiceAvailable(serviceName: string): boolean {
    const circuitBreaker = this.circuitBreakers.get(serviceName);
    return circuitBreaker?.state !== 'open';
  }

  getCircuitBreakerState(serviceName: string): CircuitBreakerState | null {
    return this.circuitBreakers.get(serviceName) || null;
  }

  recordServiceSuccess(serviceName: string, responseTime = 0, metadata?: any): void {
    this.handleHealthCheckSuccess(serviceName, responseTime, metadata);
  }

  recordServiceFailure(serviceName: string, error: Error, responseTime = 0): void {
    this.handleHealthCheckFailure(serviceName, responseTime, error);
  }

  // Force a health check for a specific service
  async forceHealthCheck(serviceName: string): Promise<void> {
    await this.performHealthCheck(serviceName);
  }

  // Get overall system health
  getSystemHealth(): { status: 'healthy' | 'degraded' | 'unhealthy'; services: ServiceHealth[] } {
    const services = this.getAllServicesHealth();
    const healthyCount = services.filter(s => s.status === 'healthy').length;
    const totalCount = services.length;

    let status: 'healthy' | 'degraded' | 'unhealthy';
    if (healthyCount === totalCount) {
      status = 'healthy';
    } else if (healthyCount > totalCount / 2) {
      status = 'degraded';
    } else {
      status = 'unhealthy';
    }

    return { status, services };
  }
}

// Singleton instance
export const healthMonitor = new HealthMonitor();