/**
 * Fallback Service
 * 
 * Implements intelligent fallback mechanisms based on service health monitoring.
 * Provides automatic failover logic when services become unavailable.
 */

import { healthMonitor, ServiceType, ServiceHealth } from './health-monitor';
import { EventEmitter } from 'events';

export interface FallbackStrategy {
  primary: string;
  fallbacks: string[];
  requiresHealthy: boolean;
  degradationAcceptable: boolean;
}

export interface FallbackResult<T = any> {
  success: boolean;
  data?: T;
  serviceName: string;
  isFallback: boolean;
  confidence: number;
  error?: Error;
  metadata?: Record<string, any>;
}

export interface ServiceOperation<T = any> {
  serviceName: string;
  operation: () => Promise<T>;
  timeout?: number;
  retries?: number;
}

export class FallbackService extends EventEmitter {
  private strategies: Map<string, FallbackStrategy> = new Map();
  private operationHistory: Map<string, { success: number; failure: number; lastUsed: Date }> = new Map();

  constructor() {
    super();
    this.setupDefaultStrategies();
    this.setupHealthMonitorListeners();
  }

  private setupDefaultStrategies(): void {
    // LLM fallback strategy
    this.registerStrategy('llm-analysis', {
      primary: 'gemini-llm',
      fallbacks: ['rule-based-analysis'],
      requiresHealthy: false,
      degradationAcceptable: true,
    });

    // PermaGraph fallback strategy
    this.registerStrategy('knowledge-retrieval', {
      primary: 'permagraph',
      fallbacks: ['local-cache', 'static-templates'],
      requiresHealthy: false,
      degradationAcceptable: true,
    });

    // MCP fallback strategy
    this.registerStrategy('code-generation', {
      primary: 'auto-detect-mcp',
      fallbacks: ['tuetano-mcp', 'kthulu-mcp', 'ferrum-mcp', 'direct-templates'],
      requiresHealthy: false,
      degradationAcceptable: true,
    });

    // Streaming fallback strategy
    this.registerStrategy('real-time-updates', {
      primary: 'streaming-service',
      fallbacks: ['batch-updates', 'polling-updates'],
      requiresHealthy: true,
      degradationAcceptable: false,
    });
  }

  private setupHealthMonitorListeners(): void {
    healthMonitor.on('service-unhealthy', ({ serviceName, health, error }) => {
      console.log(`⚠️ Service ${serviceName} became unhealthy, activating fallbacks`);
      this.emit('service-degraded', { serviceName, health, error });
    });

    healthMonitor.on('service-healthy', ({ serviceName, health }) => {
      console.log(`✅ Service ${serviceName} recovered, fallbacks may be deactivated`);
      this.emit('service-recovered', { serviceName, health });
    });
  }

  registerStrategy(operationType: string, strategy: FallbackStrategy): void {
    this.strategies.set(operationType, strategy);
  }

  async executeWithFallback<T>(
    operationType: string,
    operations: ServiceOperation<T>[],
    options: {
      timeoutMs?: number;
      maxRetries?: number;
      requireSuccess?: boolean;
    } = {}
  ): Promise<FallbackResult<T>> {
    const strategy = this.strategies.get(operationType);
    if (!strategy) {
      throw new Error(`No fallback strategy found for operation type: ${operationType}`);
    }

    const { timeoutMs = 30000, maxRetries = 3, requireSuccess = false } = options;
    const operationMap = new Map(operations.map(op => [op.serviceName, op]));

    // Determine execution order based on health and strategy
    const executionOrder = this.determineExecutionOrder(strategy, operationMap);

    let lastError: Error | null = null;
    let attemptCount = 0;

    for (const serviceName of executionOrder) {
      const operation = operationMap.get(serviceName);
      if (!operation) continue;

      attemptCount++;
      const startTime = Date.now();

      try {
        console.log(`🔄 Attempting ${operationType} with service: ${serviceName}`);
        
        const result = await Promise.race([
          operation.operation(),
          new Promise<never>((_, reject) => 
            setTimeout(() => reject(new Error(`Operation timeout after ${timeoutMs}ms`)), timeoutMs)
          )
        ]);

        const responseTime = Date.now() - startTime;
        const isFallback = serviceName !== strategy.primary;
        const confidence = this.calculateConfidence(serviceName, strategy, isFallback, responseTime);

        // Update operation history
        this.updateOperationHistory(serviceName, true);

        console.log(`✅ ${operationType} succeeded with ${serviceName} (${responseTime}ms, confidence: ${confidence})`);

        this.emit('operation-success', {
          operationType,
          serviceName,
          responseTime,
          isFallback,
          confidence
        });

        return {
          success: true,
          data: result,
          serviceName,
          isFallback,
          confidence,
          metadata: {
            responseTime,
            attemptCount,
            executionOrder: executionOrder.slice(0, attemptCount)
          }
        };

      } catch (error) {
        lastError = error as Error;
        const responseTime = Date.now() - startTime;
        
        console.log(`❌ ${operationType} failed with ${serviceName}: ${lastError.message} (${responseTime}ms)`);
        
        // Update operation history
        this.updateOperationHistory(serviceName, false);

        this.emit('operation-failure', {
          operationType,
          serviceName,
          error: lastError,
          responseTime,
          attemptCount
        });

        // If this is not the last service and we have retries left, continue
        if (attemptCount < executionOrder.length && attemptCount < maxRetries) {
          continue;
        }
      }
    }

    // All services failed
    const isFallback = executionOrder.length > 1;
    
    if (requireSuccess) {
      throw new Error(`All fallback services failed for ${operationType}. Last error: ${lastError?.message}`);
    }

    return {
      success: false,
      serviceName: executionOrder[executionOrder.length - 1] || 'unknown',
      isFallback,
      confidence: 0,
      error: lastError || new Error('Unknown error'),
      metadata: {
        attemptCount,
        executionOrder
      }
    };
  }

  private determineExecutionOrder(strategy: FallbackStrategy, operationMap: Map<string, ServiceOperation>): string[] {
    const order: string[] = [];
    
    // Check primary service first
    if (operationMap.has(strategy.primary)) {
      const isAvailable = healthMonitor.isServiceAvailable(strategy.primary);
      const isHealthy = healthMonitor.isServiceHealthy(strategy.primary);
      
      if (isAvailable && (isHealthy || !strategy.requiresHealthy)) {
        order.push(strategy.primary);
      }
    }

    // Add fallback services based on health and availability
    for (const fallbackService of strategy.fallbacks) {
      if (operationMap.has(fallbackService)) {
        const isAvailable = healthMonitor.isServiceAvailable(fallbackService);
        const isHealthy = healthMonitor.isServiceHealthy(fallbackService);
        
        if (isAvailable && (isHealthy || strategy.degradationAcceptable)) {
          order.push(fallbackService);
        }
      }
    }

    // If no services are available and degradation is acceptable, try all services
    if (order.length === 0 && strategy.degradationAcceptable) {
      if (operationMap.has(strategy.primary)) {
        order.push(strategy.primary);
      }
      for (const fallbackService of strategy.fallbacks) {
        if (operationMap.has(fallbackService)) {
          order.push(fallbackService);
        }
      }
    }

    return order;
  }

  private calculateConfidence(
    serviceName: string,
    strategy: FallbackStrategy,
    isFallback: boolean,
    responseTime: number
  ): number {
    let confidence = 1.0;

    // Reduce confidence for fallback services
    if (isFallback) {
      const fallbackIndex = strategy.fallbacks.indexOf(serviceName);
      confidence *= Math.max(0.1, 1.0 - (fallbackIndex * 0.2));
    }

    // Reduce confidence based on service health
    const health = healthMonitor.getServiceHealth(serviceName);
    if (health) {
      if (health.status === 'degraded') {
        confidence *= 0.7;
      } else if (health.status === 'unhealthy') {
        confidence *= 0.3;
      }
    }

    // Reduce confidence for slow responses
    if (responseTime > 10000) { // 10 seconds
      confidence *= 0.5;
    } else if (responseTime > 5000) { // 5 seconds
      confidence *= 0.8;
    }

    // Factor in historical success rate
    const history = this.operationHistory.get(serviceName);
    if (history) {
      const total = history.success + history.failure;
      if (total > 0) {
        const successRate = history.success / total;
        confidence *= successRate;
      }
    }

    return Math.max(0.1, Math.min(1.0, confidence));
  }

  private updateOperationHistory(serviceName: string, success: boolean): void {
    const history = this.operationHistory.get(serviceName) || {
      success: 0,
      failure: 0,
      lastUsed: new Date()
    };

    if (success) {
      history.success++;
    } else {
      history.failure++;
    }
    history.lastUsed = new Date();

    this.operationHistory.set(serviceName, history);
  }

  // Public API methods
  getStrategy(operationType: string): FallbackStrategy | null {
    return this.strategies.get(operationType) || null;
  }

  getAllStrategies(): Map<string, FallbackStrategy> {
    return new Map(this.strategies);
  }

  getOperationHistory(serviceName: string): { success: number; failure: number; lastUsed: Date } | null {
    return this.operationHistory.get(serviceName) || null;
  }

  getServiceReliability(serviceName: string): number {
    const history = this.operationHistory.get(serviceName);
    if (!history) return 0;

    const total = history.success + history.failure;
    return total > 0 ? history.success / total : 0;
  }

  // Convenience methods for common operations
  async executeLLMOperation<T>(operation: () => Promise<T>): Promise<FallbackResult<T>> {
    return this.executeWithFallback('llm-analysis', [
      { serviceName: 'gemini-llm', operation },
      { serviceName: 'rule-based-analysis', operation: () => this.executeRuleBasedFallback(operation) }
    ]);
  }

  async executeKnowledgeRetrieval<T>(operation: () => Promise<T>): Promise<FallbackResult<T>> {
    return this.executeWithFallback('knowledge-retrieval', [
      { serviceName: 'permagraph', operation },
      { serviceName: 'local-cache', operation: () => this.executeLocalCacheFallback(operation) }
    ]);
  }

  async executeCodeGeneration<T>(operations: ServiceOperation<T>[]): Promise<FallbackResult<T>> {
    return this.executeWithFallback('code-generation', operations);
  }

  // Fallback implementations
  private async executeRuleBasedFallback<T>(originalOperation: () => Promise<T>): Promise<T> {
    // This would implement rule-based semantic analysis as a fallback
    // For now, we'll simulate a degraded response
    console.log('🔄 Executing rule-based fallback for LLM operation');
    
    // In a real implementation, this would perform deterministic analysis
    // based on keywords, patterns, and heuristics
    throw new Error('Rule-based fallback not yet implemented');
  }

  private async executeLocalCacheFallback<T>(originalOperation: () => Promise<T>): Promise<T> {
    // This implements local cache lookup as a fallback for PermaGraph operations
    console.log('🔄 Executing local cache fallback for PermaGraph operation');
    
    try {
      // Import the local pattern cache
      const { localPatternCache } = await import('./local-pattern-cache');
      
      // For now, we'll try to execute the original operation with degraded confidence
      // In a real implementation, this would parse the operation context and
      // search the local cache for relevant patterns
      
      // Simulate cache lookup based on operation context
      const result = await this.simulateCacheLookup<T>();
      
      console.log('✅ Local cache fallback provided results with degraded confidence');
      return result;
      
    } catch (error) {
      console.error('Local cache fallback failed:', error);
      throw new Error(`Local cache fallback failed: ${(error as Error).message}`);
    }
  }

  private async simulateCacheLookup<T>(): Promise<T> {
    // This is a placeholder implementation that would be replaced with
    // actual cache lookup logic based on the operation context
    
    // For 2FA patterns, we might search for authentication patterns
    // For payment services, we might search for service patterns
    // For requirements, we might search for requirement chains
    
    // Return a mock result indicating limited context
    return {
      patterns: [],
      source: 'local-cache',
      confidence: 0.6, // Degraded confidence for cache results
      metadata: {
        limitedContext: true,
        fallbackReason: 'PermaGraph unavailable',
        cacheSource: 'local-pattern-cache'
      }
    } as unknown as T;
  }
}

// Singleton instance
export const fallbackService = new FallbackService();