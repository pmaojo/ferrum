/**
 * Comprehensive Metrics Collection System
 * 
 * Implements token usage tracking, latency measurement, cost calculation,
 * and resource utilization monitoring for the hybrid intelligence system.
 */

import { EventEmitter } from 'events';
import { performance } from 'perf_hooks';
import { promises as fs } from 'fs';
import { join } from 'path';

export interface BenchmarkMetrics {
  id: string;
  timestamp: Date;
  operation: string;
  phase: 'intent-classification' | 'domain-detection' | 'security-assessment' | 'knowledge-retrieval' | 'recommendation-generation' | 'complete';
  
  // Token usage metrics
  tokenUsage: {
    inputTokens: number;
    outputTokens: number;
    totalTokens: number;
    model: string;
    provider: 'gemini' | 'openai' | 'anthropic' | 'local' | 'rule-based';
  };
  
  // Performance metrics
  performance: {
    startTime: number;
    endTime: number;
    duration: number; // milliseconds
    cpuUsage: number; // percentage
    memoryUsage: number; // bytes
    networkLatency?: number; // milliseconds
  };
  
  // Cost metrics
  cost: {
    inputCost: number; // USD
    outputCost: number; // USD
    totalCost: number; // USD
    currency: 'USD';
  };
  
  // Quality metrics
  quality: {
    confidence: number; // 0-1
    accuracy?: number; // 0-1 (if ground truth available)
    fallbackUsed: boolean;
    servicePath: string[];
  };
  
  // Context metrics
  context: {
    requestSize: number; // bytes
    responseSize: number; // bytes
    cacheHit: boolean;
    retryCount: number;
    errorCount: number;
  };
  
  metadata: Record<string, any>;
}

export interface AggregatedMetrics {
  timeRange: {
    start: Date;
    end: Date;
    duration: number; // milliseconds
  };
  
  totalOperations: number;
  successfulOperations: number;
  failedOperations: number;
  successRate: number;
  
  tokenUsage: {
    totalInputTokens: number;
    totalOutputTokens: number;
    totalTokens: number;
    averageTokensPerOperation: number;
    tokensByProvider: Record<string, number>;
  };
  
  performance: {
    averageDuration: number;
    medianDuration: number;
    p95Duration: number;
    p99Duration: number;
    averageCpuUsage: number;
    averageMemoryUsage: number;
    peakMemoryUsage: number;
  };
  
  cost: {
    totalCost: number;
    averageCostPerOperation: number;
    costByProvider: Record<string, number>;
    costByPhase: Record<string, number>;
  };
  
  quality: {
    averageConfidence: number;
    fallbackUsageRate: number;
    cacheHitRate: number;
    averageRetryCount: number;
  };
}

export interface MetricsConfig {
  enableCollection: boolean;
  enablePersistence: boolean;
  persistenceInterval: number; // milliseconds
  metricsDirectory: string;
  maxMetricsInMemory: number;
  enableRealTimeStreaming: boolean;
  costRates: {
    [provider: string]: {
      inputTokenCost: number; // cost per 1K tokens
      outputTokenCost: number; // cost per 1K tokens
    };
  };
}

export class MetricsCollector extends EventEmitter {
  private metrics: Map<string, BenchmarkMetrics> = new Map();
  private activeOperations: Map<string, Partial<BenchmarkMetrics>> = new Map();
  private config: MetricsConfig;
  private persistenceTimer: NodeJS.Timeout | null = null;

  constructor(config: Partial<MetricsConfig> = {}) {
    super();
    
    this.config = {
      enableCollection: true,
      enablePersistence: true,
      persistenceInterval: 60000, // 1 minute
      metricsDirectory: join(process.cwd(), '.metrics'),
      maxMetricsInMemory: 10000,
      enableRealTimeStreaming: true,
      costRates: {
        'gemini': {
          inputTokenCost: 0.00015, // $0.15 per 1K input tokens
          outputTokenCost: 0.0006, // $0.60 per 1K output tokens
        },
        'openai': {
          inputTokenCost: 0.0015, // $1.50 per 1K input tokens
          outputTokenCost: 0.002, // $2.00 per 1K output tokens
        },
        'anthropic': {
          inputTokenCost: 0.0008, // $0.80 per 1K input tokens
          outputTokenCost: 0.0024, // $2.40 per 1K output tokens
        },
        'local': {
          inputTokenCost: 0, // Free for local models
          outputTokenCost: 0,
        },
        'rule-based': {
          inputTokenCost: 0, // Free for rule-based analysis
          outputTokenCost: 0,
        }
      },
      ...config
    };

    this.initialize();
  }

  private async initialize(): Promise<void> {
    if (!this.config.enableCollection) return;

    try {
      // Create metrics directory
      if (this.config.enablePersistence) {
        await fs.mkdir(this.config.metricsDirectory, { recursive: true });
        await this.loadPersistedMetrics();
      }

      // Start persistence timer
      if (this.config.enablePersistence) {
        this.startPersistenceTimer();
      }

      console.log('📊 Metrics collection system initialized');
      this.emit('metrics-initialized');

    } catch (error) {
      console.error('Failed to initialize metrics collector:', error);
      this.emit('metrics-error', { error, operation: 'initialize' });
    }
  }

  private async loadPersistedMetrics(): Promise<void> {
    try {
      const metricsFile = join(this.config.metricsDirectory, 'metrics.json');
      const data = await fs.readFile(metricsFile, 'utf-8');
      const persistedMetrics: Array<[string, BenchmarkMetrics]> = JSON.parse(data);
      
      for (const [id, metric] of persistedMetrics) {
        // Restore Date objects
        metric.timestamp = new Date(metric.timestamp);
        this.metrics.set(id, metric);
      }
      
      console.log(`📂 Loaded ${this.metrics.size} persisted metrics`);
      
    } catch (error) {
      // No persisted metrics file, start fresh
      console.log('🆕 Starting with fresh metrics collection');
    }
  }

  private startPersistenceTimer(): void {
    if (this.persistenceTimer) {
      clearInterval(this.persistenceTimer);
    }

    this.persistenceTimer = setInterval(() => {
      this.persistMetrics();
    }, this.config.persistenceInterval);
  }

  private async persistMetrics(): Promise<void> {
    if (!this.config.enablePersistence) return;

    try {
      const metricsFile = join(this.config.metricsDirectory, 'metrics.json');
      const metricsArray = Array.from(this.metrics.entries());
      await fs.writeFile(metricsFile, JSON.stringify(metricsArray, null, 2));
      
      this.emit('metrics-persisted', { count: metricsArray.length });
      
    } catch (error) {
      console.error('Failed to persist metrics:', error);
      this.emit('metrics-error', { error, operation: 'persist' });
    }
  }

  /**
   * Start tracking a new operation
   */
  startOperation(
    operationId: string,
    operation: string,
    phase: BenchmarkMetrics['phase'],
    metadata: Record<string, any> = {}
  ): void {
    if (!this.config.enableCollection) return;

    const startTime = performance.now();
    const memoryUsage = process.memoryUsage();

    const operationMetrics: Partial<BenchmarkMetrics> = {
      id: operationId,
      timestamp: new Date(),
      operation,
      phase,
      performance: {
        startTime,
        endTime: 0,
        duration: 0,
        cpuUsage: 0,
        memoryUsage: memoryUsage.heapUsed,
      },
      tokenUsage: {
        inputTokens: 0,
        outputTokens: 0,
        totalTokens: 0,
        model: '',
        provider: 'rule-based'
      },
      cost: {
        inputCost: 0,
        outputCost: 0,
        totalCost: 0,
        currency: 'USD'
      },
      quality: {
        confidence: 0,
        fallbackUsed: false,
        servicePath: []
      },
      context: {
        requestSize: 0,
        responseSize: 0,
        cacheHit: false,
        retryCount: 0,
        errorCount: 0
      },
      metadata
    };

    this.activeOperations.set(operationId, operationMetrics);
    
    if (this.config.enableRealTimeStreaming) {
      this.emit('operation-started', { operationId, operation, phase });
    }
  }

  /**
   * Update token usage for an operation
   */
  updateTokenUsage(
    operationId: string,
    inputTokens: number,
    outputTokens: number,
    model: string,
    provider: BenchmarkMetrics['tokenUsage']['provider']
  ): void {
    if (!this.config.enableCollection) return;

    const operation = this.activeOperations.get(operationId);
    if (!operation || !operation.tokenUsage || !operation.cost) return;

    operation.tokenUsage.inputTokens += inputTokens;
    operation.tokenUsage.outputTokens += outputTokens;
    operation.tokenUsage.totalTokens = operation.tokenUsage.inputTokens + operation.tokenUsage.outputTokens;
    operation.tokenUsage.model = model;
    operation.tokenUsage.provider = provider;

    // Calculate costs
    const rates = this.config.costRates[provider] || { inputTokenCost: 0, outputTokenCost: 0 };
    const inputCost = (inputTokens / 1000) * rates.inputTokenCost;
    const outputCost = (outputTokens / 1000) * rates.outputTokenCost;
    
    operation.cost.inputCost += inputCost;
    operation.cost.outputCost += outputCost;
    operation.cost.totalCost = operation.cost.inputCost + operation.cost.outputCost;

    if (this.config.enableRealTimeStreaming) {
      this.emit('token-usage-updated', { 
        operationId, 
        tokenUsage: operation.tokenUsage, 
        cost: operation.cost 
      });
    }
  }

  /**
   * Update performance metrics for an operation
   */
  updatePerformance(
    operationId: string,
    updates: Partial<BenchmarkMetrics['performance']>
  ): void {
    if (!this.config.enableCollection) return;

    const operation = this.activeOperations.get(operationId);
    if (!operation || !operation.performance) return;

    Object.assign(operation.performance, updates);

    if (this.config.enableRealTimeStreaming) {
      this.emit('performance-updated', { operationId, performance: operation.performance });
    }
  }

  /**
   * Update quality metrics for an operation
   */
  updateQuality(
    operationId: string,
    confidence: number,
    fallbackUsed: boolean,
    servicePath: string[],
    accuracy?: number
  ): void {
    if (!this.config.enableCollection) return;

    const operation = this.activeOperations.get(operationId);
    if (!operation || !operation.quality) return;

    operation.quality.confidence = confidence;
    operation.quality.fallbackUsed = fallbackUsed;
    operation.quality.servicePath = servicePath;
    if (accuracy !== undefined) {
      operation.quality.accuracy = accuracy;
    }

    if (this.config.enableRealTimeStreaming) {
      this.emit('quality-updated', { operationId, quality: operation.quality });
    }
  }

  /**
   * Update context metrics for an operation
   */
  updateContext(
    operationId: string,
    updates: Partial<BenchmarkMetrics['context']>
  ): void {
    if (!this.config.enableCollection) return;

    const operation = this.activeOperations.get(operationId);
    if (!operation || !operation.context) return;

    Object.assign(operation.context, updates);

    if (this.config.enableRealTimeStreaming) {
      this.emit('context-updated', { operationId, context: operation.context });
    }
  }

  /**
   * Complete an operation and finalize metrics
   */
  completeOperation(
    operationId: string,
    success: boolean = true,
    error?: Error
  ): BenchmarkMetrics | null {
    if (!this.config.enableCollection) return null;

    const operation = this.activeOperations.get(operationId);
    if (!operation) return null;

    // Finalize performance metrics
    const endTime = performance.now();
    const memoryUsage = process.memoryUsage();
    
    if (operation.performance) {
      operation.performance.endTime = endTime;
      operation.performance.duration = endTime - operation.performance.startTime;
      operation.performance.memoryUsage = memoryUsage.heapUsed;
      
      // Calculate CPU usage (simplified)
      const cpuUsage = process.cpuUsage();
      operation.performance.cpuUsage = (cpuUsage.user + cpuUsage.system) / 1000000; // Convert to seconds
    }

    // Update error count if operation failed
    if (!success && operation.context) {
      operation.context.errorCount++;
    }

    // Add error information to metadata
    if (error && operation.metadata) {
      operation.metadata.error = {
        message: error.message,
        stack: error.stack,
        timestamp: new Date()
      };
    }

    // Convert to complete metrics
    const completeMetrics = operation as BenchmarkMetrics;
    
    // Store metrics
    this.metrics.set(operationId, completeMetrics);
    this.activeOperations.delete(operationId);

    // Cleanup old metrics if we exceed the limit
    if (this.metrics.size > this.config.maxMetricsInMemory) {
      this.cleanupOldMetrics();
    }

    if (this.config.enableRealTimeStreaming) {
      this.emit('operation-completed', { 
        operationId, 
        success, 
        metrics: completeMetrics 
      });
    }

    return completeMetrics;
  }

  private cleanupOldMetrics(): void {
    const metricsArray = Array.from(this.metrics.entries());
    metricsArray.sort(([, a], [, b]) => a.timestamp.getTime() - b.timestamp.getTime());
    
    const toRemove = metricsArray.slice(0, Math.floor(this.config.maxMetricsInMemory * 0.1));
    for (const [id] of toRemove) {
      this.metrics.delete(id);
    }
    
    console.log(`🧹 Cleaned up ${toRemove.length} old metrics`);
  }

  /**
   * Get metrics for a specific operation
   */
  getOperationMetrics(operationId: string): BenchmarkMetrics | null {
    return this.metrics.get(operationId) || null;
  }

  /**
   * Get all metrics within a time range
   */
  getMetricsInRange(startTime: Date, endTime: Date): BenchmarkMetrics[] {
    return Array.from(this.metrics.values()).filter(
      metric => metric.timestamp >= startTime && metric.timestamp <= endTime
    );
  }

  /**
   * Get aggregated metrics for a time range
   */
  getAggregatedMetrics(startTime: Date, endTime: Date): AggregatedMetrics {
    const metricsInRange = this.getMetricsInRange(startTime, endTime);
    
    if (metricsInRange.length === 0) {
      return this.createEmptyAggregatedMetrics(startTime, endTime);
    }

    const totalOperations = metricsInRange.length;
    const successfulOperations = metricsInRange.filter(m => !m.metadata?.error).length;
    const failedOperations = totalOperations - successfulOperations;
    const successRate = totalOperations > 0 ? successfulOperations / totalOperations : 0;

    // Token usage aggregation
    const totalInputTokens = metricsInRange.reduce((sum, m) => sum + m.tokenUsage.inputTokens, 0);
    const totalOutputTokens = metricsInRange.reduce((sum, m) => sum + m.tokenUsage.outputTokens, 0);
    const totalTokens = totalInputTokens + totalOutputTokens;
    const averageTokensPerOperation = totalOperations > 0 ? totalTokens / totalOperations : 0;
    
    const tokensByProvider: Record<string, number> = {};
    metricsInRange.forEach(m => {
      tokensByProvider[m.tokenUsage.provider] = (tokensByProvider[m.tokenUsage.provider] || 0) + m.tokenUsage.totalTokens;
    });

    // Performance aggregation
    const durations = metricsInRange.map(m => m.performance.duration).sort((a, b) => a - b);
    const averageDuration = durations.reduce((sum, d) => sum + d, 0) / durations.length;
    const medianDuration = durations[Math.floor(durations.length / 2)];
    const p95Duration = durations[Math.floor(durations.length * 0.95)];
    const p99Duration = durations[Math.floor(durations.length * 0.99)];
    const averageCpuUsage = metricsInRange.reduce((sum, m) => sum + m.performance.cpuUsage, 0) / totalOperations;
    const averageMemoryUsage = metricsInRange.reduce((sum, m) => sum + m.performance.memoryUsage, 0) / totalOperations;
    const peakMemoryUsage = Math.max(...metricsInRange.map(m => m.performance.memoryUsage));

    // Cost aggregation
    const totalCost = metricsInRange.reduce((sum, m) => sum + m.cost.totalCost, 0);
    const averageCostPerOperation = totalOperations > 0 ? totalCost / totalOperations : 0;
    
    const costByProvider: Record<string, number> = {};
    const costByPhase: Record<string, number> = {};
    metricsInRange.forEach(m => {
      costByProvider[m.tokenUsage.provider] = (costByProvider[m.tokenUsage.provider] || 0) + m.cost.totalCost;
      costByPhase[m.phase] = (costByPhase[m.phase] || 0) + m.cost.totalCost;
    });

    // Quality aggregation
    const averageConfidence = metricsInRange.reduce((sum, m) => sum + m.quality.confidence, 0) / totalOperations;
    const fallbackUsageRate = metricsInRange.filter(m => m.quality.fallbackUsed).length / totalOperations;
    const cacheHitRate = metricsInRange.filter(m => m.context.cacheHit).length / totalOperations;
    const averageRetryCount = metricsInRange.reduce((sum, m) => sum + m.context.retryCount, 0) / totalOperations;

    return {
      timeRange: {
        start: startTime,
        end: endTime,
        duration: endTime.getTime() - startTime.getTime()
      },
      totalOperations,
      successfulOperations,
      failedOperations,
      successRate,
      tokenUsage: {
        totalInputTokens,
        totalOutputTokens,
        totalTokens,
        averageTokensPerOperation,
        tokensByProvider
      },
      performance: {
        averageDuration,
        medianDuration,
        p95Duration,
        p99Duration,
        averageCpuUsage,
        averageMemoryUsage,
        peakMemoryUsage
      },
      cost: {
        totalCost,
        averageCostPerOperation,
        costByProvider,
        costByPhase
      },
      quality: {
        averageConfidence,
        fallbackUsageRate,
        cacheHitRate,
        averageRetryCount
      }
    };
  }

  private createEmptyAggregatedMetrics(startTime: Date, endTime: Date): AggregatedMetrics {
    return {
      timeRange: {
        start: startTime,
        end: endTime,
        duration: endTime.getTime() - startTime.getTime()
      },
      totalOperations: 0,
      successfulOperations: 0,
      failedOperations: 0,
      successRate: 0,
      tokenUsage: {
        totalInputTokens: 0,
        totalOutputTokens: 0,
        totalTokens: 0,
        averageTokensPerOperation: 0,
        tokensByProvider: {}
      },
      performance: {
        averageDuration: 0,
        medianDuration: 0,
        p95Duration: 0,
        p99Duration: 0,
        averageCpuUsage: 0,
        averageMemoryUsage: 0,
        peakMemoryUsage: 0
      },
      cost: {
        totalCost: 0,
        averageCostPerOperation: 0,
        costByProvider: {},
        costByPhase: {}
      },
      quality: {
        averageConfidence: 0,
        fallbackUsageRate: 0,
        cacheHitRate: 0,
        averageRetryCount: 0
      }
    };
  }

  /**
   * Get current system resource usage
   */
  getCurrentResourceUsage(): {
    memory: NodeJS.MemoryUsage;
    cpu: NodeJS.CpuUsage;
    uptime: number;
  } {
    return {
      memory: process.memoryUsage(),
      cpu: process.cpuUsage(),
      uptime: process.uptime()
    };
  }

  /**
   * Export metrics to JSON
   */
  async exportMetrics(filePath: string, startTime?: Date, endTime?: Date): Promise<void> {
    let metricsToExport: BenchmarkMetrics[];
    
    if (startTime && endTime) {
      metricsToExport = this.getMetricsInRange(startTime, endTime);
    } else {
      metricsToExport = Array.from(this.metrics.values());
    }

    const exportData = {
      exportTimestamp: new Date(),
      totalMetrics: metricsToExport.length,
      timeRange: startTime && endTime ? { start: startTime, end: endTime } : null,
      metrics: metricsToExport
    };

    await fs.writeFile(filePath, JSON.stringify(exportData, null, 2));
    console.log(`📤 Exported ${metricsToExport.length} metrics to ${filePath}`);
  }

  /**
   * Clear all metrics
   */
  clearMetrics(): void {
    const count = this.metrics.size;
    this.metrics.clear();
    this.activeOperations.clear();
    
    console.log(`🗑️ Cleared ${count} metrics`);
    this.emit('metrics-cleared', { count });
  }

  /**
   * Shutdown the metrics collector
   */
  async shutdown(): Promise<void> {
    if (this.persistenceTimer) {
      clearInterval(this.persistenceTimer);
      this.persistenceTimer = null;
    }

    if (this.config.enablePersistence) {
      await this.persistMetrics();
    }

    console.log('💾 Metrics collector shutdown complete');
    this.emit('metrics-shutdown');
  }
}

// Singleton instance
export const metricsCollector = new MetricsCollector();