import type {
  KnowledgeQueryResult,
  PermaGraphKnowledgeClient,
} from '../permagraph-knowledge-client';

import { EnhancedHybridIntelligence } from '../hybrid-intelligence-enhanced';
import { localKnowledgeCache, KnowledgePattern } from '../local-knowledge-cache';

function createRequest() {
  return {
    text: 'add 2FA to my payment service',
    context: {
      projectPath: '/test/project',
      files: ['package.json', 'src/auth.js', 'src/payment.js'],
      fileContents: new Map<string, string>([
        ['package.json', '{"name": "test-app", "dependencies": {"express": "^4.0.0"}}'],
        ['src/auth.js', 'const express = require("express");'],
        ['src/payment.js', 'const stripe = require("stripe");'],
      ]),
    },
    options: {
      enableStreaming: false,
      requireHighConfidence: false,
      allowFallbacks: true,
      cacheResults: true,
    },
  };
}

describe('Enhanced Hybrid Intelligence Service', () => {
  let service: EnhancedHybridIntelligence;
  let knowledgeClient: jest.Mocked<PermaGraphKnowledgeClient>;

  beforeAll(async () => {
    knowledgeClient = {
      queryKnowledge: jest.fn(),
      getHealth: jest.fn(),
    } as unknown as jest.Mocked<PermaGraphKnowledgeClient>;

    knowledgeClient.getHealth.mockResolvedValue({ ok: true, status: 'healthy' });
    knowledgeClient.queryKnowledge.mockResolvedValue({ results: [], metadata: {} });

    service = new EnhancedHybridIntelligence({
      knowledgeClient,
      autoStart: false,
    });

    await service.start();
  });

  afterAll(async () => {
    await service.shutdown();
  });

  beforeEach(() => {
    knowledgeClient.queryKnowledge.mockReset();
    knowledgeClient.getHealth.mockReset();
    knowledgeClient.getHealth.mockResolvedValue({ ok: true, status: 'healthy' });
  });

  it('uses the PermaGraph adapter and maps results to knowledge patterns', async () => {
    const permagraphResult: KnowledgeQueryResult = {
      queryId: 'query-1',
      resultType: 'auth-pattern',
      title: 'Time-based OTP',
      description: 'Implements TOTP authentication',
      content: {
        id: 'pattern-123',
        framework: 'nestjs',
        successRate: 0.91,
        usageCount: 42,
        relatedPatterns: ['recovery-codes'],
      },
      relevanceScore: 0.82,
      source: 'library',
      metadata: {
        patternType: 'auth-pattern',
        successRate: 0.91,
        usageCount: 42,
        lastUpdated: new Date().toISOString(),
      },
    };

    knowledgeClient.queryKnowledge.mockResolvedValue({
      results: [permagraphResult],
      metadata: { requestId: 'abc' },
    });

    const response = await service.processRequest(createRequest());

    expect(knowledgeClient.queryKnowledge).toHaveBeenCalledTimes(1);
    const [payload] = knowledgeClient.queryKnowledge.mock.calls[0];
    expect(payload.question).toContain('add-2fa');
    expect(payload.query_opts?.filters).toMatchObject({ intent: 'add-2fa' });
    expect(response.success).toBe(true);
    expect(response.knowledgePatterns).toHaveLength(1);

    const pattern = response.knowledgePatterns[0];
    expect(pattern.id).toBe('pattern-123');
    expect(pattern.type).toBe('auth-pattern');
    expect(pattern.framework).toBe('nestjs');
    expect(pattern.successRate).toBeCloseTo(0.91, 5);

    const stats = service.getProcessingStats();
    expect(stats.totalRequests).toBe(1);
    expect(stats.successRate).toBeCloseTo(1, 5);
    expect(stats.fallbackUsageRate).toBe(0);
  });

  it('falls back to cached knowledge when PermaGraph fails and records metrics', async () => {
    knowledgeClient.queryKnowledge.mockRejectedValue(new Error('PermaGraph unavailable'));

    const cachedPattern: KnowledgePattern = {
      id: 'cached-pattern',
      type: 'auth-pattern',
      framework: 'generic',
      domain: 'security',
      pattern: { description: 'Cached TOTP guidance' },
      successRate: 0.75,
      usageCount: 18,
      lastUpdated: new Date(),
      relationships: ['audit-trails'],
      metadata: {},
    };

    await localKnowledgeCache.storeKnowledgePattern(cachedPattern);

    const response = await service.processRequest(createRequest());

    expect(response.success).toBe(true);
    expect(response.fallbacksUsed).toBe(true);
    expect(response.servicePath).toContain('local-cache');
    expect(response.knowledgePatterns[0].id).toBe('cached-pattern');

    const stats = service.getProcessingStats();
    expect(stats.totalRequests).toBe(2);
    expect(stats.fallbackUsageRate).toBeGreaterThan(0);
    expect(stats.cacheHitRate).toBeGreaterThan(0);

    await localKnowledgeCache.delete('pattern:auth-pattern:generic:cached-pattern');
  });

  it('records failure metrics when downstream processing throws', async () => {
    const permagraphResult: KnowledgeQueryResult = {
      queryId: 'query-2',
      resultType: 'service-pattern',
      title: 'Service Template',
      description: 'Used for failure scenario test',
      content: {
        id: 'pattern-456',
        framework: 'react',
      },
      relevanceScore: 0.6,
      source: 'library',
    };

    knowledgeClient.queryKnowledge.mockResolvedValue({
      results: [permagraphResult],
      metadata: {},
    });

    const recommendationSpy = jest
      .spyOn<any, any>(service as any, 'generateRecommendations')
      .mockRejectedValue(new Error('Recommendation generator offline'));

    const response = await service.processRequest(createRequest());

    expect(response.success).toBe(false);
    expect(response.metadata.errors[0]).toContain('Recommendation generator offline');

    const stats = service.getProcessingStats();
    expect(stats.totalRequests).toBe(3);
    expect(stats.successRate).toBeLessThan(1);
    expect(stats.averageProcessingTime).toBeGreaterThan(0);

    recommendationSpy.mockRestore();
  });
});

