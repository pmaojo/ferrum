/**
 * Simple Local Pattern Cache Tests
 * 
 * Basic tests to verify the local pattern cache implementation works.
 */

import { LocalPatternCache } from '../local-pattern-cache';
import { AuthPattern } from '../pattern-models';
import { promises as fs } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';

describe('LocalPatternCache - Basic Tests', () => {
  let cache: LocalPatternCache;
  let tempDir: string;

  beforeEach(async () => {
    // Create temporary directory for testing
    tempDir = join(tmpdir(), `pattern-cache-test-${Date.now()}`);
    await fs.mkdir(tempDir, { recursive: true });
    
    cache = new LocalPatternCache({
      cacheDirectory: tempDir,
      maxSize: 1024 * 1024, // 1MB for testing
      maxEntries: 100,
      defaultTTL: 60000, // 1 minute for testing
      persistToDisk: true,
      compressionEnabled: false // Disable for easier testing
    });
  });

  afterEach(async () => {
    await cache.shutdown();
    // Clean up temp directory
    try {
      await fs.rm(tempDir, { recursive: true, force: true });
    } catch (error) {
      // Ignore cleanup errors
    }
  });

  it('should create cache instance', () => {
    expect(cache).toBeDefined();
  });

  it('should store and retrieve a simple auth pattern', async () => {
    const authPattern: AuthPattern = {
      id: 'test-auth-pattern',
      version: '1.0.0',
      createdAt: new Date(),
      updatedAt: new Date(),
      createdBy: 'test-user',
      usageCount: 1,
      successRate: 0.9,
      tags: ['test', '2fa'],
      deprecated: false,
      type: '2fa',
      framework: 'tuetano',
      securityCompliance: {
        owasp: true,
        pciDss: false,
        gdpr: false,
        sox: false,
        score: 80
      },
      dependencies: [],
      codeTemplates: [],
      historicalUsage: {
        totalImplementations: 5,
        successfulImplementations: 4,
        averageImplementationTime: 3600000,
        commonIssues: [],
        lastUsed: new Date()
      },
      architecturalFit: 0.8,
      securityStrength: {
        authenticationFactors: 2,
        encryptionStrength: 'strong',
        vulnerabilityResistance: {
          bruteForce: 0.9,
          phishing: 0.8,
          manInTheMiddle: 0.9,
          sessionHijacking: 0.8,
          crossSiteScripting: 0.7
        },
        complianceScore: 80
      },
      implementationComplexity: {
        implementationTime: 3600000,
        linesOfCode: 150,
        cyclomaticComplexity: 5,
        dependencyCount: 2,
        configurationComplexity: 2
      },
      testingStrategy: {
        unitTestCoverage: 0.9,
        integrationTestCoverage: 0.8,
        securityTestCoverage: 0.85,
        automatedTestSuite: true,
        performanceTestSuite: true
      }
    };

    await cache.storePattern(authPattern);
    const retrieved = await cache.getPattern(authPattern.id);

    expect(retrieved).toBeDefined();
    expect(retrieved?.id).toBe(authPattern.id);
    expect(retrieved?.type).toBe('2fa');
    expect(retrieved?.framework).toBe('tuetano');
  });

  it('should return null for non-existent pattern', async () => {
    const result = await cache.getPattern('non-existent-pattern');
    expect(result).toBeNull();
  });

  it('should get cache statistics', () => {
    const stats = cache.getPatternStats();
    expect(stats).toBeDefined();
    expect(stats.totalPatterns).toBe(0);
    expect(stats.authPatterns).toBe(0);
    expect(stats.servicePatterns).toBe(0);
    expect(stats.requirementChains).toBe(0);
  });
});