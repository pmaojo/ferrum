/**
 * Tests for PermaGraph Query Engine
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { GraphQueryBuilder } from '../permagraph-query-engine';
import { RelationshipAnalyzer } from '../relationship-analyzer';
import { PatternScorer } from '../pattern-scorer';
import { PermaGraphQueryService } from '../permagraph-query-service';
import { PermaGraphController } from '../permagraph-controller';

// Mock the logger
jest.mock('../utils/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn()
  }
}));

describe('GraphQueryBuilder', () => {
  let queryBuilder: GraphQueryBuilder;

  beforeEach(() => {
    queryBuilder = new GraphQueryBuilder();
  });

  describe('buildAuthenticationPatternQuery', () => {
    it('should build a basic authentication pattern query', () => {
      const query = queryBuilder.buildAuthenticationPatternQuery('2fa');
      
      expect(query.id).toContain('auth-pattern-2fa');
      expect(query.name).toBe('Authentication Pattern Query - 2fa');
      expect(query.query).toContain('MATCH (p:AuthPattern)');
      expect(query.query).toContain('p.type = $authType');
      expect(query.parameters.authType).toBe('2fa');
      expect(query.category).toBe('authentication');
      expect(query.optimized).toBe(true);
    });

    it('should include framework filter when provided', () => {
      const query = queryBuilder.buildAuthenticationPatternQuery('2fa', 'kthulu');
      
      expect(query.query).toContain('p.framework = $framework');
      expect(query.parameters.framework).toBe('kthulu');
    });

    it('should include security level filter when provided', () => {
      const query = queryBuilder.buildAuthenticationPatternQuery('2fa', undefined, '80');
      
      expect(query.query).toContain('p.securityCompliance.score >= $securityLevel');
      expect(query.parameters.securityLevel).toBe('80');
    });
  });

  describe('buildPaymentServiceQuery', () => {
    it('should build a basic payment service query', () => {
      const query = queryBuilder.buildPaymentServiceQuery('payment_gateway');
      
      expect(query.id).toContain('payment-service-payment_gateway');
      expect(query.name).toBe('Payment Service Pattern Query - payment_gateway');
      expect(query.query).toContain('MATCH (p:ServicePattern)');
      expect(query.query).toContain('p.type = $serviceType');
      expect(query.parameters.serviceType).toBe('payment_gateway');
      expect(query.category).toBe('payment');
    });

    it('should include compliance requirements when provided', () => {
      const query = queryBuilder.buildPaymentServiceQuery('payment_gateway', ['pci-dss', 'gdpr']);
      
      expect(query.query).toContain('ANY(req IN $complianceRequirements');
      expect(query.parameters.complianceRequirements).toEqual(['pci-dss', 'gdpr']);
    });
  });

  describe('buildSecurityRequirementsQuery', () => {
    it('should build a security requirements query', () => {
      const query = queryBuilder.buildSecurityRequirementsQuery('2fa-payment');
      
      expect(query.id).toContain('security-requirements-2fa-payment');
      expect(query.name).toBe('Security Requirements Query - 2fa-payment');
      expect(query.query).toContain('MATCH (f:Feature)-[:REQUIRES_SECURITY]->(r:SecurityRequirement)');
      expect(query.parameters.feature).toBe('2fa-payment');
      expect(query.category).toBe('security');
    });
  });

  describe('cache management', () => {
    it('should cache query results', () => {
      const queryResult = {
        data: [{ id: { value: 'test' } }],
        metadata: {
          executionTime: 100,
          recordCount: 1,
          cached: false,
          queryId: 'test-query'
        }
      };

      queryBuilder.cacheResult('test-key', queryResult, 300000);
      const cached = queryBuilder.getCachedResult('test-key');
      
      expect(cached).toBeTruthy();
      expect(cached?.data).toEqual(queryResult.data);
      expect(cached?.metadata.cached).toBe(true);
    });

    it('should return null for expired cache entries', () => {
      const queryResult = {
        data: [{ id: { value: 'test' } }],
        metadata: {
          executionTime: 100,
          recordCount: 1,
          cached: false,
          queryId: 'test-query'
        }
      };

      queryBuilder.cacheResult('test-key', queryResult, -1); // Expired TTL
      const cached = queryBuilder.getCachedResult('test-key');
      
      expect(cached).toBeNull();
    });
  });

  describe('predefined queries', () => {
    it('should have predefined 2FA patterns query', () => {
      const query = queryBuilder.getPredefinedQuery('find-2fa-patterns');
      
      expect(query).toBeTruthy();
      expect(query?.name).toBe('Find 2FA Implementation Patterns');
      expect(query?.category).toBe('authentication');
    });

    it('should list all predefined queries', () => {
      const queries = queryBuilder.listPredefinedQueries();
      
      expect(queries.length).toBeGreaterThan(0);
      expect(queries.some(q => q.id === 'find-2fa-patterns')).toBe(true);
      expect(queries.some(q => q.id === 'find-payment-integrations')).toBe(true);
    });
  });
});

describe('RelationshipAnalyzer', () => {
  let analyzer: RelationshipAnalyzer;

  beforeEach(() => {
    analyzer = new RelationshipAnalyzer('/test/project');
  });

  describe('detectRequirementLinkages', () => {
    it('should detect linkages between similar requirements', async () => {
      const requirements = [
        'Implement 2FA authentication for payment processing',
        'Add two-factor authentication to user login',
        'Create backup code system for authentication'
      ];

      const linkages = await analyzer.detectRequirementLinkages(requirements, 'payment system');
      
      expect(linkages.length).toBeGreaterThan(0);
      
      const authLinkage = linkages.find(l => 
        l.sourceRequirement.includes('2FA') && l.targetRequirement.includes('two-factor')
      );
      expect(authLinkage).toBeTruthy();
      expect(authLinkage?.similarity).toBeGreaterThan(0.3);
    });

    it('should provide evidence for linkages', async () => {
      const requirements = [
        'Implement TOTP authentication',
        'Add time-based one-time password support'
      ];

      const linkages = await analyzer.detectRequirementLinkages(requirements, 'auth system');
      
      expect(linkages.length).toBeGreaterThan(0);
      const linkage = linkages[0];
      expect(linkage.evidence.length).toBeGreaterThan(0);
      expect(linkage.evidence[0].type).toBe('semantic');
    });
  });

  describe('recognizeArchitecturalPatterns', () => {
    it('should detect hexagonal architecture pattern', async () => {
      const mockGraph = {
        nodes: [
          { id: 'domain/user.ts', name: 'User', type: 'class' as const, layer: 'domain' as const, metadata: { loc: 100, complexity: 5, fanIn: 2, fanOut: 1, stability: 0.8 } },
          { id: 'application/auth-service.ts', name: 'AuthService', type: 'class' as const, layer: 'application' as const, metadata: { loc: 200, complexity: 8, fanIn: 3, fanOut: 2, stability: 0.6 } },
          { id: 'infrastructure/db-adapter.ts', name: 'DbAdapter', type: 'class' as const, layer: 'infrastructure' as const, metadata: { loc: 150, complexity: 6, fanIn: 1, fanOut: 3, stability: 0.4 } }
        ],
        edges: [
          { source: 'application/auth-service.ts', target: 'domain/user.ts', type: 'uses', weight: 1.0, metadata: { frequency: 10, lastModified: new Date(), changeImpact: 0.8 } },
          { source: 'infrastructure/db-adapter.ts', target: 'application/auth-service.ts', type: 'implements', weight: 0.9, metadata: { frequency: 5, lastModified: new Date(), changeImpact: 0.6 } }
        ],
        cycles: [],
        metrics: {
          nodeCount: 3,
          edgeCount: 2,
          density: 0.33,
          averageDegree: 1.33,
          cycleCount: 0,
          maxDepth: 2
        }
      };

      const patterns = await analyzer.recognizeArchitecturalPatterns(mockGraph);
      
      expect(patterns.length).toBeGreaterThan(0);
      const hexPattern = patterns.find(p => p.type === 'hexagonal');
      expect(hexPattern).toBeTruthy();
      expect(hexPattern?.confidence).toBeGreaterThan(0.5);
    });
  });
});

describe('PatternScorer', () => {
  let scorer: PatternScorer;

  beforeEach(() => {
    scorer = new PatternScorer();
  });

  describe('scoreAuthenticationPatterns', () => {
    it('should score authentication patterns correctly', async () => {
      const patterns = [{
        id: 'totp-pattern-1',
        type: '2fa' as const,
        framework: 'kthulu' as const,
        successRate: 0.85,
        securityCompliance: {
          owasp: true,
          pciDss: true,
          gdpr: false,
          sox: false,
          score: 85
        },
        dependencies: ['crypto', 'qrcode'],
        codeTemplates: [
          { id: 'totp-1', path: '/templates/totp.ts', framework: 'kthulu', language: 'typescript', category: 'auth' }
        ],
        historicalUsage: {
          totalImplementations: 150,
          successfulImplementations: 128,
          averageImplementationTime: 240,
          commonIssues: ['clock skew', 'backup codes'],
          lastUsed: new Date('2024-01-15')
        },
        architecturalFit: 0.9
      }];

      const context = {
        projectType: 'web-app',
        framework: 'kthulu',
        securityRequirements: ['2fa', 'audit'],
        complianceStandards: ['owasp', 'pci-dss'],
        teamExperience: 'intermediate' as const,
        timeConstraints: 'moderate' as const,
        budgetConstraints: 'medium' as const
      };

      const scores = await scorer.scoreAuthenticationPatterns(patterns, context);
      
      expect(scores.length).toBe(1);
      const score = scores[0];
      expect(score.patternId).toBe('totp-pattern-1');
      expect(score.overallScore).toBeGreaterThan(0.7);
      expect(score.factors.length).toBeGreaterThan(0);
      
      const successRateFactor = score.factors.find(f => f.name === 'Success Rate');
      expect(successRateFactor).toBeTruthy();
      expect(successRateFactor?.value).toBeGreaterThan(0.8);
    });
  });

  describe('scoreServicePatterns', () => {
    it('should score service patterns correctly', async () => {
      const patterns = [{
        id: 'stripe-gateway-1',
        type: 'payment_gateway' as const,
        framework: 'kthulu',
        integrationPoints: ['webhook', 'api', 'dashboard'],
        securityRequirements: ['tls', 'tokenization', 'pci-compliance'],
        complianceStandards: ['pci-dss', 'gdpr'],
        successRate: 0.92,
        architecturalFit: 0.88
      }];

      const context = {
        projectType: 'e-commerce',
        framework: 'kthulu',
        securityRequirements: ['encryption', 'audit'],
        complianceStandards: ['pci-dss'],
        teamExperience: 'expert' as const,
        timeConstraints: 'flexible' as const,
        budgetConstraints: 'high' as const
      };

      const scores = await scorer.scoreServicePatterns(patterns, context);
      
      expect(scores.length).toBe(1);
      const score = scores[0];
      expect(score.patternId).toBe('stripe-gateway-1');
      expect(score.overallScore).toBeGreaterThan(0.8);
      
      const complianceFactor = score.factors.find(f => f.name === 'Compliance');
      expect(complianceFactor).toBeTruthy();
      expect(complianceFactor?.value).toBe(1.0); // Perfect compliance match
    });
  });
});

describe('PermaGraphQueryService', () => {
  let service: PermaGraphQueryService;
  let mockController: jest.Mocked<PermaGraphController>;

  beforeEach(() => {
    mockController = {
      executeSPARQL: jest.fn()
    } as any;

    const config = {
      projectRoot: '/test/project',
      permagraphController: mockController,
      cacheTTL: 300000,
      enableOptimization: true,
      enableScoring: true
    };

    service = new PermaGraphQueryService(config);
  });

  describe('queryAuthenticationPatterns', () => {
    it('should query and score authentication patterns', async () => {
      const mockSparqlResult = {
        results: {
          bindings: [{
            id: { value: 'totp-1' },
            type: { value: '2fa' },
            framework: { value: 'kthulu' },
            successRate: { value: '0.85' },
            totalUsage: { value: '100' },
            successfulUsage: { value: '85' }
          }]
        }
      };

      mockController.executeSPARQL.mockResolvedValue(mockSparqlResult);

      const request = {
        type: 'authentication' as const,
        parameters: { authType: '2fa', framework: 'kthulu' },
        context: {
          projectType: 'web-app',
          framework: 'kthulu',
          securityRequirements: ['2fa'],
          complianceStandards: ['owasp'],
          teamExperience: 'intermediate' as const,
          timeConstraints: 'moderate' as const,
          budgetConstraints: 'medium' as const
        },
        includeScoring: true,
        includeRelationships: false
      };

      const response = await service.queryAuthenticationPatterns(request);
      
      expect(response.patterns.length).toBe(1);
      expect(response.patterns[0].id).toBe('totp-1');
      expect(response.patterns[0].type).toBe('2fa');
      expect(response.scores).toBeTruthy();
      expect(response.scores!.length).toBe(1);
      expect(response.metadata.patternCount).toBe(1);
      expect(response.metadata.executionTime).toBeGreaterThan(0);
    });
  });

  describe('queryPaymentServicePatterns', () => {
    it('should query payment service patterns', async () => {
      const mockSparqlResult = {
        results: {
          bindings: [{
            id: { value: 'stripe-1' },
            type: { value: 'payment_gateway' },
            framework: { value: 'kthulu' },
            successRate: { value: '0.92' }
          }]
        }
      };

      mockController.executeSPARQL.mockResolvedValue(mockSparqlResult);

      const request = {
        type: 'payment' as const,
        parameters: { serviceType: 'payment_gateway' },
        context: {
          projectType: 'e-commerce',
          framework: 'kthulu',
          securityRequirements: [],
          complianceStandards: ['pci-dss'],
          teamExperience: 'intermediate' as const,
          timeConstraints: 'moderate' as const,
          budgetConstraints: 'medium' as const
        },
        includeScoring: false,
        includeRelationships: false
      };

      const response = await service.queryPaymentServicePatterns(request);
      
      expect(response.patterns.length).toBe(1);
      expect(response.patterns[0].id).toBe('stripe-1');
      expect(response.patterns[0].type).toBe('payment_gateway');
      expect(response.scores).toBeUndefined();
    });
  });

  describe('getComprehensivePatternAnalysis', () => {
    it('should perform comprehensive analysis', async () => {
      const mockSparqlResult = {
        results: {
          bindings: [{
            id: { value: 'test-1' },
            type: { value: '2fa' },
            framework: { value: 'kthulu' },
            successRate: { value: '0.85' }
          }]
        }
      };

      mockController.executeSPARQL.mockResolvedValue(mockSparqlResult);

      const context = {
        projectType: 'web-app',
        framework: 'kthulu',
        securityRequirements: ['2fa'],
        complianceStandards: ['owasp'],
        teamExperience: 'intermediate' as const,
        timeConstraints: 'moderate' as const,
        budgetConstraints: 'medium' as const
      };

      const result = await service.getComprehensivePatternAnalysis(
        '2fa',
        'payment_gateway',
        ['/test/file1.ts', '/test/file2.ts'],
        context
      );

      expect(result.authPatterns).toBeTruthy();
      expect(result.servicePatterns).toBeTruthy();
      expect(result.dependencies).toBeTruthy();
      expect(result.recommendations).toBeTruthy();
      expect(Array.isArray(result.recommendations)).toBe(true);
    });
  });

  describe('cache management', () => {
    it('should provide cache statistics', () => {
      const stats = service.getStatistics();
      
      expect(stats.queryCache).toBeTruthy();
      expect(stats.patternScorer).toBeTruthy();
      expect(typeof stats.queryCache.size).toBe('number');
    });

    it('should clear caches', () => {
      service.clearCaches();
      const stats = service.getStatistics();
      
      expect(stats.queryCache.size).toBe(0);
    });
  });
});