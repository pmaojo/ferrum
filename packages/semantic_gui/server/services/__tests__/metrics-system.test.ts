/**
 * Tests for Comprehensive Metrics Collection System
 */

import { metricsCollector } from '../metrics-collector';
import { metricsIntegration } from '../metrics-integration';
import { baselineComparison } from '../baseline-comparison';

describe('Comprehensive Metrics Collection System', () => {
  beforeAll(async () => {
    // Wait for system initialization
    await new Promise(resolve => setTimeout(resolve, 1000));
  });

  afterAll(async () => {
    await metricsCollector.shutdown();
    await metricsIntegration.shutdown();
  });

  describe('Metrics Collector', () => {
    it('should start and complete operations', async () => {
      const operationId = 'test_operation_1';
      
      metricsCollector.startOperation(
        operationId,
        'test-operation',
        'intent-classification',
        { testData: true }
      );

      // Update token usage
      metricsCollector.updateTokenUsage(operationId, 100, 50, 'gpt-4', 'openai');
      
      // Update performance
      metricsCollector.updatePerformance(operationId, {
        networkLatency: 1500
      });
      
      // Update quality
      metricsCollector.updateQuality(operationId, 0.85, false, ['openai']);
      
      // Update context
      metricsCollector.updateContext(operationId, {
        requestSize: 1000,
        responseSize: 2000,
        cacheHit: false
      });

      // Complete operation
      const metrics = metricsCollector.completeOperation(operationId, true);

      expect(metrics).toBeDefined();
      expect(metrics?.id).toBe(operationId);
      expect(metrics?.tokenUsage.inputTokens).toBe(100);
      expect(metrics?.tokenUsage.outputTokens).toBe(50);
      expect(metrics?.quality.confidence).toBe(0.85);
      expect(metrics?.cost.totalCost).toBeGreaterThan(0);
    });

    it('should calculate aggregated metrics', async () => {
      const now = new Date();
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
      
      // Create a few test operations
      for (let i = 0; i < 3; i++) {
        const operationId = `test_agg_${i}`;
        metricsCollector.startOperation(operationId, 'test-agg', 'complete');
        metricsCollector.updateTokenUsage(operationId, 50 + i * 10, 25 + i * 5, 'gpt-4', 'openai');
        metricsCollector.updateQuality(operationId, 0.8 + i * 0.05, false, ['openai']);
        metricsCollector.completeOperation(operationId, true);
      }

      const aggregated = metricsCollector.getAggregatedMetrics(oneHourAgo, now);
      
      expect(aggregated.totalOperations).toBeGreaterThanOrEqual(3);
      expect(aggregated.successRate).toBeGreaterThan(0);
      expect(aggregated.tokenUsage.totalTokens).toBeGreaterThan(0);
      expect(aggregated.cost.totalCost).toBeGreaterThan(0);
    });

    it('should handle operation failures', async () => {
      const operationId = 'test_failure';
      
      metricsCollector.startOperation(operationId, 'test-failure', 'complete');
      
      const error = new Error('Test error');
      const metrics = metricsCollector.completeOperation(operationId, false, error);
      
      expect(metrics).toBeDefined();
      expect(metrics?.metadata?.error?.message).toBe('Test error');
      expect(metrics?.context.errorCount).toBe(1);
    });
  });

  describe('Metrics Integration', () => {
    it('should provide dashboard data', () => {
      const dashboardData = metricsIntegration.getDashboardData();
      
      expect(dashboardData).toBeDefined();
      expect(dashboardData.currentMetrics).toBeDefined();
      expect(dashboardData.resourceUsage).toBeDefined();
      expect(dashboardData.systemHealth).toBeDefined();
      expect(dashboardData.recentOperations).toBeInstanceOf(Array);
    });

    it('should generate metrics reports', async () => {
      const now = new Date();
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
      
      const report = await metricsIntegration.generateReport(oneHourAgo, now, false);
      
      expect(report).toBeDefined();
      expect(report.summary).toBeDefined();
      expect(report.insights).toBeInstanceOf(Array);
      expect(report.recommendations).toBeInstanceOf(Array);
    });

    it('should instrument functions', async () => {
      const testFunction = async (input: string) => {
        await new Promise(resolve => setTimeout(resolve, 100));
        return `processed: ${input}`;
      };

      const instrumentedFunction = metricsIntegration.instrumentFunction(
        testFunction,
        'test-instrumented-function',
        'complete'
      );

      const result = await instrumentedFunction('test input');
      
      expect(result).toBe('processed: test input');
    });
  });

  describe('Baseline Comparison', () => {
    it('should simulate full-context LLM approach', async () => {
      const mockRequest = {
        text: 'add 2FA to my payment service',
        context: {
          files: ['auth.js', 'payment.js'],
          fileContents: new Map([
            ['auth.js', 'const auth = require("auth");'],
            ['payment.js', 'const payment = require("payment");']
          ])
        },
        options: { allowFallbacks: true }
      };

      const simulation = await baselineComparison.simulateFullContextLLM(mockRequest, 'gpt-4');
      
      expect(simulation).toBeDefined();
      expect(simulation.approach).toBe('full-context-llm');
      expect(simulation.performance.cost).toBeGreaterThan(0);
      expect(simulation.performance.tokenUsage.totalTokens).toBeGreaterThan(0);
      expect(simulation.quality.confidence).toBeGreaterThan(0.8);
    });

    it('should simulate rule-based only approach', async () => {
      const mockRequest = {
        text: 'add 2FA to my payment service',
        context: {
          files: ['auth.js', 'payment.js']
        },
        options: { allowFallbacks: true }
      };

      const simulation = await baselineComparison.simulateRuleBasedOnly(mockRequest);
      
      expect(simulation).toBeDefined();
      expect(simulation.approach).toBe('rule-based-only');
      expect(simulation.performance.cost).toBe(0); // Rule-based is free
      expect(simulation.performance.duration).toBeLessThan(500); // Should be fast
      expect(simulation.quality.confidence).toBeLessThan(0.8); // Lower quality
    });

    it('should generate comparison reports', async () => {
      // Start collection
      baselineComparison.startCollection();
      
      const now = new Date();
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
      
      const report = await baselineComparison.generateComparisonReport(
        oneHourAgo,
        now,
        true // Include simulations
      );
      
      expect(report).toBeDefined();
      expect(report.timeRange).toBeDefined();
      expect(report.approaches).toBeDefined();
      expect(report.comparison).toBeDefined();
      expect(report.insights).toBeDefined();
      expect(report.insights.recommendations).toBeInstanceOf(Array);
      
      baselineComparison.stopCollection();
    });

    it('should handle context limit exceeded', async () => {
      const largeRequest = {
        text: 'a'.repeat(1000000), // Very large request
        context: {
          files: new Array(1000).fill('large-file.js'),
          fileContents: new Map([
            ['large-file.js', 'x'.repeat(100000)]
          ])
        },
        options: { allowFallbacks: true }
      };

      await expect(
        baselineComparison.simulateFullContextLLM(largeRequest, 'gpt-3.5-turbo')
      ).rejects.toThrow('exceeds model context limit');
    });
  });

  describe('Integration Tests', () => {
    it('should collect metrics during hybrid intelligence operations', (done) => {
      let operationStarted = false;
      let operationCompleted = false;

      metricsIntegration.on('metrics-stream', (event) => {
        if (event.type === 'operation-started') {
          operationStarted = true;
        }
        if (event.type === 'operation-completed') {
          operationCompleted = true;
        }
        
        if (operationStarted && operationCompleted) {
          done();
        }
      });

      // Simulate a hybrid intelligence request
      const testOperationId = 'integration_test';
      metricsCollector.startOperation(testOperationId, 'integration-test', 'complete');
      metricsCollector.updateTokenUsage(testOperationId, 10, 5, 'test-model', 'local');
      metricsCollector.completeOperation(testOperationId, true);
    });

    it('should stream resource monitoring data', (done) => {
      metricsIntegration.on('resource-monitoring', (data) => {
        expect(data).toBeDefined();
        expect(data.timestamp).toBeInstanceOf(Date);
        expect(data.memory).toBeDefined();
        expect(data.cpu).toBeDefined();
        expect(data.services).toBeDefined();
        done();
      });
    });
  });

  describe('Performance Tests', () => {
    it('should handle high-volume metrics collection', async () => {
      const startTime = Date.now();
      const operationCount = 100;
      
      // Create many operations quickly
      const promises = [];
      for (let i = 0; i < operationCount; i++) {
        const operationId = `perf_test_${i}`;
        
        const promise = new Promise<void>((resolve) => {
          metricsCollector.startOperation(operationId, 'perf-test', 'complete');
          metricsCollector.updateTokenUsage(operationId, 10, 5, 'test-model', 'local');
          metricsCollector.updateQuality(operationId, 0.8, false, ['local']);
          metricsCollector.completeOperation(operationId, true);
          resolve();
        });
        
        promises.push(promise);
      }
      
      await Promise.all(promises);
      
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      console.log(`Processed ${operationCount} operations in ${duration}ms`);
      expect(duration).toBeLessThan(5000); // Should complete within 5 seconds
    });
  });
});