/**
 * Metrics Integration Service
 * 
 * Integrates metrics collection with the hybrid intelligence system,
 * providing automatic instrumentation and real-time metrics streaming.
 */

import { EventEmitter } from 'events';
import { metricsCollector, BenchmarkMetrics, AggregatedMetrics } from './metrics-collector';
import { enhancedHybridIntelligence } from './hybrid-intelligence-enhanced';
import { healthMonitor } from './health-monitor';

export interface MetricsStreamEvent {
  type: 'operation-started' | 'operation-completed' | 'token-usage-updated' | 'performance-updated' | 'aggregated-update';
  timestamp: Date;
  data: any;
}

export interface ResourceMonitoringData {
  timestamp: Date;
  memory: {
    heapUsed: number;
    heapTotal: number;
    external: number;
    rss: number;
  };
  cpu: {
    user: number;
    system: number;
  };
  services: {
    healthy: number;
    unhealthy: number;
    total: number;
  };
  activeOperations: number;
}

export class MetricsIntegration extends EventEmitter {
  private isInitialized = false;
  private resourceMonitoringInterval: NodeJS.Timeout | null = null;
  private aggregationInterval: NodeJS.Timeout | null = null;
  private lastAggregationTime = new Date();

  constructor() {
    super();
    this.initialize();
  }

  private async initialize(): Promise<void> {
    try {
      console.log('📊 Initializing metrics integration...');

      // Set up event listeners for hybrid intelligence system
      this.setupHybridIntelligenceListeners();

      // Set up event listeners for metrics collector
      this.setupMetricsCollectorListeners();

      // Set up event listeners for health monitor
      this.setupHealthMonitorListeners();

      // Start resource monitoring
      this.startResourceMonitoring();

      // Start periodic aggregation
      this.startPeriodicAggregation();

      this.isInitialized = true;
      console.log('✅ Metrics integration initialized');
      this.emit('integration-ready');

    } catch (error) {
      console.error('❌ Failed to initialize metrics integration:', error);
      this.emit('integration-error', { error, phase: 'initialization' });
    }
  }

  private setupHybridIntelligenceListeners(): void {
    // Listen for request processing events
    enhancedHybridIntelligence.on('request-started', ({ requestId, request }) => {
      metricsCollector.startOperation(
        requestId,
        'hybrid-intelligence-request',
        'intent-classification',
        {
          requestText: request.text,
          contextFiles: request.context.files?.length || 0,
          options: request.options
        }
      );

      // Update context with request size
      const requestSize = JSON.stringify(request).length;
      metricsCollector.updateContext(requestId, { requestSize });
    });

    enhancedHybridIntelligence.on('request-completed', ({ requestId, response }) => {
      // Update quality metrics
      metricsCollector.updateQuality(
        requestId,
        response.confidence,
        response.fallbacksUsed,
        response.servicePath
      );

      // Update context with response size
      const responseSize = JSON.stringify(response).length;
      metricsCollector.updateContext(requestId, { 
        responseSize,
        cacheHit: response.metadata.cacheHits > 0
      });

      // Complete the operation
      metricsCollector.completeOperation(requestId, response.success);
    });

    enhancedHybridIntelligence.on('request-failed', ({ requestId, error, metadata }) => {
      // Update context with error information
      metricsCollector.updateContext(requestId, { 
        errorCount: 1,
        retryCount: metadata.errors?.length || 0
      });

      // Complete the operation with failure
      metricsCollector.completeOperation(requestId, false, error);
    });

    enhancedHybridIntelligence.on('processing-step', (step) => {
      if (step.status === 'completed' && step.confidence) {
        // Update phase-specific metrics
        const operationId = this.findOperationIdForStep(step);
        if (operationId) {
          metricsCollector.updateQuality(
            operationId,
            step.confidence,
            step.service !== 'rule-based-analyzer',
            [step.service]
          );

          // Update performance if duration is available
          if (step.duration) {
            metricsCollector.updatePerformance(operationId, {
              networkLatency: step.duration
            });
          }
        }
      }
    });
  }

  private setupMetricsCollectorListeners(): void {
    // Forward metrics events for real-time streaming
    metricsCollector.on('operation-started', (data) => {
      this.emit('metrics-stream', {
        type: 'operation-started',
        timestamp: new Date(),
        data
      } as MetricsStreamEvent);
    });

    metricsCollector.on('operation-completed', (data) => {
      this.emit('metrics-stream', {
        type: 'operation-completed',
        timestamp: new Date(),
        data
      } as MetricsStreamEvent);
    });

    metricsCollector.on('token-usage-updated', (data) => {
      this.emit('metrics-stream', {
        type: 'token-usage-updated',
        timestamp: new Date(),
        data
      } as MetricsStreamEvent);
    });

    metricsCollector.on('performance-updated', (data) => {
      this.emit('metrics-stream', {
        type: 'performance-updated',
        timestamp: new Date(),
        data
      } as MetricsStreamEvent);
    });
  }

  private setupHealthMonitorListeners(): void {
    // Track service health changes in metrics
    healthMonitor.on('service-unhealthy', ({ serviceName, health, error }) => {
      // This could be used to correlate service health with performance metrics
      this.emit('service-health-changed', {
        serviceName,
        status: 'unhealthy',
        timestamp: new Date(),
        error: error?.message
      });
    });

    healthMonitor.on('service-healthy', ({ serviceName, health }) => {
      this.emit('service-health-changed', {
        serviceName,
        status: 'healthy',
        timestamp: new Date()
      });
    });
  }

  private findOperationIdForStep(step: any): string | null {
    // This is a simplified implementation
    // In a real system, you'd maintain a mapping between processing steps and operation IDs
    return null;
  }

  private startResourceMonitoring(): void {
    this.resourceMonitoringInterval = setInterval(() => {
      const resourceData = this.collectResourceData();
      
      this.emit('resource-monitoring', resourceData);
      
      // Emit as metrics stream event
      this.emit('metrics-stream', {
        type: 'resource-update',
        timestamp: new Date(),
        data: resourceData
      } as any);
      
    }, 5000); // Every 5 seconds
  }

  private collectResourceData(): ResourceMonitoringData {
    const memoryUsage = process.memoryUsage();
    const cpuUsage = process.cpuUsage();
    const systemHealth = healthMonitor.getSystemHealth();
    
    return {
      timestamp: new Date(),
      memory: {
        heapUsed: memoryUsage.heapUsed,
        heapTotal: memoryUsage.heapTotal,
        external: memoryUsage.external,
        rss: memoryUsage.rss
      },
      cpu: {
        user: cpuUsage.user,
        system: cpuUsage.system
      },
      services: {
        healthy: systemHealth.services.filter(s => s.status === 'healthy').length,
        unhealthy: systemHealth.services.filter(s => s.status === 'unhealthy').length,
        total: systemHealth.services.length
      },
      activeOperations: 0 // This would be tracked by the metrics collector
    };
  }

  private startPeriodicAggregation(): void {
    this.aggregationInterval = setInterval(() => {
      const now = new Date();
      const aggregatedMetrics = metricsCollector.getAggregatedMetrics(
        this.lastAggregationTime,
        now
      );
      
      this.lastAggregationTime = now;
      
      this.emit('metrics-stream', {
        type: 'aggregated-update',
        timestamp: now,
        data: aggregatedMetrics
      } as MetricsStreamEvent);
      
    }, 60000); // Every minute
  }

  /**
   * Instrument a function with automatic metrics collection
   */
  instrumentFunction<T extends (...args: any[]) => Promise<any>>(
    fn: T,
    operationName: string,
    phase: BenchmarkMetrics['phase']
  ): T {
    return (async (...args: any[]) => {
      const operationId = `${operationName}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      metricsCollector.startOperation(operationId, operationName, phase, {
        arguments: args.length,
        functionName: fn.name
      });

      try {
        const result = await fn(...args);
        
        // Update context with result size
        const resultSize = JSON.stringify(result).length;
        metricsCollector.updateContext(operationId, { responseSize: resultSize });
        
        metricsCollector.completeOperation(operationId, true);
        return result;
        
      } catch (error) {
        metricsCollector.completeOperation(operationId, false, error as Error);
        throw error;
      }
    }) as T;
  }

  /**
   * Create a metrics-aware wrapper for LLM calls
   */
  instrumentLLMCall<T>(
    llmCall: () => Promise<T>,
    model: string,
    provider: BenchmarkMetrics['tokenUsage']['provider'],
    estimatedInputTokens: number = 0,
    operationId?: string
  ): Promise<T> {
    const id = operationId || `llm_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    if (!operationId) {
      metricsCollector.startOperation(id, 'llm-call', 'complete', {
        model,
        provider,
        estimatedInputTokens
      });
    }

    return new Promise(async (resolve, reject) => {
      try {
        const startTime = performance.now();
        const result = await llmCall();
        const endTime = performance.now();
        
        // Update token usage (this would need to be extracted from the actual LLM response)
        metricsCollector.updateTokenUsage(
          id,
          estimatedInputTokens,
          0, // Output tokens would need to be calculated from response
          model,
          provider
        );
        
        // Update performance
        metricsCollector.updatePerformance(id, {
          networkLatency: endTime - startTime
        });
        
        if (!operationId) {
          metricsCollector.completeOperation(id, true);
        }
        
        resolve(result);
        
      } catch (error) {
        if (!operationId) {
          metricsCollector.completeOperation(id, false, error as Error);
        }
        reject(error);
      }
    });
  }

  /**
   * Get real-time metrics dashboard data
   */
  getDashboardData(): {
    currentMetrics: AggregatedMetrics;
    resourceUsage: ResourceMonitoringData;
    systemHealth: any;
    recentOperations: BenchmarkMetrics[];
  } {
    const now = new Date();
    const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
    
    return {
      currentMetrics: metricsCollector.getAggregatedMetrics(oneHourAgo, now),
      resourceUsage: this.collectResourceData(),
      systemHealth: healthMonitor.getSystemHealth(),
      recentOperations: metricsCollector.getMetricsInRange(
        new Date(now.getTime() - 10 * 60 * 1000), // Last 10 minutes
        now
      ).slice(-10) // Last 10 operations
    };
  }

  /**
   * Generate a comprehensive metrics report
   */
  async generateReport(
    startTime: Date,
    endTime: Date,
    includeDetails: boolean = false
  ): Promise<{
    summary: AggregatedMetrics;
    details?: BenchmarkMetrics[];
    insights: string[];
    recommendations: string[];
  }> {
    const summary = metricsCollector.getAggregatedMetrics(startTime, endTime);
    const details = includeDetails ? metricsCollector.getMetricsInRange(startTime, endTime) : undefined;
    
    // Generate insights
    const insights: string[] = [];
    const recommendations: string[] = [];
    
    if (summary.cost.totalCost > 10) {
      insights.push(`High cost detected: $${summary.cost.totalCost.toFixed(2)} for ${summary.totalOperations} operations`);
      recommendations.push('Consider optimizing token usage or using more cost-effective models');
    }
    
    if (summary.quality.fallbackUsageRate > 0.3) {
      insights.push(`High fallback usage: ${(summary.quality.fallbackUsageRate * 100).toFixed(1)}% of operations used fallbacks`);
      recommendations.push('Investigate primary service reliability and consider improving health monitoring');
    }
    
    if (summary.performance.averageDuration > 5000) {
      insights.push(`Slow performance: Average operation takes ${(summary.performance.averageDuration / 1000).toFixed(1)} seconds`);
      recommendations.push('Consider implementing more aggressive caching or optimizing service calls');
    }
    
    if (summary.quality.cacheHitRate < 0.2) {
      insights.push(`Low cache hit rate: ${(summary.quality.cacheHitRate * 100).toFixed(1)}%`);
      recommendations.push('Review cache TTL settings and cache key strategies');
    }
    
    return {
      summary,
      details,
      insights,
      recommendations
    };
  }

  /**
   * Export metrics with analysis
   */
  async exportMetricsWithAnalysis(
    filePath: string,
    startTime: Date,
    endTime: Date
  ): Promise<void> {
    const report = await this.generateReport(startTime, endTime, true);
    
    const exportData = {
      exportTimestamp: new Date(),
      timeRange: { start: startTime, end: endTime },
      report,
      systemInfo: {
        nodeVersion: process.version,
        platform: process.platform,
        arch: process.arch,
        uptime: process.uptime()
      }
    };
    
    await metricsCollector.exportMetrics(filePath);
    console.log(`📊 Exported metrics analysis to ${filePath}`);
  }

  /**
   * Shutdown the metrics integration
   */
  async shutdown(): Promise<void> {
    if (this.resourceMonitoringInterval) {
      clearInterval(this.resourceMonitoringInterval);
      this.resourceMonitoringInterval = null;
    }
    
    if (this.aggregationInterval) {
      clearInterval(this.aggregationInterval);
      this.aggregationInterval = null;
    }
    
    await metricsCollector.shutdown();
    
    console.log('📊 Metrics integration shutdown complete');
    this.emit('integration-shutdown');
  }
}

// Singleton instance
export const metricsIntegration = new MetricsIntegration();