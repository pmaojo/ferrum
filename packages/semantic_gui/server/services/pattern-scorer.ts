/**
 * Pattern Scorer
 * 
 * Implements pattern scoring based on historical success rates and architectural fit.
 * Provides comprehensive scoring algorithms for authentication patterns, service patterns,
 * and requirement chains with multiple scoring factors and weighting.
 */

import { performance } from 'node:perf_hooks';
import { logger } from '../utils/logger';
import type {
  AuthPattern,
  ServicePattern,
  RequirementChain,
  PatternScore,
  ScoreFactor,
  HistoricalUsage,
  ComplianceLevel
} from './permagraph-query-engine';

export interface ScoringContext {
  projectType: string;
  framework: string;
  securityRequirements: string[];
  complianceStandards: string[];
  teamExperience: 'beginner' | 'intermediate' | 'expert';
  timeConstraints: 'tight' | 'moderate' | 'flexible';
  budgetConstraints: 'low' | 'medium' | 'high';
}

export interface ScoringWeights {
  successRate: number;
  architecturalFit: number;
  compliance: number;
  historical: number;
  complexity: number;
  maintenance: number;
  performance: number;
  security: number;
}

export interface PatternMetrics {
  complexity: number;
  maintainability: number;
  performance: number;
  security: number;
  testability: number;
  scalability: number;
}

export interface ArchitecturalFitAnalysis {
  frameworkCompatibility: number;
  patternConsistency: number;
  integrationComplexity: number;
  futureProofing: number;
  teamFamiliarity: number;
}

/**
 * Pattern Scorer - Main class for scoring patterns based on multiple criteria
 */
export class PatternScorer {
  private defaultWeights: ScoringWeights = {
    successRate: 0.25,
    architecturalFit: 0.20,
    compliance: 0.15,
    historical: 0.15,
    complexity: 0.10,
    maintenance: 0.05,
    performance: 0.05,
    security: 0.05
  };

  private scoringCache: Map<string, PatternScore> = new Map();

  constructor(private customWeights?: Partial<ScoringWeights>) {
    if (customWeights) {
      this.defaultWeights = { ...this.defaultWeights, ...customWeights };
    }
  }

  /**
   * Score authentication patterns based on multiple criteria
   */
  async scoreAuthenticationPatterns(
    patterns: AuthPattern[],
    context: ScoringContext
  ): Promise<PatternScore[]> {
    const startTime = performance.now();
    const scores: PatternScore[] = [];

    try {
      for (const pattern of patterns) {
        const cacheKey = this.generateCacheKey('auth', pattern.id, context);
        const cachedScore = this.scoringCache.get(cacheKey);

        if (cachedScore) {
          scores.push(cachedScore);
          continue;
        }

        const score = await this.scoreAuthenticationPattern(pattern, context);
        scores.push(score);
        this.scoringCache.set(cacheKey, score);
      }

      // Sort by overall score descending
      scores.sort((a, b) => b.overallScore - a.overallScore);

      const endTime = performance.now();
      logger.info('Authentication pattern scoring completed', {
        patternCount: patterns.length,
        duration: endTime - startTime
      });

      return scores;
    } catch (error) {
      logger.error('Error scoring authentication patterns', error as Error);
      throw error;
    }
  }

  /**
   * Score service patterns based on multiple criteria
   */
  async scoreServicePatterns(
    patterns: ServicePattern[],
    context: ScoringContext
  ): Promise<PatternScore[]> {
    const startTime = performance.now();
    const scores: PatternScore[] = [];

    try {
      for (const pattern of patterns) {
        const cacheKey = this.generateCacheKey('service', pattern.id, context);
        const cachedScore = this.scoringCache.get(cacheKey);

        if (cachedScore) {
          scores.push(cachedScore);
          continue;
        }

        const score = await this.scoreServicePattern(pattern, context);
        scores.push(score);
        this.scoringCache.set(cacheKey, score);
      }

      // Sort by overall score descending
      scores.sort((a, b) => b.overallScore - a.overallScore);

      const endTime = performance.now();
      logger.info('Service pattern scoring completed', {
        patternCount: patterns.length,
        duration: endTime - startTime
      });

      return scores;
    } catch (error) {
      logger.error('Error scoring service patterns', error as Error);
      throw error;
    }
  }

  /**
   * Score requirement chains based on completeness and compliance
   */
  async scoreRequirementChains(
    chains: RequirementChain[],
    context: ScoringContext
  ): Promise<PatternScore[]> {
    const startTime = performance.now();
    const scores: PatternScore[] = [];

    try {
      for (const chain of chains) {
        const cacheKey = this.generateCacheKey('requirement', chain.id, context);
        const cachedScore = this.scoringCache.get(cacheKey);

        if (cachedScore) {
          scores.push(cachedScore);
          continue;
        }

        const score = await this.scoreRequirementChain(chain, context);
        scores.push(score);
        this.scoringCache.set(cacheKey, score);
      }

      // Sort by overall score descending
      scores.sort((a, b) => b.overallScore - a.overallScore);

      const endTime = performance.now();
      logger.info('Requirement chain scoring completed', {
        chainCount: chains.length,
        duration: endTime - startTime
      });

      return scores;
    } catch (error) {
      logger.error('Error scoring requirement chains', error as Error);
      throw error;
    }
  }

  /**
   * Score individual authentication pattern
   */
  private async scoreAuthenticationPattern(
    pattern: AuthPattern,
    context: ScoringContext
  ): Promise<PatternScore> {
    const factors: ScoreFactor[] = [];

    // Success Rate Score
    const successRateScore = this.calculateSuccessRateScore(pattern.successRate);
    factors.push({
      name: 'Success Rate',
      weight: this.defaultWeights.successRate,
      value: successRateScore,
      description: `Historical success rate: ${(pattern.successRate * 100).toFixed(1)}%`
    });

    // Architectural Fit Score
    const architecturalFitScore = await this.calculateArchitecturalFitScore(pattern, context);
    factors.push({
      name: 'Architectural Fit',
      weight: this.defaultWeights.architecturalFit,
      value: architecturalFitScore,
      description: `Framework compatibility and pattern consistency`
    });

    // Compliance Score
    const complianceScore = this.calculateComplianceScore(pattern.securityCompliance, context);
    factors.push({
      name: 'Compliance',
      weight: this.defaultWeights.compliance,
      value: complianceScore,
      description: `Security and regulatory compliance`
    });

    // Historical Score
    const historicalScore = this.calculateHistoricalScore(pattern.historicalUsage);
    factors.push({
      name: 'Historical Usage',
      weight: this.defaultWeights.historical,
      value: historicalScore,
      description: `Based on usage patterns and community adoption`
    });

    // Complexity Score
    const complexityScore = this.calculateComplexityScore(pattern);
    factors.push({
      name: 'Implementation Complexity',
      weight: this.defaultWeights.complexity,
      value: complexityScore,
      description: `Ease of implementation and integration`
    });

    // Security Score
    const securityScore = this.calculateSecurityScore(pattern, context);
    factors.push({
      name: 'Security Strength',
      weight: this.defaultWeights.security,
      value: securityScore,
      description: `Security robustness and threat protection`
    });

    // Calculate overall score
    const overallScore = factors.reduce((sum, factor) =>
      sum + (factor.value * factor.weight), 0
    );

    return {
      patternId: pattern.id,
      overallScore,
      successRateScore,
      architecturalFitScore,
      complianceScore,
      historicalScore,
      factors
    };
  }

  /**
   * Score individual service pattern
   */
  private async scoreServicePattern(
    pattern: ServicePattern,
    context: ScoringContext
  ): Promise<PatternScore> {
    const factors: ScoreFactor[] = [];

    // Success Rate Score
    const successRateScore = this.calculateSuccessRateScore(pattern.successRate);
    factors.push({
      name: 'Success Rate',
      weight: this.defaultWeights.successRate,
      value: successRateScore,
      description: `Historical success rate: ${(pattern.successRate * 100).toFixed(1)}%`
    });

    // Architectural Fit Score
    const architecturalFitScore = pattern.architecturalFit;
    factors.push({
      name: 'Architectural Fit',
      weight: this.defaultWeights.architecturalFit,
      value: architecturalFitScore,
      description: `Framework compatibility and integration ease`
    });

    // Compliance Score
    const complianceScore = this.calculateServiceComplianceScore(pattern, context);
    factors.push({
      name: 'Compliance',
      weight: this.defaultWeights.compliance,
      value: complianceScore,
      description: `Regulatory and industry standard compliance`
    });

    // Integration Complexity Score
    const integrationScore = this.calculateIntegrationComplexityScore(pattern);
    factors.push({
      name: 'Integration Complexity',
      weight: this.defaultWeights.complexity,
      value: integrationScore,
      description: `Ease of integration with existing systems`
    });

    // Performance Score
    const performanceScore = this.calculatePerformanceScore(pattern);
    factors.push({
      name: 'Performance',
      weight: this.defaultWeights.performance,
      value: performanceScore,
      description: `Expected performance characteristics`
    });

    // Maintenance Score
    const maintenanceScore = this.calculateMaintenanceScore(pattern);
    factors.push({
      name: 'Maintainability',
      weight: this.defaultWeights.maintenance,
      value: maintenanceScore,
      description: `Long-term maintenance and support requirements`
    });

    // Calculate overall score
    const overallScore = factors.reduce((sum, factor) =>
      sum + (factor.value * factor.weight), 0
    );

    return {
      patternId: pattern.id,
      overallScore,
      successRateScore,
      architecturalFitScore,
      complianceScore,
      historicalScore: 0, // Not applicable for service patterns
      factors
    };
  }

  /**
   * Score individual requirement chain
   */
  private async scoreRequirementChain(
    chain: RequirementChain,
    context: ScoringContext
  ): Promise<PatternScore> {
    const factors: ScoreFactor[] = [];

    // Completeness Score
    const completenessScore = this.calculateCompletenessScore(chain);
    factors.push({
      name: 'Completeness',
      weight: 0.3,
      value: completenessScore,
      description: `Coverage of all necessary requirements`
    });

    // Compliance Score
    const complianceScore = this.calculateChainComplianceScore(chain, context);
    factors.push({
      name: 'Compliance Coverage',
      weight: 0.25,
      value: complianceScore,
      description: `Compliance with regulatory standards`
    });

    // Dependency Clarity Score
    const dependencyScore = this.calculateDependencyClarityScore(chain);
    factors.push({
      name: 'Dependency Clarity',
      weight: 0.2,
      value: dependencyScore,
      description: `Clear and well-defined dependencies`
    });

    // Validation Coverage Score
    const validationScore = this.calculateValidationCoverageScore(chain);
    factors.push({
      name: 'Validation Coverage',
      weight: 0.15,
      value: validationScore,
      description: `Automated validation and testing coverage`
    });

    // Traceability Score
    const traceabilityScore = this.calculateTraceabilityScore(chain);
    factors.push({
      name: 'Traceability',
      weight: 0.1,
      value: traceabilityScore,
      description: `End-to-end requirement traceability`
    });

    // Calculate overall score
    const overallScore = factors.reduce((sum, factor) =>
      sum + (factor.value * factor.weight), 0
    );

    return {
      patternId: chain.id,
      overallScore,
      successRateScore: 0, // Not applicable
      architecturalFitScore: 0, // Not applicable
      complianceScore,
      historicalScore: 0, // Not applicable
      factors
    };
  }

  // Scoring calculation methods

  private calculateSuccessRateScore(successRate: number): number {
    // Convert success rate to a score with diminishing returns
    return Math.min(1.0, successRate * 1.2);
  }

  private async calculateArchitecturalFitScore(
    pattern: AuthPattern,
    context: ScoringContext
  ): Promise<number> {
    let score = 0;

    // Framework compatibility
    if (pattern.framework === context.framework || pattern.framework === 'generic') {
      score += 0.4;
    } else {
      score += 0.1; // Partial compatibility
    }

    // Dependency compatibility
    const dependencyScore = this.calculateDependencyCompatibility(pattern.dependencies, context);
    score += dependencyScore * 0.3;

    // Team experience factor
    const experienceMultiplier = this.getExperienceMultiplier(context.teamExperience);
    score *= experienceMultiplier;

    // Time constraints factor
    const timeMultiplier = this.getTimeConstraintMultiplier(context.timeConstraints);
    score *= timeMultiplier;

    return Math.min(1.0, score);
  }

  private calculateComplianceScore(
    compliance: ComplianceLevel,
    context: ScoringContext
  ): number {
    let score = 0;
    let totalRequirements = 0;

    // Check each compliance standard
    if (context.complianceStandards.includes('owasp')) {
      totalRequirements++;
      if (compliance.owasp) score++;
    }

    if (context.complianceStandards.includes('pci-dss')) {
      totalRequirements++;
      if (compliance.pciDss) score++;
    }

    if (context.complianceStandards.includes('gdpr')) {
      totalRequirements++;
      if (compliance.gdpr) score++;
    }

    if (context.complianceStandards.includes('sox')) {
      totalRequirements++;
      if (compliance.sox) score++;
    }

    // If no specific standards required, use overall compliance score
    if (totalRequirements === 0) {
      return compliance.score / 100;
    }

    return totalRequirements > 0 ? score / totalRequirements : 0;
  }

  private calculateHistoricalScore(usage: HistoricalUsage): number {
    let score = 0;

    // Usage frequency score
    if (usage.totalImplementations > 100) score += 0.4;
    else if (usage.totalImplementations > 50) score += 0.3;
    else if (usage.totalImplementations > 10) score += 0.2;
    else score += 0.1;

    // Recency score
    const daysSinceLastUsed = (Date.now() - usage.lastUsed.getTime()) / (1000 * 60 * 60 * 24);
    if (daysSinceLastUsed < 30) score += 0.3;
    else if (daysSinceLastUsed < 90) score += 0.2;
    else if (daysSinceLastUsed < 180) score += 0.1;

    // Issue frequency penalty
    const issueRate = usage.commonIssues.length / Math.max(1, usage.totalImplementations);
    score *= (1 - Math.min(0.5, issueRate));

    return Math.min(1.0, score);
  }

  private calculateComplexityScore(pattern: AuthPattern): number {
    let complexity = 0;

    // Dependency complexity
    complexity += pattern.dependencies.length * 0.1;

    // Template complexity (inverse score - simpler is better)
    complexity += pattern.codeTemplates.length * 0.05;

    // Convert to score (lower complexity = higher score)
    return Math.max(0, 1.0 - Math.min(1.0, complexity));
  }

  private calculateSecurityScore(pattern: AuthPattern, context: ScoringContext): number {
    let score = 0;

    // Base security score from compliance
    score += pattern.securityCompliance.score / 100 * 0.5;

    // Pattern-specific security features
    switch (pattern.type) {
      case '2fa':
      case 'totp':
        score += 0.4; // High security
        break;
      case 'oauth':
        score += 0.3; // Good security
        break;
      case 'jwt':
        score += 0.2; // Moderate security
        break;
      case 'session':
        score += 0.1; // Basic security
        break;
      default:
        score += 0.1;
    }

    // Security requirement alignment
    const securityAlignment = this.calculateSecurityAlignment(pattern, context.securityRequirements);
    score += securityAlignment * 0.1;

    return Math.min(1.0, score);
  }

  private calculateServiceComplianceScore(pattern: ServicePattern, context: ScoringContext): number {
    const requiredStandards = context.complianceStandards;
    const patternStandards = pattern.complianceStandards;

    if (requiredStandards.length === 0) return 1.0;

    const matchedStandards = requiredStandards.filter(std =>
      patternStandards.includes(std)
    );

    return matchedStandards.length / requiredStandards.length;
  }

  private calculateIntegrationComplexityScore(pattern: ServicePattern): number {
    // Fewer integration points = higher score (simpler integration)
    const integrationComplexity = pattern.integrationPoints.length;
    return Math.max(0.1, 1.0 - (integrationComplexity * 0.1));
  }

  private calculatePerformanceScore(pattern: ServicePattern): number {
    // This would typically be based on benchmarks or historical data
    // For now, return a default score based on pattern type
    const performanceMap: Record<string, number> = {
      'payment_gateway': 0.8,
      'payment_processor': 0.9,
      'billing': 0.7,
      'subscription': 0.8
    };

    return performanceMap[pattern.type] || 0.7;
  }

  private calculateMaintenanceScore(pattern: ServicePattern): number {
    // Fewer security requirements typically means easier maintenance
    const securityComplexity = pattern.securityRequirements.length;
    return Math.max(0.3, 1.0 - (securityComplexity * 0.05));
  }

  private calculateCompletenessScore(chain: RequirementChain): number {
    // Score based on the richness of the requirement chain
    let score = 0;

    // Base score for having linked requirements
    if (chain.linkedRequirements.length > 0) score += 0.4;

    // Score for dependencies
    if (chain.dependencies.length > 0) score += 0.3;

    // Score for compliance mapping
    if (chain.complianceMapping.length > 0) score += 0.2;

    // Score for validation rules
    if (chain.validationRules.length > 0) score += 0.1;

    return Math.min(1.0, score);
  }

  private calculateChainComplianceScore(chain: RequirementChain, context: ScoringContext): number {
    const requiredStandards = context.complianceStandards;
    if (requiredStandards.length === 0) return 1.0;

    const coveredStandards = new Set(
      chain.complianceMapping.map(mapping => mapping.standard)
    );

    const matchedStandards = requiredStandards.filter(std =>
      coveredStandards.has(std)
    );

    return matchedStandards.length / requiredStandards.length;
  }

  private calculateDependencyClarityScore(chain: RequirementChain): number {
    if (chain.dependencies.length === 0) return 0.5; // Neutral score for no dependencies

    // Score based on dependency strength and bidirectionality
    const totalStrength = chain.dependencies.reduce((sum, dep) => sum + dep.strength, 0);
    const averageStrength = totalStrength / chain.dependencies.length;

    const bidirectionalCount = chain.dependencies.filter(dep => dep.bidirectional).length;
    const bidirectionalRatio = bidirectionalCount / chain.dependencies.length;

    return (averageStrength * 0.7) + (bidirectionalRatio * 0.3);
  }

  private calculateValidationCoverageScore(chain: RequirementChain): number {
    if (chain.validationRules.length === 0) return 0;

    const automatedRules = chain.validationRules.filter(rule => rule.automated).length;
    const automationRatio = automatedRules / chain.validationRules.length;

    // Higher score for more automated validation
    return automationRatio;
  }

  private calculateTraceabilityScore(chain: RequirementChain): number {
    // Score based on the connectivity of the requirement chain
    const linkageRatio = chain.linkedRequirements.length / Math.max(1, chain.dependencies.length);
    return Math.min(1.0, linkageRatio);
  }

  // Helper methods

  private calculateDependencyCompatibility(dependencies: string[], context: ScoringContext): number {
    // This would check against known compatible dependencies for the framework
    // For now, return a default score
    return 0.8;
  }

  private getExperienceMultiplier(experience: string): number {
    const multipliers = {
      'beginner': 0.8,
      'intermediate': 1.0,
      'expert': 1.2
    };
    return multipliers[experience as keyof typeof multipliers] || 1.0;
  }

  private getTimeConstraintMultiplier(constraints: string): number {
    const multipliers = {
      'tight': 0.8,   // Favor simpler patterns
      'moderate': 1.0,
      'flexible': 1.1  // Can handle more complex patterns
    };
    return multipliers[constraints as keyof typeof multipliers] || 1.0;
  }

  private calculateSecurityAlignment(pattern: AuthPattern, requirements: string[]): number {
    // Check how well the pattern aligns with security requirements
    let alignmentScore = 0;

    requirements.forEach(req => {
      if (pattern.type.includes(req.toLowerCase()) ||
        pattern.securityCompliance.score > 80) {
        alignmentScore += 1;
      }
    });

    return requirements.length > 0 ? alignmentScore / requirements.length : 0;
  }

  private generateCacheKey(type: string, patternId: string, context: ScoringContext): string {
    const contextHash = JSON.stringify({
      projectType: context.projectType,
      framework: context.framework,
      securityRequirements: context.securityRequirements.sort(),
      complianceStandards: context.complianceStandards.sort()
    });

    return `${type}-${patternId}-${Buffer.from(contextHash).toString('base64').slice(0, 16)}`;
  }

  /**
   * Clear scoring cache
   */
  clearCache(): void {
    this.scoringCache.clear();
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): { size: number; hitRate: number } {
    return {
      size: this.scoringCache.size,
      hitRate: 0 // Would need to track hits/misses to calculate
    };
  }
}