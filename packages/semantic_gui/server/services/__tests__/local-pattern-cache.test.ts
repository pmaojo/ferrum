/**
 * Local Pattern Cache Tests
 * 
 * Tests for file-based pattern storage with JSON serialization,
 * cache indexing for fast pattern lookup and filtering,
 * and cache size management with LRU eviction policy.
 */

import { LocalPatternCache, PatternCacheEntry, CacheIndexEntry } from '../local-pattern-cache';
import { AuthPattern, ServicePattern, RequirementChain } from '../pattern-models';
import { promises as fs } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { string } from 'zod';
import { string } from 'zod';
import { string } from 'zod';
import { any } from 'zod';

describe('LocalPatternCache', () => {
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

  describe('Pattern Storage and Retrieval', () => {
    it('should store and retrieve auth patterns', async () => {
      const authPattern: AuthPattern = {
        id: 'auth-2fa-test-001',
        version: '1.0.0',
        createdAt: new Date(),
        updatedAt: new Date(),
        createdBy: 'test-user',
        usageCount: 5,
        successRate: 0.9,
        tags: ['2fa', 'totp', 'security'],
        deprecated: false,
        type: '2fa',
        framework: 'tuetano',
        securityCompliance: {
          owasp: true,
          pciDss: true,
          gdpr: false,
          sox: false,
          score: 85
        },
        dependencies: [],
        codeTemplates: [],
        historicalUsage: {
          totalImplementations: 10,
          successfulImplementations: 9,
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
          complianceScore: 85
        },
        implementationComplexity: {
          implementationTime: 3600000,
          linesOfCode: 150,
          cyclomaticComplexity: 5,
          dependencyCount: 3,
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

    it('should store and retrieve service patterns', async () => {
      const servicePattern: ServicePattern = {
        id: 'service-payment-test-001',
        version: '1.0.0',
        createdAt: new Date(),
        updatedAt: new Date(),
        createdBy: 'test-user',
        usageCount: 3,
        successRate: 0.95,
        tags: ['payment', 'gateway', 'stripe'],
        deprecated: false,
        type: 'payment_gateway',
        framework: 'kthulu',
        integrationPoints: [
          {
            name: 'stripe-api',
            type: 'api',
            protocol: 'https',
            authentication: 'api-key',
            dataFormat: 'json',
            errorHandling: 'retry-with-backoff'
          }
        ],
        securityRequirements: [
          {
            id: 'sec-001',
            type: 'encryption',
            description: 'All payment data must be encrypted in transit',
            severity: 'critical',
            implementation: 'TLS 1.3',
            validationRules: ['tls-version-check'],
            complianceStandards: ['PCI-DSS']
          }
        ],
        complianceStandards: ['PCI-DSS', 'SOX'],
        architecturalFit: 0.9
      };

      await cache.storePattern(servicePattern);
      const retrieved = await cache.getPattern(servicePattern.id);

      expect(retrieved).toBeDefined();
      expect(retrieved?.id).toBe(servicePattern.id);
      expect((retrieved as ServicePattern)?.type).toBe('payment_gateway');
      expect((retrieved as ServicePattern)?.framework).toBe('kthulu');
    });

    it('should handle pattern expiration based on TTL', async () => {
      const pattern: AuthPattern = {
        id: 'auth-expiring-test',
        version: '1.0.0',
        createdAt: new Date(),
        updatedAt: new Date(),
        createdBy: 'test-user',
        usageCount: 1,
        successRate: 0.8,
        tags: ['test'],
        deprecated: false,
        type: '2fa',
        framework: 'generic',
        securityCompliance: {
          owasp: false,
          pciDss: false,
          gdpr: false,
          sox: false,
          score: 50
        },
        dependencies: [],
        codeTemplates: [],
        historicalUsage: {
          totalImplementations: 1,
          successfulImplementations: 1,
          averageImplementationTime: 1800000,
          commonIssues: [],
          lastUsed: new Date()
        },
        architecturalFit: 0.5,
        securityStrength: {
          authenticationFactors: 1,
          encryptionStrength: 'moderate',
          vulnerabilityResistance: {
            bruteForce: 0.5,
            phishing: 0.5,
            manInTheMiddle: 0.5,
            sessionHijacking: 0.5,
            crossSiteScripting: 0.5
          },
          complianceScore: 50
        },
        implementationComplexity: {
          implementationTime: 1800000,
          linesOfCode: 50,
          cyclomaticComplexity: 2,
          dependencyCount: 1,
          configurationComplexity: 1
        },
        testingStrategy: {
          unitTestCoverage: 0.7,
          integrationTestCoverage: 0.6,
          securityTestCoverage: 0.5,
          automatedTestSuite: false,
          performanceTestSuite: false
        }
      };

      // Store with very short TTL
      await cache.storePattern(pattern, { ttl: 100 }); // 100ms

      // Should be available immediately
      let retrieved = await cache.getPattern(pattern.id);
      expect(retrieved).toBeDefined();

      // Wait for expiration
      await new Promise(resolve => setTimeout(resolve, 150));

      // Should be expired now
      retrieved = await cache.getPattern(pattern.id);
      expect(retrieved).toBeNull();
    });
  });

  describe('Pattern Indexing and Search', () => {
    beforeEach(async () => {
      // Add test patterns for search testing
      const patterns = [
        {
          id: 'auth-2fa-tuetano-001',
          type: '2fa' as const,
          framework: 'tuetano' as const,
          tags: ['2fa', 'totp', 'tuetano', 'security'],
          successRate: 0.9
        },
        {
          id: 'auth-oauth-kthulu-001',
          type: 'oauth' as const,
          framework: 'kthulu' as const,
          tags: ['oauth', 'kthulu', 'authentication'],
          successRate: 0.85
        },
        {
          id: 'service-payment-ferrum-001',
          type: 'payment_gateway' as const,
          framework: 'ferrum' as const,
          tags: ['payment', 'gateway', 'ferrum'],
          successRate: 0.95
        }
      ];

      for (const patternData of patterns) {
        const pattern = this.createTestPattern(patternData);
        await cache.storePattern(pattern);
      }
    });

    it('should find patterns by type', async () => {
      const authPatterns = await cache.findPatternsByType('auth');
      expect(authPatterns.length).toBe(2);
      expect(authPatterns.every(p => p.id.startsWith('auth-'))).toBe(true);

      const servicePatterns = await cache.findPatternsByType('service');
      expect(servicePatterns.length).toBe(1);
      expect(servicePatterns[0].id).toBe('service-payment-ferrum-001');
    });

    it('should find patterns by framework', async () => {
      const tuetanoPatterns = await cache.findPatternsByFramework('tuetano');
      expect(tuetanoPatterns.length).toBe(1);
      expect(tuetanoPatterns[0].id).toBe('auth-2fa-tuetano-001');

      const kthuluPatterns = await cache.findPatternsByFramework('kthulu');
      expect(kthuluPatterns.length).toBe(1);
      expect(kthuluPatterns[0].id).toBe('auth-oauth-kthulu-001');
    });

    it('should find patterns by tags', async () => {
      const securityPatterns = await cache.findPatternsByTags(['security']);
      expect(securityPatterns.length).toBe(1);
      expect(securityPatterns[0].id).toBe('auth-2fa-tuetano-001');

      const paymentPatterns = await cache.findPatternsByTags(['payment']);
      expect(paymentPatterns.length).toBe(1);
      expect(paymentPatterns[0].id).toBe('service-payment-ferrum-001');
    });

    it('should perform complex searches with multiple criteria', async () => {
      const results = await cache.searchPatterns({
        type: 'auth',
        framework: 'tuetano',
        tags: ['2fa'],
        minSuccessRate: 0.8
      });

      expect(results.length).toBe(1);
      expect(results[0].id).toBe('auth-2fa-tuetano-001');
    });

    // Helper method to create test patterns
    createTestPattern(data: any): AuthPattern | ServicePattern {
      const basePattern = {
        version: '1.0.0',
        createdAt: new Date(),
        updatedAt: new Date(),
        createdBy: 'test-user',
        usageCount: 1,
        deprecated: false,
        ...data
      };

      if (data.type === 'payment_gateway') {
        return {
          ...basePattern,
          integrationPoints: [],
          securityRequirements: [],
          complianceStandards: [],
          architecturalFit: 0.8
        } as ServicePattern;
      } else {
        return {
          ...basePattern,
          securityCompliance: {
            owasp: true,
            pciDss: false,
            gdpr: false,
            sox: false,
            score: 75
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
            encryptionStrength: 'strong' as const,
            vulnerabilityResistance: {
              bruteForce: 0.8,
              phishing: 0.7,
              manInTheMiddle: 0.8,
              sessionHijacking: 0.7,
              crossSiteScripting: 0.6
            },
            complianceScore: 75
          },
          implementationComplexity: {
            implementationTime: 3600000,
            linesOfCode: 100,
            cyclomaticComplexity: 3,
            dependencyCount: 2,
            configurationComplexity: 2
          },
          testingStrategy: {
            unitTestCoverage: 0.8,
            integrationTestCoverage: 0.7,
            securityTestCoverage: 0.75,
            automatedTestSuite: true,
            performanceTestSuite: false
          }
        } as AuthPattern;
      }
    }
  });

  describe('Cache Management', () => {
    it('should enforce size limits with LRU eviction', async () => {
      // Create cache with very small size limit
      const smallCache = new LocalPatternCache({
        cacheDirectory: join(tempDir, 'small-cache'),
        maxSize: 1024, // 1KB
        maxEntries: 2,
        defaultTTL: 60000,
        persistToDisk: false
      });

      try {
        // Add patterns that exceed the limit
        for (let i = 0; i < 5; i++) {
          const pattern = this.createLargeTestPattern(`test-pattern-${i}`);
          await smallCache.storePattern(pattern);
        }

        const stats = smallCache.getStats();
        expect(stats.totalEntries).toBeLessThanOrEqual(2);
        expect(stats.cacheSize).toBeLessThanOrEqual(1024);

        // The most recently added patterns should still be there
        const pattern4 = await smallCache.getPattern('test-pattern-4');
        const pattern3 = await smallCache.getPattern('test-pattern-3');
        expect(pattern4).toBeDefined();
        expect(pattern3).toBeDefined();

        // Earlier patterns should have been evicted
        const pattern0 = await smallCache.getPattern('test-pattern-0');
        expect(pattern0).toBeNull();
      } finally {
        await smallCache.shutdown();
      }
    });

    it('should persist cache to disk and reload', async () => {
      const pattern: AuthPattern = this.createTestAuthPattern('persistent-test');
      await cache.storePattern(pattern);

      // Force save to disk
      await cache.syncToDisk();

      // Create new cache instance with same directory
      const newCache = new LocalPatternCache({
        cacheDirectory: tempDir,
        persistToDisk: true
      });

      try {
        // Wait for initialization
        await new Promise(resolve => setTimeout(resolve, 100));

        const retrieved = await newCache.getPattern('persistent-test');
        expect(retrieved).toBeDefined();
        expect(retrieved?.id).toBe('persistent-test');
      } finally {
        await newCache.shutdown();
      }
    });

    // Helper methods
    createLargeTestPattern(id: string): AuthPattern {
      return {
        id,
        version: '1.0.0',
        createdAt: new Date(),
        updatedAt: new Date(),
        createdBy: 'test-user',
        usageCount: 1,
        successRate: 0.8,
        tags: ['test', 'large-pattern', 'memory-test'],
        deprecated: false,
        type: '2fa',
        framework: 'generic',
        securityCompliance: {
          owasp: true,
          pciDss: true,
          gdpr: true,
          sox: true,
          score: 90
        },
        dependencies: Array(10).fill(null).map((_, i) => ({
          name: `dependency-${i}`,
          version: '1.0.0',
          type: 'required' as const,
          securityImplications: [`security-implication-${i}`]
        })),
        codeTemplates: [],
        historicalUsage: {
          totalImplementations: 100,
          successfulImplementations: 80,
          averageImplementationTime: 3600000,
          commonIssues: Array(20).fill(null).map((_, i) => `issue-${i}`),
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
          complianceScore: 90
        },
        implementationComplexity: {
          implementationTime: 3600000,
          linesOfCode: 500,
          cyclomaticComplexity: 10,
          dependencyCount: 10,
          configurationComplexity: 5
        },
        testingStrategy: {
          unitTestCoverage: 0.95,
          integrationTestCoverage: 0.9,
          securityTestCoverage: 0.95,
          automatedTestSuite: true,
          performanceTestSuite: true
        }
      };
    }

    createTestAuthPattern(id: string): AuthPattern {
      return {
        id,
        version: '1.0.0',
        createdAt: new Date(),
        updatedAt: new Date(),
        createdBy: 'test-user',
        usageCount: 1,
        successRate: 0.8,
        tags: ['test'],
        deprecated: false,
        type: '2fa',
        framework: 'generic',
        securityCompliance: {
          owasp: false,
          pciDss: false,
          gdpr: false,
          sox: false,
          score: 50
        },
        dependencies: [],
        codeTemplates: [],
        historicalUsage: {
          totalImplementations: 1,
          successfulImplementations: 1,
          averageImplementationTime: 1800000,
          commonIssues: [],
          lastUsed: new Date()
        },
        architecturalFit: 0.5,
        securityStrength: {
          authenticationFactors: 1,
          encryptionStrength: 'moderate',
          vulnerabilityResistance: {
            bruteForce: 0.5,
            phishing: 0.5,
            manInTheMiddle: 0.5,
            sessionHijacking: 0.5,
            crossSiteScripting: 0.5
          },
          complianceScore: 50
        },
        implementationComplexity: {
          implementationTime: 1800000,
          linesOfCode: 50,
          cyclomaticComplexity: 2,
          dependencyCount: 1,
          configurationComplexity: 1
        },
        testingStrategy: {
          unitTestCoverage: 0.7,
          integrationTestCoverage: 0.6,
          securityTestCoverage: 0.5,
          automatedTestSuite: false,
          performanceTestSuite: false
        }
      };
    }
  });

  describe('Cache Synchronization', () => {
    it('should invalidate patterns by tags', async () => {
      // Add test patterns
      const pattern1 = this.createTestAuthPattern('sync-test-1');
      pattern1.tags = ['sync', 'test', 'group-a'];
      const pattern2 = this.createTestAuthPattern('sync-test-2');
      pattern2.tags = ['sync', 'test', 'group-b'];

      await cache.storePattern(pattern1);
      await cache.storePattern(pattern2);

      // Verify both are stored
      expect(await cache.getPattern('sync-test-1')).toBeDefined();
      expect(await cache.getPattern('sync-test-2')).toBeDefined();

      // Invalidate by tag
      const invalidated = await cache.invalidateByTags(['group-a']);
      expect(invalidated).toBe(1);

      // Verify selective invalidation
      expect(await cache.getPattern('sync-test-1')).toBeNull();
      expect(await cache.getPattern('sync-test-2')).toBeDefined();
    });

    it('should handle cache refresh from external source', async () => {
      const pattern = this.createTestAuthPattern('refresh-test');
      await cache.storePattern(pattern);

      // Simulate external update
      const updatedPattern = { ...pattern };
      updatedPattern.successRate = 0.95;
      updatedPattern.usageCount = 10;
      updatedPattern.updatedAt = new Date();

      await cache.refreshPattern(updatedPattern);

      const retrieved = await cache.getPattern('refresh-test');
      expect(retrieved?.successRate).toBe(0.95);
      expect(retrieved?.usageCount).toBe(10);
    });
  });
});