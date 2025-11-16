/**
 * Baseline Comparison Engine
 * 
 * Implements performance comparison between hybrid intelligence approach
 * and full-context LLM approaches with cost-benefit analysis.
 */

import { EventEmitter } from 'events';
import { metricsCollector, BenchmarkMetrics, AggregatedMetrics } from './metrics-collector';
import { enhancedHybridIntelligence, HybridIntelligenceRequest, HybridIntelligenceResponse } from './hybrid-intelligence-enhanced';

export interface BaselineMetrics {
  id: string;
  timestamp: Date;
  approach: 'hybrid' | 'full-context-llm' | 'rule-based-only';
  
  // Request characteristics
  request: {
    textLength: number;
    contextFiles: number;
    contextSize: number; // bytes
    complexity: 'low' | 'medium' | 'high';
  };
  
  // Performance metrics
  performance: {
    duration: number; // milliseconds
    tokenUsage: {
      inputTokens: number;
      outputTokens: number;
      totalTokens: number;
    };
    cost: number; // USD
    memoryUsage: number; // bytes
  };
  
  // Quality metrics
  quality: {
    confidence: number; // 0-1
    accuracy?: number; // 0-1 (if ground truth available)
    completeness: number; // 0-1
    relevance: number; // 0-1
  };
  
  // Result characteristics
  result: {
    responseLength: number;
    recommendationsCount: number;
    codeGenerated: boolean;
    securityIssuesFound: number;
  };
  
  metadata: Record<string, any>;
}

export interface ComparisonResult {
  timeRange: {
    start: Date;
    end: Date;
  };
  
  approaches: {
    hybrid: BaselineMetrics[];
    fullContextLLM: BaselineMetrics[];
    ruleBasedOnly: BaselineMetrics[];
  };
  
  comparison: {
    performance: {
      averageDuration: Record<string, number>;
      averageCost: Record<string, number>;
      averageTokenUsage: Record<string, number>;
      costEfficiency: Record<string, number>; // quality per dollar
    };
    
    quality: {
      averageConfidence: Record<string, number>;
      averageAccuracy: Record<string, number>;
      averageCompleteness: Record<string, number>;
      averageRelevance: Record<string, number>;
    };
    
    scalability: {
      throughput: Record<string, number>; // operations per minute
      resourceUsage: Record<string, number>; // memory per operation
      costPerOperation: Record<string, number>;
    };
  };
  
  insights: {
    winner: string;
    costSavings: number; // percentage
    performanceGain: number; // percentage
    qualityDelta: number; // percentage
    recommendations: string[];
  };
}

export interface FullContextLLMSimulation {
  model: 'gpt-4' | 'gpt-3.5-turbo' | 'claude-3' | 'gemini-pro';
  maxContextTokens: number;
  costPerInputToken: number;
  costPerOutputToken: number;
  averageLatency: number; // milliseconds
  qualityScore: number; // 0-1
}

export class BaselineComparison extends EventEmitter {
  private baselineMetrics: Map<string, BaselineMetrics> = new Map();
  private fullContextSimulations: Map<string, FullContextLLMSimulation> = new Map();
  private isCollecting = false;

  constructor() {
    super();
    this.initializeFullContextSimulations();
    this.setupEventListeners();
  }

  private initializeFullContextSimulations(): void {
    // GPT-4 simulation
    this.fullContextSimulations.set('gpt-4', {
      model: 'gpt-4',
      maxContextTokens: 128000,
      costPerInputToken: 0.03 / 1000, // $0.03 per 1K tokens
      costPerOutputToken: 0.06 / 1000, // $0.06 per 1K tokens
      averageLatency: 3000, // 3 seconds
      qualityScore: 0.95
    });

    // GPT-3.5 Turbo simulation
    this.fullContextSimulations.set('gpt-3.5-turbo', {
      model: 'gpt-3.5-turbo',
      maxContextTokens: 16385,
      costPerInputToken: 0.0015 / 1000, // $0.0015 per 1K tokens
      costPerOutputToken: 0.002 / 1000, // $0.002 per 1K tokens
      averageLatency: 1500, // 1.5 seconds
      qualityScore: 0.85
    });

    // Claude-3 simulation
    this.fullContextSimulations.set('claude-3', {
      model: 'claude-3',
      maxContextTokens: 200000,
      costPerInputToken: 0.015 / 1000, // $0.015 per 1K tokens
      costPerOutputToken: 0.075 / 1000, // $0.075 per 1K tokens
      averageLatency: 2500, // 2.5 seconds
      qualityScore: 0.92
    });

    // Gemini Pro simulation
    this.fullContextSimulations.set('gemini-pro', {
      model: 'gemini-pro',
      maxContextTokens: 32768,
      costPerInputToken: 0.00025 / 1000, // $0.00025 per 1K tokens
      costPerOutputToken: 0.0005 / 1000, // $0.0005 per 1K tokens
      averageLatency: 2000, // 2 seconds
      qualityScore: 0.88
    });
  }

  private setupEventListeners(): void {
    // Listen for hybrid intelligence operations
    enhancedHybridIntelligence.on('request-completed', ({ requestId, response, request }) => {
      if (this.isCollecting) {
        this.recordHybridMetrics(requestId, request, response);
      }
    });

    // Listen for metrics collection events
    metricsCollector.on('operation-completed', ({ operationId, metrics }) => {
      if (this.isCollecting && metrics.operation === 'hybrid-intelligence-request') {
        this.updateBaselineMetricsFromCollector(operationId, metrics);
      }
    });
  }

  /**
   * Start baseline comparison collection
   */
  startCollection(): void {
    this.isCollecting = true;
    console.log('📊 Started baseline comparison collection');
    this.emit('collection-started');
  }

  /**
   * Stop baseline comparison collection
   */
  stopCollection(): void {
    this.isCollecting = false;
    console.log('⏹️ Stopped baseline comparison collection');
    this.emit('collection-stopped');
  }

  private recordHybridMetrics(
    requestId: string,
    request: HybridIntelligenceRequest,
    response: HybridIntelligenceResponse
  ): void {
    const contextSize = this.calculateContextSize(request);
    const complexity = this.assessComplexity(request);
    
    const baselineMetric: BaselineMetrics = {
      id: requestId,
      timestamp: new Date(),
      approach: 'hybrid',
      request: {
        textLength: request.text.length,
        contextFiles: request.context.files?.length || 0,
        contextSize,
        complexity
      },
      performance: {
        duration: response.metadata.processingTime,
        tokenUsage: {
          inputTokens: 0, // Will be updated from metrics collector
          outputTokens: 0,
          totalTokens: 0
        },
        cost: 0, // Will be updated from metrics collector
        memoryUsage: 0 // Will be updated from metrics collector
      },
      quality: {
        confidence: response.confidence,
        completeness: this.assessCompleteness(response),
        relevance: this.assessRelevance(response, request)
      },
      result: {
        responseLength: JSON.stringify(response).length,
        recommendationsCount: response.recommendations.length,
        codeGenerated: response.recommendations.some(r => r.includes('implement') || r.includes('create')),
        securityIssuesFound: response.security.risks.length
      },
      metadata: {
        fallbacksUsed: response.fallbacksUsed,
        servicePath: response.servicePath,
        intent: response.intent.intent,
        domain: response.domain.domain
      }
    };

    this.baselineMetrics.set(requestId, baselineMetric);
  }

  private updateBaselineMetricsFromCollector(operationId: string, metrics: BenchmarkMetrics): void {
    const baselineMetric = this.baselineMetrics.get(operationId);
    if (!baselineMetric) return;

    // Update performance metrics from collector
    baselineMetric.performance.tokenUsage = {
      inputTokens: metrics.tokenUsage.inputTokens,
      outputTokens: metrics.tokenUsage.outputTokens,
      totalTokens: metrics.tokenUsage.totalTokens
    };
    baselineMetric.performance.cost = metrics.cost.totalCost;
    baselineMetric.performance.memoryUsage = metrics.performance.memoryUsage;
  }

  /**
   * Simulate full-context LLM approach for comparison
   */
  async simulateFullContextLLM(
    request: HybridIntelligenceRequest,
    model: string = 'gpt-4'
  ): Promise<BaselineMetrics> {
    const simulation = this.fullContextSimulations.get(model);
    if (!simulation) {
      throw new Error(`Unknown model for simulation: ${model}`);
    }

    const contextSize = this.calculateContextSize(request);
    const complexity = this.assessComplexity(request);
    
    // Estimate token usage for full context
    const estimatedInputTokens = Math.ceil(contextSize / 4); // Rough estimate: 4 chars per token
    const estimatedOutputTokens = Math.ceil(estimatedInputTokens * 0.3); // 30% of input as output
    
    // Check if request exceeds model's context limit
    if (estimatedInputTokens > simulation.maxContextTokens) {
      throw new Error(`Request exceeds model context limit: ${estimatedInputTokens} > ${simulation.maxContextTokens}`);
    }

    // Calculate costs
    const inputCost = estimatedInputTokens * simulation.costPerInputToken;
    const outputCost = estimatedOutputTokens * simulation.costPerOutputToken;
    const totalCost = inputCost + outputCost;

    // Simulate latency with some variance
    const latencyVariance = 0.2; // 20% variance
    const simulatedLatency = simulation.averageLatency * (1 + (Math.random() - 0.5) * latencyVariance);

    // Simulate quality based on complexity
    let qualityMultiplier = 1.0;
    if (complexity === 'high') qualityMultiplier = 0.9;
    else if (complexity === 'medium') qualityMultiplier = 0.95;

    const simulatedQuality = simulation.qualityScore * qualityMultiplier;

    const baselineMetric: BaselineMetrics = {
      id: `sim_${model}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      approach: 'full-context-llm',
      request: {
        textLength: request.text.length,
        contextFiles: request.context.files?.length || 0,
        contextSize,
        complexity
      },
      performance: {
        duration: simulatedLatency,
        tokenUsage: {
          inputTokens: estimatedInputTokens,
          outputTokens: estimatedOutputTokens,
          totalTokens: estimatedInputTokens + estimatedOutputTokens
        },
        cost: totalCost,
        memoryUsage: estimatedInputTokens * 100 // Rough estimate
      },
      quality: {
        confidence: simulatedQuality,
        completeness: simulatedQuality * 0.95, // Slightly lower completeness
        relevance: simulatedQuality * 0.98 // High relevance for full context
      },
      result: {
        responseLength: estimatedOutputTokens * 4, // Rough character estimate
        recommendationsCount: Math.ceil(complexity === 'high' ? 8 : complexity === 'medium' ? 5 : 3),
        codeGenerated: true, // Full context LLM likely generates code
        securityIssuesFound: Math.ceil(Math.random() * 5) // Random for simulation
      },
      metadata: {
        model,
        simulated: true,
        contextLimitUtilization: estimatedInputTokens / simulation.maxContextTokens
      }
    };

    this.baselineMetrics.set(baselineMetric.id, baselineMetric);
    return baselineMetric;
  }

  /**
   * Simulate rule-based only approach
   */
  async simulateRuleBasedOnly(request: HybridIntelligenceRequest): Promise<BaselineMetrics> {
    const contextSize = this.calculateContextSize(request);
    const complexity = this.assessComplexity(request);
    
    // Rule-based is fast but lower quality
    const simulatedLatency = 100 + Math.random() * 200; // 100-300ms
    const qualityScore = complexity === 'low' ? 0.7 : complexity === 'medium' ? 0.5 : 0.3;

    const baselineMetric: BaselineMetrics = {
      id: `rule_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      approach: 'rule-based-only',
      request: {
        textLength: request.text.length,
        contextFiles: request.context.files?.length || 0,
        contextSize,
        complexity
      },
      performance: {
        duration: simulatedLatency,
        tokenUsage: {
          inputTokens: 0, // No LLM tokens
          outputTokens: 0,
          totalTokens: 0
        },
        cost: 0, // Free
        memoryUsage: contextSize * 0.1 // Minimal memory usage
      },
      quality: {
        confidence: qualityScore,
        completeness: qualityScore * 0.8, // Lower completeness
        relevance: qualityScore * 0.9 // Decent relevance for simple cases
      },
      result: {
        responseLength: 500 + Math.random() * 1000, // 500-1500 characters
        recommendationsCount: Math.ceil(complexity === 'high' ? 3 : complexity === 'medium' ? 2 : 1),
        codeGenerated: false, // Rule-based doesn't generate code
        securityIssuesFound: Math.ceil(Math.random() * 3) // Limited security detection
      },
      metadata: {
        approach: 'deterministic',
        simulated: true
      }
    };

    this.baselineMetrics.set(baselineMetric.id, baselineMetric);
    return baselineMetric;
  }

  private calculateContextSize(request: HybridIntelligenceRequest): number {
    let size = request.text.length;
    
    if (request.context.files) {
      size += request.context.files.join('').length;
    }
    
    if (request.context.fileContents) {
      for (const content of request.context.fileContents.values()) {
        size += content.length;
      }
    }
    
    return size;
  }

  private assessComplexity(request: HybridIntelligenceRequest): 'low' | 'medium' | 'high' {
    const contextSize = this.calculateContextSize(request);
    const fileCount = request.context.files?.length || 0;
    
    if (contextSize > 50000 || fileCount > 20) return 'high';
    if (contextSize > 10000 || fileCount > 5) return 'medium';
    return 'low';
  }

  private assessCompleteness(response: HybridIntelligenceResponse): number {
    let score = 0.5; // Base score
    
    if (response.recommendations.length > 0) score += 0.2;
    if (response.intent.confidence > 0.7) score += 0.1;
    if (response.domain.confidence > 0.7) score += 0.1;
    if (response.security.risks.length > 0) score += 0.1;
    
    return Math.min(score, 1.0);
  }

  private assessRelevance(response: HybridIntelligenceResponse, request: HybridIntelligenceRequest): number {
    // Simple relevance assessment based on intent matching
    const intentKeywords = request.text.toLowerCase().split(/\s+/);
    const responseText = JSON.stringify(response).toLowerCase();
    
    const matchingKeywords = intentKeywords.filter(keyword => 
      responseText.includes(keyword) && keyword.length > 3
    );
    
    return Math.min(matchingKeywords.length / Math.max(intentKeywords.length, 1), 1.0);
  }

  /**
   * Generate comprehensive comparison report
   */
  async generateComparisonReport(
    startTime: Date,
    endTime: Date,
    includeSimulations: boolean = true
  ): Promise<ComparisonResult> {
    const metricsInRange = Array.from(this.baselineMetrics.values()).filter(
      metric => metric.timestamp >= startTime && metric.timestamp <= endTime
    );

    // Group metrics by approach
    const approaches = {
      hybrid: metricsInRange.filter(m => m.approach === 'hybrid'),
      fullContextLLM: metricsInRange.filter(m => m.approach === 'full-context-llm'),
      ruleBasedOnly: metricsInRange.filter(m => m.approach === 'rule-based-only')
    };

    // If we don't have enough comparison data and simulations are enabled, generate some
    if (includeSimulations && approaches.hybrid.length > 0) {
      // Generate simulations for each hybrid request
      for (const hybridMetric of approaches.hybrid.slice(0, 5)) { // Limit to 5 for performance
        try {
          // Simulate full-context LLM (we'd need to reconstruct the request, this is simplified)
          const mockRequest: HybridIntelligenceRequest = {
            text: 'mock request for simulation',
            context: {
              files: new Array(hybridMetric.request.contextFiles).fill('mock.js')
            },
            options: { allowFallbacks: true }
          };
          
          await this.simulateFullContextLLM(mockRequest, 'gpt-4');
          await this.simulateRuleBasedOnly(mockRequest);
        } catch (error) {
          console.warn('Failed to generate simulation:', error);
        }
      }
      
      // Refresh approaches with new simulations
      const updatedMetrics = Array.from(this.baselineMetrics.values()).filter(
        metric => metric.timestamp >= startTime && metric.timestamp <= endTime
      );
      
      approaches.fullContextLLM = updatedMetrics.filter(m => m.approach === 'full-context-llm');
      approaches.ruleBasedOnly = updatedMetrics.filter(m => m.approach === 'rule-based-only');
    }

    // Calculate comparison metrics
    const comparison = this.calculateComparison(approaches);
    
    // Generate insights
    const insights = this.generateInsights(comparison);

    return {
      timeRange: { start: startTime, end: endTime },
      approaches,
      comparison,
      insights
    };
  }

  private calculateComparison(approaches: {
    hybrid: BaselineMetrics[];
    fullContextLLM: BaselineMetrics[];
    ruleBasedOnly: BaselineMetrics[];
  }) {
    const calculateAverages = (metrics: BaselineMetrics[]) => {
      if (metrics.length === 0) return { duration: 0, cost: 0, tokenUsage: 0, confidence: 0, accuracy: 0, completeness: 0, relevance: 0 };
      
      return {
        duration: metrics.reduce((sum, m) => sum + m.performance.duration, 0) / metrics.length,
        cost: metrics.reduce((sum, m) => sum + m.performance.cost, 0) / metrics.length,
        tokenUsage: metrics.reduce((sum, m) => sum + m.performance.tokenUsage.totalTokens, 0) / metrics.length,
        confidence: metrics.reduce((sum, m) => sum + m.quality.confidence, 0) / metrics.length,
        accuracy: metrics.reduce((sum, m) => sum + (m.quality.accuracy || 0), 0) / metrics.length,
        completeness: metrics.reduce((sum, m) => sum + m.quality.completeness, 0) / metrics.length,
        relevance: metrics.reduce((sum, m) => sum + m.quality.relevance, 0) / metrics.length
      };
    };

    const hybridAvg = calculateAverages(approaches.hybrid);
    const llmAvg = calculateAverages(approaches.fullContextLLM);
    const ruleAvg = calculateAverages(approaches.ruleBasedOnly);

    return {
      performance: {
        averageDuration: {
          hybrid: hybridAvg.duration,
          fullContextLLM: llmAvg.duration,
          ruleBasedOnly: ruleAvg.duration
        },
        averageCost: {
          hybrid: hybridAvg.cost,
          fullContextLLM: llmAvg.cost,
          ruleBasedOnly: ruleAvg.cost
        },
        averageTokenUsage: {
          hybrid: hybridAvg.tokenUsage,
          fullContextLLM: llmAvg.tokenUsage,
          ruleBasedOnly: ruleAvg.tokenUsage
        },
        costEfficiency: {
          hybrid: hybridAvg.cost > 0 ? hybridAvg.confidence / hybridAvg.cost : Infinity,
          fullContextLLM: llmAvg.cost > 0 ? llmAvg.confidence / llmAvg.cost : Infinity,
          ruleBasedOnly: ruleAvg.cost > 0 ? ruleAvg.confidence / ruleAvg.cost : Infinity
        }
      },
      quality: {
        averageConfidence: {
          hybrid: hybridAvg.confidence,
          fullContextLLM: llmAvg.confidence,
          ruleBasedOnly: ruleAvg.confidence
        },
        averageAccuracy: {
          hybrid: hybridAvg.accuracy,
          fullContextLLM: llmAvg.accuracy,
          ruleBasedOnly: ruleAvg.accuracy
        },
        averageCompleteness: {
          hybrid: hybridAvg.completeness,
          fullContextLLM: llmAvg.completeness,
          ruleBasedOnly: ruleAvg.completeness
        },
        averageRelevance: {
          hybrid: hybridAvg.relevance,
          fullContextLLM: llmAvg.relevance,
          ruleBasedOnly: ruleAvg.relevance
        }
      },
      scalability: {
        throughput: {
          hybrid: hybridAvg.duration > 0 ? 60000 / hybridAvg.duration : 0, // operations per minute
          fullContextLLM: llmAvg.duration > 0 ? 60000 / llmAvg.duration : 0,
          ruleBasedOnly: ruleAvg.duration > 0 ? 60000 / ruleAvg.duration : 0
        },
        resourceUsage: {
          hybrid: hybridAvg.duration > 0 ? approaches.hybrid.reduce((sum, m) => sum + m.performance.memoryUsage, 0) / approaches.hybrid.length / hybridAvg.duration : 0,
          fullContextLLM: llmAvg.duration > 0 ? approaches.fullContextLLM.reduce((sum, m) => sum + m.performance.memoryUsage, 0) / approaches.fullContextLLM.length / llmAvg.duration : 0,
          ruleBasedOnly: ruleAvg.duration > 0 ? approaches.ruleBasedOnly.reduce((sum, m) => sum + m.performance.memoryUsage, 0) / approaches.ruleBasedOnly.length / ruleAvg.duration : 0
        },
        costPerOperation: {
          hybrid: hybridAvg.cost,
          fullContextLLM: llmAvg.cost,
          ruleBasedOnly: ruleAvg.cost
        }
      }
    };
  }

  private generateInsights(comparison: any) {
    const approaches = ['hybrid', 'fullContextLLM', 'ruleBasedOnly'];
    
    // Find winner based on cost efficiency
    const costEfficiencies = comparison.performance.costEfficiency;
    const winner = Object.keys(costEfficiencies).reduce((a, b) => 
      costEfficiencies[a] > costEfficiencies[b] ? a : b
    );

    // Calculate savings compared to full-context LLM
    const hybridCost = comparison.performance.averageCost.hybrid;
    const llmCost = comparison.performance.averageCost.fullContextLLM;
    const costSavings = llmCost > 0 ? ((llmCost - hybridCost) / llmCost) * 100 : 0;

    // Calculate performance gain
    const hybridDuration = comparison.performance.averageDuration.hybrid;
    const llmDuration = comparison.performance.averageDuration.fullContextLLM;
    const performanceGain = llmDuration > 0 ? ((llmDuration - hybridDuration) / llmDuration) * 100 : 0;

    // Calculate quality delta
    const hybridQuality = comparison.quality.averageConfidence.hybrid;
    const llmQuality = comparison.quality.averageConfidence.fullContextLLM;
    const qualityDelta = llmQuality > 0 ? ((hybridQuality - llmQuality) / llmQuality) * 100 : 0;

    const recommendations: string[] = [];
    
    if (costSavings > 50) {
      recommendations.push(`Hybrid approach saves ${costSavings.toFixed(1)}% in costs compared to full-context LLM`);
    }
    
    if (performanceGain > 30) {
      recommendations.push(`Hybrid approach is ${performanceGain.toFixed(1)}% faster than full-context LLM`);
    }
    
    if (qualityDelta < -10) {
      recommendations.push(`Consider improving hybrid approach quality (${Math.abs(qualityDelta).toFixed(1)}% lower than full-context LLM)`);
    }
    
    if (comparison.quality.averageConfidence.hybrid < 0.7) {
      recommendations.push('Hybrid approach confidence is below 70%, consider tuning fallback strategies');
    }

    return {
      winner,
      costSavings,
      performanceGain,
      qualityDelta,
      recommendations
    };
  }

  /**
   * Export comparison report
   */
  async exportComparisonReport(
    filePath: string,
    startTime: Date,
    endTime: Date
  ): Promise<void> {
    const report = await this.generateComparisonReport(startTime, endTime);
    
    const exportData = {
      exportTimestamp: new Date(),
      report,
      metadata: {
        totalMetrics: Array.from(this.baselineMetrics.values()).length,
        simulationsIncluded: true
      }
    };
    
    const fs = await import('fs/promises');
    await fs.writeFile(filePath, JSON.stringify(exportData, null, 2));
    console.log(`📊 Exported baseline comparison report to ${filePath}`);
  }

  /**
   * Clear all baseline metrics
   */
  clearMetrics(): void {
    const count = this.baselineMetrics.size;
    this.baselineMetrics.clear();
    console.log(`🗑️ Cleared ${count} baseline metrics`);
    this.emit('metrics-cleared', { count });
  }
}

// Singleton instance
export const baselineComparison = new BaselineComparison();