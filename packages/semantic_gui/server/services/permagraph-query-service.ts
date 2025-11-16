/**
 * PermaGraph Query Service
 * 
 * Main service that integrates the GraphQueryBuilder, RelationshipAnalyzer, and PatternScorer
 * to provide comprehensive PermaGraph querying capabilities for authentication and payment patterns.
 */

import { performance } from 'node:perf_hooks';
import { logger } from '../utils/logger';
import { PermaGraphController } from './permagraph-controller';
import { GraphQueryBuilder, type CypherQuery, type QueryResult, type AuthPattern, type ServicePattern, type RequirementChain } from './permagraph-query-engine';
import { RelationshipAnalyzer, type CodeDependency, type RequirementLinkage, type ArchitecturalPattern, type DependencyGraph } from './relationship-analyzer';
import { PatternScorer, type PatternScore, type ScoringContext } from './pattern-scorer';

export interface QueryEngineConfig {
  projectRoot: string;
  permagraphController: PermaGraphController;
  cacheTTL: number;
  enableOptimization: boolean;
  enableScoring: boolean;
}

export interface PatternQueryRequest {
  type: 'authentication' | 'payment' | 'security';
  parameters: Record<string, any>;
  context: ScoringContext;
  includeScoring: boolean;
  includeRelationships: boolean;
}

export interface PatternQueryResponse {
  patterns: (AuthPattern | ServicePattern)[];
  scores?: PatternScore[];
  relationships?: CodeDependency[];
  architecturalPatterns?: ArchitecturalPattern[];
  requirementLinkages?: RequirementLinkage[];
  metadata: QueryMetadata;
}

export interface QueryMetadata {
  executionTime: number;
  queryCount: number;
  cacheHits: number;
  patternCount: number;
  confidence: number;
}

export interface DependencyAnalysisRequest {
  filePaths: string[];
  includeArchitecturalPatterns: boolean;
  includeRequirementLinkages: boolean;
  requirements?: string[];
  context?: string;
}

export interface DependencyAnalysisResponse {
  dependencies: CodeDependency[];
  dependencyGraph: DependencyGraph;
  architecturalPatterns?: ArchitecturalPattern[];
  requirementLinkages?: RequirementLinkage[];
  metadata: AnalysisMetadata;
}

export interface AnalysisMetadata {
  executionTime: number;
  fileCount: number;
  dependencyCount: number;
  cycleCount: number;
  patternCount: number;
}

/**
 * PermaGraph Query Service - Main orchestrator for pattern queries and analysis
 */
export class PermaGraphQueryService {
  private queryBuilder: GraphQueryBuilder;
  private relationshipAnalyzer: RelationshipAnalyzer;
  private patternScorer: PatternScorer;
  private queryCache: Map<string, any> = new Map();

  constructor(private config: QueryEngineConfig) {
    this.queryBuilder = new GraphQueryBuilder();
    this.relationshipAnalyzer = new RelationshipAnalyzer(config.projectRoot);
    this.patternScorer = new PatternScorer();
  }

  /**
   * Query authentication patterns with optional scoring and relationship analysis
   */
  async queryAuthenticationPatterns(request: PatternQueryRequest): Promise<PatternQueryResponse> {
    const startTime = performance.now();
    
    try {
      logger.info('Querying authentication patterns', {
        type: request.type,
        parameters: request.parameters,
        includeScoring: request.includeScoring,
        includeRelationships: request.includeRelationships
      });

      // Build and execute Cypher query
      const cypherQuery = this.buildAuthenticationQuery(request);
      const queryResult = await this.executeQuery(cypherQuery);
      
      // Transform results to AuthPattern objects
      const patterns = this.transformToAuthPatterns(queryResult.data);

      // Optional scoring
      let scores: PatternScore[] | undefined;
      if (request.includeScoring && patterns.length > 0) {
        scores = await this.patternScorer.scoreAuthenticationPatterns(patterns, request.context);
      }

      // Optional relationship analysis
      let relationships: CodeDependency[] | undefined;
      let architecturalPatterns: ArchitecturalPattern[] | undefined;
      if (request.includeRelationships) {
        const relationshipData = await this.analyzePatternRelationships(patterns);
        relationships = relationshipData.dependencies;
        architecturalPatterns = relationshipData.architecturalPatterns;
      }

      const endTime = performance.now();
      const executionTime = endTime - startTime;

      logger.info('Authentication pattern query completed', {
        patternCount: patterns.length,
        executionTime,
        includeScoring: request.includeScoring,
        includeRelationships: request.includeRelationships
      });

      return {
        patterns,
        scores,
        relationships,
        architecturalPatterns,
        metadata: {
          executionTime,
          queryCount: 1,
          cacheHits: 0, // Would track actual cache hits
          patternCount: patterns.length,
          confidence: this.calculateOverallConfidence(patterns, scores)
        }
      };
    } catch (error) {
      logger.error('Error querying authentication patterns', error as Error);
      throw error;
    }
  }

  /**
   * Query payment service patterns with optional scoring and relationship analysis
   */
  async queryPaymentServicePatterns(request: PatternQueryRequest): Promise<PatternQueryResponse> {
    const startTime = performance.now();
    
    try {
      logger.info('Querying payment service patterns', {
        type: request.type,
        parameters: request.parameters,
        includeScoring: request.includeScoring,
        includeRelationships: request.includeRelationships
      });

      // Build and execute Cypher query
      const cypherQuery = this.buildPaymentServiceQuery(request);
      const queryResult = await this.executeQuery(cypherQuery);
      
      // Transform results to ServicePattern objects
      const patterns = this.transformToServicePatterns(queryResult.data);

      // Optional scoring
      let scores: PatternScore[] | undefined;
      if (request.includeScoring && patterns.length > 0) {
        scores = await this.patternScorer.scoreServicePatterns(patterns, request.context);
      }

      // Optional relationship analysis
      let relationships: CodeDependency[] | undefined;
      let architecturalPatterns: ArchitecturalPattern[] | undefined;
      if (request.includeRelationships) {
        const relationshipData = await this.analyzePatternRelationships(patterns);
        relationships = relationshipData.dependencies;
        architecturalPatterns = relationshipData.architecturalPatterns;
      }

      const endTime = performance.now();
      const executionTime = endTime - startTime;

      logger.info('Payment service pattern query completed', {
        patternCount: patterns.length,
        executionTime,
        includeScoring: request.includeScoring,
        includeRelationships: request.includeRelationships
      });

      return {
        patterns,
        scores,
        relationships,
        architecturalPatterns,
        metadata: {
          executionTime,
          queryCount: 1,
          cacheHits: 0,
          patternCount: patterns.length,
          confidence: this.calculateOverallConfidence(patterns, scores)
        }
      };
    } catch (error) {
      logger.error('Error querying payment service patterns', error as Error);
      throw error;
    }
  }

  /**
   * Query security requirements with compliance mapping
   */
  async querySecurityRequirements(
    feature: string,
    complianceStandards: string[] = [],
    context: ScoringContext
  ): Promise<RequirementChain[]> {
    const startTime = performance.now();
    
    try {
      logger.info('Querying security requirements', {
        feature,
        complianceStandards,
        context: context.framework
      });

      // Build and execute security requirements query
      const cypherQuery = this.queryBuilder.buildSecurityRequirementsQuery(feature, complianceStandards);
      const queryResult = await this.executeQuery(cypherQuery);
      
      // Transform results to RequirementChain objects
      const requirementChains = this.transformToRequirementChains(queryResult.data);

      // Score requirement chains
      const scores = await this.patternScorer.scoreRequirementChains(requirementChains, context);

      // Sort by score
      requirementChains.sort((a, b) => {
        const scoreA = scores.find(s => s.patternId === a.id)?.overallScore || 0;
        const scoreB = scores.find(s => s.patternId === b.id)?.overallScore || 0;
        return scoreB - scoreA;
      });

      const endTime = performance.now();
      logger.info('Security requirements query completed', {
        requirementCount: requirementChains.length,
        executionTime: endTime - startTime
      });

      return requirementChains;
    } catch (error) {
      logger.error('Error querying security requirements', error as Error);
      throw error;
    }
  }

  /**
   * Analyze code dependencies and architectural patterns
   */
  async analyzeDependencies(request: DependencyAnalysisRequest): Promise<DependencyAnalysisResponse> {
    const startTime = performance.now();
    
    try {
      logger.info('Analyzing code dependencies', {
        fileCount: request.filePaths.length,
        includeArchitecturalPatterns: request.includeArchitecturalPatterns,
        includeRequirementLinkages: request.includeRequirementLinkages
      });

      // Analyze code dependencies
      const dependencies = await this.relationshipAnalyzer.analyzeCodeDependencies(request.filePaths);
      
      // Build dependency graph
      const dependencyGraph = this.buildDependencyGraph(dependencies);

      // Optional architectural pattern recognition
      let architecturalPatterns: ArchitecturalPattern[] | undefined;
      if (request.includeArchitecturalPatterns) {
        architecturalPatterns = await this.relationshipAnalyzer.recognizeArchitecturalPatterns(dependencyGraph);
      }

      // Optional requirement linkage detection
      let requirementLinkages: RequirementLinkage[] | undefined;
      if (request.includeRequirementLinkages && request.requirements && request.context) {
        requirementLinkages = await this.relationshipAnalyzer.detectRequirementLinkages(
          request.requirements,
          request.context
        );
      }

      const endTime = performance.now();
      const executionTime = endTime - startTime;

      logger.info('Dependency analysis completed', {
        dependencyCount: dependencies.length,
        cycleCount: dependencyGraph.cycles.length,
        patternCount: architecturalPatterns?.length || 0,
        executionTime
      });

      return {
        dependencies,
        dependencyGraph,
        architecturalPatterns,
        requirementLinkages,
        metadata: {
          executionTime,
          fileCount: request.filePaths.length,
          dependencyCount: dependencies.length,
          cycleCount: dependencyGraph.cycles.length,
          patternCount: architecturalPatterns?.length || 0
        }
      };
    } catch (error) {
      logger.error('Error analyzing dependencies', error as Error);
      throw error;
    }
  }

  /**
   * Get comprehensive pattern analysis combining queries and relationships
   */
  async getComprehensivePatternAnalysis(
    authType: string,
    serviceType: string,
    filePaths: string[],
    context: ScoringContext
  ): Promise<{
    authPatterns: PatternQueryResponse;
    servicePatterns: PatternQueryResponse;
    dependencies: DependencyAnalysisResponse;
    recommendations: string[];
  }> {
    const startTime = performance.now();
    
    try {
      logger.info('Starting comprehensive pattern analysis', {
        authType,
        serviceType,
        fileCount: filePaths.length,
        framework: context.framework
      });

      // Execute all analyses in parallel
      const [authPatterns, servicePatterns, dependencies] = await Promise.all([
        this.queryAuthenticationPatterns({
          type: 'authentication',
          parameters: { authType, framework: context.framework },
          context,
          includeScoring: true,
          includeRelationships: true
        }),
        this.queryPaymentServicePatterns({
          type: 'payment',
          parameters: { serviceType, framework: context.framework },
          context,
          includeScoring: true,
          includeRelationships: true
        }),
        this.analyzeDependencies({
          filePaths,
          includeArchitecturalPatterns: true,
          includeRequirementLinkages: false
        })
      ]);

      // Generate recommendations based on analysis
      const recommendations = this.generateRecommendations(authPatterns, servicePatterns, dependencies, context);

      const endTime = performance.now();
      logger.info('Comprehensive pattern analysis completed', {
        authPatternCount: authPatterns.patterns.length,
        servicePatternCount: servicePatterns.patterns.length,
        dependencyCount: dependencies.dependencies.length,
        recommendationCount: recommendations.length,
        executionTime: endTime - startTime
      });

      return {
        authPatterns,
        servicePatterns,
        dependencies,
        recommendations
      };
    } catch (error) {
      logger.error('Error in comprehensive pattern analysis', error as Error);
      throw error;
    }
  }

  // Private helper methods

  private buildAuthenticationQuery(request: PatternQueryRequest): CypherQuery {
    const { authType, framework, securityLevel } = request.parameters;
    return this.queryBuilder.buildAuthenticationPatternQuery(authType, framework, securityLevel);
  }

  private buildPaymentServiceQuery(request: PatternQueryRequest): CypherQuery {
    const { serviceType, complianceRequirements } = request.parameters;
    return this.queryBuilder.buildPaymentServiceQuery(serviceType, complianceRequirements);
  }

  private async executeQuery(cypherQuery: CypherQuery): Promise<QueryResult> {
    const cacheKey = this.generateQueryCacheKey(cypherQuery);
    
    // Check cache first
    if (this.config.cacheTTL > 0) {
      const cached = this.queryCache.get(cacheKey);
      if (cached && (Date.now() - cached.timestamp) < this.config.cacheTTL) {
        return cached.result;
      }
    }

    // Execute query through PermaGraph controller
    const startTime = performance.now();
    const result = await this.config.permagraphController.executeSPARQL(
      cypherQuery.query,
      cypherQuery.parameters
    );
    const executionTime = performance.now() - startTime;

    const queryResult: QueryResult = {
      data: result.results?.bindings || [],
      metadata: {
        executionTime,
        recordCount: result.results?.bindings?.length || 0,
        cached: false,
        queryId: cypherQuery.id
      }
    };

    // Cache result
    if (this.config.cacheTTL > 0) {
      this.queryCache.set(cacheKey, {
        result: queryResult,
        timestamp: Date.now()
      });
    }

    return queryResult;
  }

  private transformToAuthPatterns(data: any[]): AuthPattern[] {
    return data.map(record => ({
      id: record.id?.value || '',
      type: record.type?.value as any || '2fa',
      framework: record.framework?.value as any || 'generic',
      successRate: parseFloat(record.successRate?.value || '0'),
      securityCompliance: {
        owasp: true,
        pciDss: false,
        gdpr: false,
        sox: false,
        score: 80
      },
      dependencies: record.dependencies || [],
      codeTemplates: record.templates || [],
      historicalUsage: {
        totalImplementations: parseInt(record.totalUsage?.value || '0'),
        successfulImplementations: parseInt(record.successfulUsage?.value || '0'),
        averageImplementationTime: 0,
        commonIssues: [],
        lastUsed: new Date()
      },
      architecturalFit: 0.8
    }));
  }

  private transformToServicePatterns(data: any[]): ServicePattern[] {
    return data.map(record => ({
      id: record.id?.value || '',
      type: record.type?.value as any || 'payment_gateway',
      framework: record.framework?.value || 'generic',
      integrationPoints: record.integrationPoints || [],
      securityRequirements: record.securityRequirements || [],
      complianceStandards: record.complianceStandards || [],
      successRate: parseFloat(record.successRate?.value || '0'),
      architecturalFit: 0.8
    }));
  }

  private transformToRequirementChains(data: any[]): RequirementChain[] {
    return data.map(record => ({
      id: record.id?.value || '',
      sourceRequirement: record.description?.value || '',
      linkedRequirements: [],
      dependencies: [],
      complianceMapping: [],
      validationRules: record.validationRules || []
    }));
  }

  private async analyzePatternRelationships(patterns: (AuthPattern | ServicePattern)[]): Promise<{
    dependencies: CodeDependency[];
    architecturalPatterns: ArchitecturalPattern[];
  }> {
    // This would analyze the relationships between patterns
    // For now, return empty arrays
    return {
      dependencies: [],
      architecturalPatterns: []
    };
  }

  private buildDependencyGraph(dependencies: CodeDependency[]): DependencyGraph {
    const nodeMap = new Map<string, any>();
    const edges: any[] = [];

    // Build nodes from dependencies
    dependencies.forEach(dep => {
      if (!nodeMap.has(dep.source)) {
        nodeMap.set(dep.source, {
          id: dep.source,
          name: dep.source.split('/').pop() || dep.source,
          type: 'module',
          layer: dep.metadata.category as any,
          framework: dep.metadata.framework,
          metadata: {
            loc: 0,
            complexity: 0,
            fanIn: 0,
            fanOut: 0,
            stability: 0
          }
        });
      }

      if (!nodeMap.has(dep.target)) {
        nodeMap.set(dep.target, {
          id: dep.target,
          name: dep.target.split('/').pop() || dep.target,
          type: 'module',
          layer: dep.metadata.category as any,
          framework: dep.metadata.framework,
          metadata: {
            loc: 0,
            complexity: 0,
            fanIn: 0,
            fanOut: 0,
            stability: 0
          }
        });
      }

      edges.push({
        source: dep.source,
        target: dep.target,
        type: dep.type,
        weight: dep.strength,
        metadata: {
          frequency: 1,
          lastModified: new Date(),
          changeImpact: dep.strength
        }
      });
    });

    const nodes = Array.from(nodeMap.values());
    const cycles: any[] = []; // Would be populated by cycle detection

    return {
      nodes,
      edges,
      cycles,
      metrics: {
        nodeCount: nodes.length,
        edgeCount: edges.length,
        density: edges.length / (nodes.length * (nodes.length - 1)),
        averageDegree: edges.length / nodes.length,
        cycleCount: cycles.length,
        maxDepth: 0
      }
    };
  }

  private calculateOverallConfidence(
    patterns: (AuthPattern | ServicePattern)[],
    scores?: PatternScore[]
  ): number {
    if (!scores || scores.length === 0) {
      return patterns.length > 0 ? 0.7 : 0;
    }

    const averageScore = scores.reduce((sum, score) => sum + score.overallScore, 0) / scores.length;
    return averageScore;
  }

  private generateRecommendations(
    authPatterns: PatternQueryResponse,
    servicePatterns: PatternQueryResponse,
    dependencies: DependencyAnalysisResponse,
    context: ScoringContext
  ): string[] {
    const recommendations: string[] = [];

    // Authentication recommendations
    if (authPatterns.scores && authPatterns.scores.length > 0) {
      const topAuthPattern = authPatterns.scores[0];
      if (topAuthPattern.overallScore > 0.8) {
        recommendations.push(`Recommended authentication pattern: ${topAuthPattern.patternId} (score: ${(topAuthPattern.overallScore * 100).toFixed(1)}%)`);
      }
    }

    // Service pattern recommendations
    if (servicePatterns.scores && servicePatterns.scores.length > 0) {
      const topServicePattern = servicePatterns.scores[0];
      if (topServicePattern.overallScore > 0.8) {
        recommendations.push(`Recommended service pattern: ${topServicePattern.patternId} (score: ${(topServicePattern.overallScore * 100).toFixed(1)}%)`);
      }
    }

    // Dependency recommendations
    if (dependencies.dependencyGraph.cycles.length > 0) {
      recommendations.push(`Found ${dependencies.dependencyGraph.cycles.length} circular dependencies that should be resolved`);
    }

    // Architectural pattern recommendations
    if (dependencies.architecturalPatterns && dependencies.architecturalPatterns.length > 0) {
      const bestPattern = dependencies.architecturalPatterns.reduce((best, current) => 
        current.confidence > best.confidence ? current : best
      );
      recommendations.push(`Detected ${bestPattern.name} pattern with ${(bestPattern.confidence * 100).toFixed(1)}% confidence`);
    }

    return recommendations;
  }

  private generateQueryCacheKey(cypherQuery: CypherQuery): string {
    const keyData = {
      query: cypherQuery.query,
      parameters: cypherQuery.parameters
    };
    return Buffer.from(JSON.stringify(keyData)).toString('base64');
  }

  /**
   * Clear all caches
   */
  clearCaches(): void {
    this.queryCache.clear();
    this.patternScorer.clearCache();
  }

  /**
   * Get service statistics
   */
  getStatistics(): {
    queryCache: { size: number };
    patternScorer: { size: number; hitRate: number };
  } {
    return {
      queryCache: { size: this.queryCache.size },
      patternScorer: this.patternScorer.getCacheStats()
    };
  }
}