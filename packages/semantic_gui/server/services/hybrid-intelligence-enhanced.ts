/**
 * Enhanced Hybrid Intelligence Service
 * 
 * Integrates health monitoring, fallback mechanisms, rule-based analysis,
 * and local knowledge caching into a unified intelligent system.
 */

import { EventEmitter } from 'events';
import client from 'prom-client';

import { healthMonitor, ServiceHealth } from './health-monitor';
import { fallbackService, FallbackResult, ServiceOperation } from './fallback-service';
import { ruleBasedAnalyzer, IntentClassification, DomainDetection, SecurityAssessment } from './rule-based-analyzer';
import { localKnowledgeCache, KnowledgePattern } from './local-knowledge-cache';
import {
  createPermaGraphKnowledgeClient,
  KnowledgeQueryPayload,
  KnowledgeQueryResult,
  PermaGraphKnowledgeClient,
} from './permagraph-knowledge-client';

interface EnhancedHybridIntelligenceOptions {
  knowledgeClient?: PermaGraphKnowledgeClient;
  autoStart?: boolean;
}

interface HybridMetricsState {
  totalRequests: number;
  successfulResponses: number;
  failedResponses: number;
  fallbackResponses: number;
  cacheHits: number;
  totalLatencyMs: number;
}

interface HybridMetricsRecorders {
  requestCounter: client.Counter<'status'>;
  fallbackCounter: client.Counter<string>;
  cacheHitCounter: client.Counter<string>;
  latencyHistogram: client.Histogram<'status'>;
}

function getOrCreateCounter<T extends string = string>(
  name: string,
  help: string,
  labelNames: T[] = []
): client.Counter<T> {
  const existing = client.register.getSingleMetric(name) as client.Counter<T> | undefined;
  if (existing) {
    return existing;
  }

  return new client.Counter<T>({
    name,
    help,
    labelNames,
  });
}

function getOrCreateHistogram<T extends string = string>(
  name: string,
  help: string,
  labelNames: T[] = []
): client.Histogram<T> {
  const existing = client.register.getSingleMetric(name) as client.Histogram<T> | undefined;
  if (existing) {
    return existing;
  }

  return new client.Histogram<T>({
    name,
    help,
    labelNames,
    buckets: [0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10],
  });
}

function createMetricsRecorders(): HybridMetricsRecorders {
  return {
    requestCounter: getOrCreateCounter('enhanced_hybrid_requests_total', 'Total hybrid intelligence requests', ['status']),
    fallbackCounter: getOrCreateCounter('enhanced_hybrid_fallback_total', 'Total requests resolved via fallback'),
    cacheHitCounter: getOrCreateCounter('enhanced_hybrid_cache_hits_total', 'Total cache hits during hybrid processing'),
    latencyHistogram: getOrCreateHistogram(
      'enhanced_hybrid_request_duration_seconds',
      'Hybrid intelligence request latency in seconds',
      ['status']
    ),
  };
}

export interface HybridIntelligenceRequest {
  text: string;
  context: {
    projectPath?: string;
    files?: string[];
    fileContents?: Map<string, string>;
    userPreferences?: Record<string, any>;
  };
  options: {
    enableStreaming?: boolean;
    requireHighConfidence?: boolean;
    allowFallbacks?: boolean;
    cacheResults?: boolean;
  };
}

export interface HybridIntelligenceResponse {
  success: boolean;
  intent: IntentClassification;
  domain: DomainDetection;
  security: SecurityAssessment;
  knowledgePatterns: KnowledgePattern[];
  recommendations: string[];
  confidence: number;
  servicePath: string[];
  fallbacksUsed: boolean;
  metadata: {
    processingTime: number;
    servicesUsed: string[];
    cacheHits: number;
    errors: string[];
  };
}

export interface ProcessingStep {
  step: string;
  status: 'started' | 'completed' | 'failed';
  service: string;
  confidence?: number;
  duration?: number;
  error?: string;
}

export class EnhancedHybridIntelligence extends EventEmitter {
  private isInitialized = false;
  private processingQueue: Map<string, HybridIntelligenceRequest> = new Map();
  private readonly knowledgeClient: PermaGraphKnowledgeClient;
  private readonly metricsRecorders: HybridMetricsRecorders;
  private metricsState: HybridMetricsState = {
    totalRequests: 0,
    successfulResponses: 0,
    failedResponses: 0,
    fallbackResponses: 0,
    cacheHits: 0,
    totalLatencyMs: 0,
  };
  private initializationPromise: Promise<void> | null = null;

  constructor(options: EnhancedHybridIntelligenceOptions = {}) {
    super();
    this.knowledgeClient = options.knowledgeClient ?? createPermaGraphKnowledgeClient();
    this.metricsRecorders = createMetricsRecorders();

    if (options.autoStart ?? true) {
      void this.start();
    }
  }

  async start(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    if (!this.initializationPromise) {
      this.initializationPromise = this.initialize();
    }

    await this.initializationPromise;
  }

  private async initialize(): Promise<void> {
    try {
      console.log('🚀 Initializing Enhanced Hybrid Intelligence System...');

      // Start health monitoring
      healthMonitor.start();

      // Set up event listeners
      this.setupEventListeners();

      this.isInitialized = true;
      console.log('✅ Enhanced Hybrid Intelligence System initialized');
      this.emit('system-ready');

    } catch (error) {
      console.error('❌ Failed to initialize Enhanced Hybrid Intelligence System:', error);
      this.emit('system-error', { error, phase: 'initialization' });
    } finally {
      this.initializationPromise = null;
    }
  }

  private setupEventListeners(): void {
    // Health monitoring events
    healthMonitor.on('service-unhealthy', ({ serviceName, health, error }) => {
      console.log(`⚠️ Service ${serviceName} is unhealthy, activating fallbacks`);
      this.emit('service-degraded', { serviceName, health, error });
    });

    healthMonitor.on('service-healthy', ({ serviceName, health }) => {
      console.log(`✅ Service ${serviceName} recovered`);
      this.emit('service-recovered', { serviceName, health });
    });

    // Fallback service events
    fallbackService.on('operation-success', (data) => {
      this.emit('processing-step', {
        step: 'fallback-operation',
        status: 'completed',
        service: data.serviceName,
        confidence: data.confidence,
        duration: data.responseTime
      });
    });

    fallbackService.on('operation-failure', (data) => {
      this.emit('processing-step', {
        step: 'fallback-operation',
        status: 'failed',
        service: data.serviceName,
        error: data.error.message,
        duration: data.responseTime
      });
    });

    // Cache events
    localKnowledgeCache.on('cache-hit', ({ key }) => {
      this.emit('cache-event', { type: 'hit', key });
    });

    localKnowledgeCache.on('cache-miss', ({ key }) => {
      this.emit('cache-event', { type: 'miss', key });
    });
  }

  /**
   * Process a hybrid intelligence request with full fallback support
   */
  async processRequest(request: HybridIntelligenceRequest): Promise<HybridIntelligenceResponse> {
    if (!this.isInitialized) {
      throw new Error('Enhanced Hybrid Intelligence System not initialized');
    }

    this.metricsState.totalRequests++;
    const startTime = Date.now();
    const stopLatencyTimer = this.metricsRecorders.latencyHistogram.startTimer();
    const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    console.log(`🔍 Processing hybrid intelligence request: ${requestId}`);
    this.emit('request-started', { requestId, request });

    const metadata = {
      processingTime: 0,
      servicesUsed: [] as string[],
      cacheHits: 0,
      errors: [] as string[]
    };

    let servicePath: string[] = [];
    let fallbacksUsed = false;
    let fallbackUsedInRequest = false;
    let cacheHitsForRequest = 0;

    try {
      // Step 1: Intent Classification
      this.emitProcessingStep('intent-classification', 'started', 'rule-based-analyzer');
      
      const intent = await this.classifyIntent(request.text);
      servicePath.push('rule-based-analyzer');
      metadata.servicesUsed.push('rule-based-analyzer');
      
      this.emitProcessingStep('intent-classification', 'completed', 'rule-based-analyzer', intent.confidence);

      // Step 2: Domain Detection
      this.emitProcessingStep('domain-detection', 'started', 'rule-based-analyzer');
      
      const domain = await this.detectDomain(request.context);
      servicePath.push('rule-based-analyzer');
      
      this.emitProcessingStep('domain-detection', 'completed', 'rule-based-analyzer', domain.confidence);

      // Step 3: Security Assessment
      this.emitProcessingStep('security-assessment', 'started', 'rule-based-analyzer');
      
      const security = await this.assessSecurity(request.context);
      servicePath.push('rule-based-analyzer');
      
      this.emitProcessingStep('security-assessment', 'completed', 'rule-based-analyzer', security.confidence);

      // Step 4: Knowledge Pattern Retrieval
      this.emitProcessingStep('knowledge-retrieval', 'started', 'permagraph');
      
      const knowledgeResult = await this.retrieveKnowledgePatterns(intent, domain, request.options);
      servicePath.push(knowledgeResult.serviceName);
      metadata.servicesUsed.push(knowledgeResult.serviceName);

      if (knowledgeResult.isFallback) {
        fallbacksUsed = true;
        fallbackUsedInRequest = true;
      }

      if (knowledgeResult.serviceName === 'local-cache') {
        metadata.cacheHits++;
        cacheHitsForRequest++;
      }

      this.emitProcessingStep('knowledge-retrieval', 'completed', knowledgeResult.serviceName, knowledgeResult.confidence);

      // Step 5: Generate Recommendations
      this.emitProcessingStep('recommendation-generation', 'started', 'hybrid-intelligence');
      
      const recommendations = await this.generateRecommendations(
        intent, domain, security, knowledgeResult.data || []
      );
      
      this.emitProcessingStep('recommendation-generation', 'completed', 'hybrid-intelligence', 1.0);

      // Calculate overall confidence
      const overallConfidence = this.calculateOverallConfidence([
        intent.confidence,
        domain.confidence,
        security.confidence,
        knowledgeResult.confidence
      ]);

      // Prepare response
      metadata.processingTime = Date.now() - startTime;

      const durationMs = metadata.processingTime;
      this.metricsState.totalLatencyMs += durationMs;
      this.metricsState.successfulResponses++;
      this.metricsRecorders.requestCounter.labels('success').inc();
      stopLatencyTimer({ status: 'success' });

      if (fallbackUsedInRequest) {
        this.metricsState.fallbackResponses++;
        this.metricsRecorders.fallbackCounter.inc();
      }

      if (cacheHitsForRequest > 0) {
        this.metricsState.cacheHits += cacheHitsForRequest;
        this.metricsRecorders.cacheHitCounter.inc(cacheHitsForRequest);
      }

      const response: HybridIntelligenceResponse = {
        success: true,
        intent,
        domain,
        security,
        knowledgePatterns: knowledgeResult.data || [],
        recommendations,
        confidence: overallConfidence,
        servicePath,
        fallbacksUsed,
        metadata
      };

      console.log(`✅ Request ${requestId} completed in ${metadata.processingTime}ms (confidence: ${overallConfidence.toFixed(2)})`);
      this.emit('request-completed', { requestId, response });

      return response;

    } catch (error) {
      const errorMessage = (error as Error).message;
      metadata.errors.push(errorMessage);
      metadata.processingTime = Date.now() - startTime;

      const durationMs = metadata.processingTime;
      this.metricsState.totalLatencyMs += durationMs;
      this.metricsState.failedResponses++;
      this.metricsRecorders.requestCounter.labels('failure').inc();
      stopLatencyTimer({ status: 'failure' });

      if (fallbackUsedInRequest) {
        this.metricsState.fallbackResponses++;
        this.metricsRecorders.fallbackCounter.inc();
      }

      if (cacheHitsForRequest > 0) {
        this.metricsState.cacheHits += cacheHitsForRequest;
        this.metricsRecorders.cacheHitCounter.inc(cacheHitsForRequest);
      }

      console.error(`❌ Request ${requestId} failed:`, error);
      this.emit('request-failed', { requestId, error, metadata });

      // Return partial results if available
      return {
        success: false,
        intent: { intent: 'unknown', confidence: 0, keywords: [], patterns: [], metadata: {} },
        domain: { domain: 'unknown', confidence: 0, indicators: [], framework: null, architecture: null },
        security: { level: 'medium', confidence: 0, risks: [], recommendations: [], complianceIssues: [] },
        knowledgePatterns: [],
        recommendations: ['System error occurred. Please try again.'],
        confidence: 0,
        servicePath,
        fallbacksUsed,
        metadata
      };
    }
  }

  private async classifyIntent(text: string): Promise<IntentClassification> {
    // Use rule-based analyzer for intent classification
    return ruleBasedAnalyzer.classifyIntent(text);
  }

  private async detectDomain(context: HybridIntelligenceRequest['context']): Promise<DomainDetection> {
    const { projectPath = '', files = [] } = context;
    return ruleBasedAnalyzer.detectDomain(projectPath, files);
  }

  private async assessSecurity(context: HybridIntelligenceRequest['context']): Promise<SecurityAssessment> {
    const { files = [], fileContents = new Map() } = context;
    return ruleBasedAnalyzer.assessSecurity(files, fileContents);
  }

  private async retrieveKnowledgePatterns(
    intent: IntentClassification,
    domain: DomainDetection,
    options: HybridIntelligenceRequest['options']
  ): Promise<FallbackResult<KnowledgePattern[]>> {
    const operations: ServiceOperation<KnowledgePattern[]>[] = [
      {
        serviceName: 'permagraph',
        operation: () => this.queryPermaGraph(intent, domain)
      },
      {
        serviceName: 'local-cache',
        operation: () => this.queryLocalCache(intent, domain)
      }
    ];

    return fallbackService.executeWithFallback('knowledge-retrieval', operations, {
      requireSuccess: false,
      maxRetries: 2
    });
  }

  private async queryPermaGraph(intent: IntentClassification, domain: DomainDetection): Promise<KnowledgePattern[]> {
    if (!healthMonitor.isServiceAvailable('permagraph')) {
      throw new Error('PermaGraph service is not available');
    }

    const start = Date.now();
    const payload = this.buildKnowledgeQueryPayload(intent, domain);

    try {
      const response = await this.knowledgeClient.queryKnowledge(payload);
      const patterns = this.mapKnowledgeResults(intent, domain, response.results);

      if (patterns.length === 0) {
        throw new Error('PermaGraph returned no knowledge patterns for the requested context');
      }

      healthMonitor.recordServiceSuccess('permagraph', Date.now() - start, {
        resultCount: patterns.length,
      });

      return patterns;
    } catch (error) {
      const duration = Date.now() - start;
      const normalizedError = error instanceof Error ? error : new Error('PermaGraph query failed');
      healthMonitor.recordServiceFailure('permagraph', normalizedError, duration);
      throw normalizedError;
    }
  }

  private buildKnowledgeQueryPayload(
    intent: IntentClassification,
    domain: DomainDetection
  ): KnowledgeQueryPayload {
    const questionParts = [
      `What knowledge patterns support the ${intent.intent} intent`,
      domain.domain ? `within the ${domain.domain} domain` : '',
      domain.framework ? `for the ${domain.framework} framework` : '',
    ].filter(Boolean);

    const filters = this.sanitizeFilters({
      intent: intent.intent,
      domain: domain.domain,
      framework: domain.framework ?? undefined,
      architecture: domain.architecture ?? undefined,
      keywords: intent.keywords?.length ? intent.keywords : undefined,
    });

    const context = this.sanitizeFilters({
      intent: intent.intent,
      intentConfidence: intent.confidence,
      domain: domain.domain,
      domainConfidence: domain.confidence,
      framework: domain.framework ?? undefined,
      architecture: domain.architecture ?? undefined,
    });

    return {
      question: `${questionParts.join(' ')}?`.trim(),
      kg_id: 'default',
      tenant_id: 'default',
      max_results: 5,
      query_opts: {
        type: 'pattern_search',
        filters,
        context,
      },
    } satisfies KnowledgeQueryPayload;
  }

  private sanitizeFilters(filters: Record<string, unknown>): Record<string, unknown> {
    return Object.fromEntries(
      Object.entries(filters).filter(([, value]) => {
        if (value === undefined || value === null) {
          return false;
        }

        if (typeof value === 'string') {
          return value.trim().length > 0;
        }

        if (Array.isArray(value)) {
          return value.length > 0;
        }

        return true;
      })
    );
  }

  private mapKnowledgeResults(
    intent: IntentClassification,
    domain: DomainDetection,
    results: KnowledgeQueryResult[]
  ): KnowledgePattern[] {
    return results.map((result, index) => {
      const metadata = (result.metadata ?? {}) as Record<string, unknown>;
      const content = (result.content ?? {}) as Record<string, unknown>;
      const rawId =
        (metadata.patternId as string) ||
        (metadata.pattern_id as string) ||
        (content.id as string) ||
        result.queryId ||
        result.title ||
        `permagraph-pattern-${index}`;
      const id = String(rawId);
      const type = this.resolvePatternType(result, content, metadata);
      const framework =
        (metadata.framework as string) ||
        (content.framework as string) ||
        domain.framework ||
        'generic';
      const successRate = this.extractNumber(metadata.successRate ?? content.successRate, 0);
      const usageCount = Math.max(
        0,
        Math.floor(this.extractNumber(metadata.usageCount ?? content.usageCount, 0))
      );
      const lastUpdated = this.extractDate(metadata.lastUpdated ?? content.lastUpdated);
      const relationships = this.extractStringArray(
        metadata.relatedPatterns ?? metadata.relationships ?? []
      );
      const patternPayload = Object.keys(content).length
        ? content
        : {
            title: result.title,
            description: result.description,
          };

      return {
        id,
        type,
        framework,
        domain: domain.domain,
        pattern: patternPayload,
        successRate,
        usageCount,
        lastUpdated,
        relationships,
        metadata: {
          ...metadata,
          source: result.source,
          relevanceScore: result.relevanceScore,
          intent: intent.intent,
          domain: domain.domain,
        },
      } satisfies KnowledgePattern;
    });
  }

  private resolvePatternType(
    result: KnowledgeQueryResult,
    content: Record<string, unknown>,
    metadata: Record<string, unknown>
  ): KnowledgePattern['type'] {
    const rawType =
      (metadata.patternType as string) ||
      (metadata.type as string) ||
      (content.type as string) ||
      result.resultType ||
      '';

    const normalized = rawType.toLowerCase();

    if (normalized.includes('auth') || normalized.includes('security')) {
      return 'auth-pattern';
    }

    if (normalized.includes('service') || normalized.includes('integration')) {
      return 'service-pattern';
    }

    if (normalized.includes('requirement')) {
      return 'requirement-chain';
    }

    return 'historical-case';
  }

  private extractNumber(value: unknown, fallback = 0): number {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }

    if (typeof value === 'string') {
      const parsed = Number(value);
      if (!Number.isNaN(parsed)) {
        return parsed;
      }
    }

    return fallback;
  }

  private extractDate(value: unknown): Date {
    if (value instanceof Date) {
      return value;
    }

    if (typeof value === 'string' || typeof value === 'number') {
      const parsed = new Date(value);
      if (!Number.isNaN(parsed.getTime())) {
        return parsed;
      }
    }

    return new Date();
  }

  private extractStringArray(value: unknown): string[] {
    if (Array.isArray(value)) {
      return value.map(item => String(item));
    }

    if (typeof value === 'string' && value.length > 0) {
      return [value];
    }

    return [];
  }

  private async queryLocalCache(intent: IntentClassification, domain: DomainDetection): Promise<KnowledgePattern[]> {
    // Query local cache for knowledge patterns
    const patterns = await localKnowledgeCache.getKnowledgePatterns(
      intent.intent,
      domain.framework || undefined,
      domain.domain
    );

    if (patterns.length === 0) {
      throw new Error('No cached patterns found');
    }

    return patterns;
  }

  private async generateRecommendations(
    intent: IntentClassification,
    domain: DomainDetection,
    security: SecurityAssessment,
    patterns: KnowledgePattern[]
  ): Promise<string[]> {
    const recommendations: string[] = [];

    // Intent-based recommendations
    if (intent.intent === 'add-2fa') {
      recommendations.push('Implement TOTP-based two-factor authentication');
      recommendations.push('Generate QR codes for mobile app setup');
      recommendations.push('Create backup code system for account recovery');
    }

    // Security-based recommendations
    if (security.level === 'high' || security.level === 'critical') {
      recommendations.push('Address critical security vulnerabilities before implementing new features');
      recommendations.push('Implement comprehensive input validation');
      recommendations.push('Enable security headers and HTTPS');
    }

    // Framework-specific recommendations
    if (domain.framework) {
      recommendations.push(`Use ${domain.framework}-specific authentication libraries`);
      recommendations.push(`Follow ${domain.framework} security best practices`);
    }

    // Pattern-based recommendations
    for (const pattern of patterns) {
      if (pattern.successRate > 0.8) {
        recommendations.push(`Consider using ${pattern.id} pattern (${Math.round(pattern.successRate * 100)}% success rate)`);
      }
    }

    return recommendations;
  }

  private calculateOverallConfidence(confidences: number[]): number {
    if (confidences.length === 0) return 0;
    
    // Use weighted average with higher weight for higher confidences
    const weights = confidences.map(c => Math.pow(c, 2));
    const weightedSum = confidences.reduce((sum, conf, i) => sum + conf * weights[i], 0);
    const totalWeight = weights.reduce((sum, w) => sum + w, 0);
    
    return totalWeight > 0 ? weightedSum / totalWeight : 0;
  }

  private emitProcessingStep(step: string, status: 'started' | 'completed' | 'failed', service: string, confidence?: number, error?: string): void {
    const processingStep: ProcessingStep = {
      step,
      status,
      service,
      confidence,
      error
    };

    this.emit('processing-step', processingStep);
  }

  /**
   * Get system health status
   */
  getSystemHealth(): {
    status: 'healthy' | 'degraded' | 'unhealthy';
    services: ServiceHealth[];
    fallbacksActive: boolean;
    cacheStats: any;
  } {
    const systemHealth = healthMonitor.getSystemHealth();
    const cacheStats = localKnowledgeCache.getStats();
    
    // Check if any fallbacks are currently active
    const fallbacksActive = systemHealth.services.some(service => 
      !healthMonitor.isServiceHealthy(service.name)
    );

    return {
      status: systemHealth.status,
      services: systemHealth.services,
      fallbacksActive,
      cacheStats
    };
  }

  /**
   * Force health check for all services
   */
  async performHealthCheck(): Promise<void> {
    const services = healthMonitor.getAllServicesHealth();
    
    for (const service of services) {
      await healthMonitor.forceHealthCheck(service.name);
    }
  }

  /**
   * Get processing statistics
   */
  getProcessingStats(): {
    totalRequests: number;
    successRate: number;
    averageProcessingTime: number;
    fallbackUsageRate: number;
    cacheHitRate: number;
  } {
    const {
      totalRequests,
      successfulResponses,
      failedResponses,
      fallbackResponses,
      cacheHits,
      totalLatencyMs,
    } = this.metricsState;

    const processedRequests = successfulResponses + failedResponses;
    const averageProcessingTime = processedRequests > 0 ? totalLatencyMs / processedRequests : 0;
    const successRate = processedRequests > 0 ? successfulResponses / processedRequests : 0;
    const fallbackUsageRate = totalRequests > 0 ? fallbackResponses / totalRequests : 0;
    const cacheHitRate = totalRequests > 0 ? cacheHits / totalRequests : 0;

    return {
      totalRequests,
      successRate,
      averageProcessingTime,
      fallbackUsageRate,
      cacheHitRate,
    };
  }

  /**
   * Shutdown the system gracefully
   */
  async shutdown(): Promise<void> {
    console.log('🛑 Shutting down Enhanced Hybrid Intelligence System...');

    healthMonitor.stop();
    await localKnowledgeCache.shutdown();

    this.isInitialized = false;
    this.initializationPromise = null;

    console.log('✅ Enhanced Hybrid Intelligence System shutdown complete');
    this.emit('system-shutdown');
  }
}

// Singleton instance
export const enhancedHybridIntelligence = new EnhancedHybridIntelligence();