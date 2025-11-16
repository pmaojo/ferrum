/**
 * Pattern Models Test Suite
 * 
 * Tests for AuthPattern, ServicePattern, and RequirementChain data models
 * with validation, serialization, and versioning functionality.
 */

import { 
  PatternManager, 
  AuthPattern, 
  ServicePattern, 
  RequirementChain,
  patternManager 
} from '../pattern-models';

describe('PatternManager', () => {
  let manager: PatternManager;

  beforeEach(() => {
    manager = new PatternManager();
  });

  describe('AuthPattern Management', () => {
    it('should create a valid AuthPattern with default values', async () => {
      const authData = {
        type: '2fa' as const,
        framework: 'tuetano' as const,
        createdBy: 'test-user'
      };

      const pattern = await manager.createAuthPattern(authData);

      expect(pattern.id).toBeDefined();
      expect(pattern.type).toBe('2fa');
      expect(pattern.framework).toBe('tuetano');
      expect(pattern.version).toBe('1.0.0');
      expect(pattern.createdBy).toBe('test-user');
      expect(pattern.usageCount).toBe(0);
      expect(pattern.successRate).toBe(0);
      expect(pattern.deprecated).toBe(false);
      expect(pattern.securityStrength).toBeDefined();
      expect(pattern.implementationComplexity).toBeDefined();
      expect(pattern.testingStrategy).toBeDefined();
    });

    it('should validate AuthPattern with required fields', async () => {
      const validPattern: Partial<AuthPattern> = {
        type: 'oauth',
        framework: 'kthulu',
        createdBy: 'test-user',
        securityCompliance: {
          owasp: true,
          pciDss: false,
          gdpr: true,
          sox: false,
          score: 85
        }
      };

      const pattern = await manager.createAuthPattern(validPattern);
      const validation = manager.validateAuthPattern(pattern);

      expect(validation.success).toBe(true);
      expect(validation.error).toBeUndefined();
    });

    it('should reject invalid AuthPattern', async () => {
      const invalidPattern = {
        type: 'invalid-type',
        framework: 'unknown-framework',
        version: 'invalid-version'
      };

      await expect(manager.createAuthPattern(invalidPattern as any))
        .rejects.toThrow('Validation failed');
    });

    it('should update AuthPattern with version tracking', async () => {
      const pattern = await manager.createAuthPattern({
        type: '2fa',
        framework: 'ferrum',
        createdBy: 'test-user'
      });

      const updatedPattern = await manager.updatePattern(
        pattern.id,
        { successRate: 0.85 },
        'Updated success rate based on recent implementations'
      );

      expect(updatedPattern.version).toBe('1.0.1');
      expect(updatedPattern.successRate).toBe(0.85);
      expect(updatedPattern.updatedAt).not.toEqual(pattern.updatedAt);

      const evolution = manager.getPatternEvolution(pattern.id);
      expect(evolution).toBeDefined();
      expect(evolution!.versions).toHaveLength(2);
    });
  });

  describe('ServicePattern Management', () => {
    it('should create a valid ServicePattern with default values', async () => {
      const serviceData = {
        type: 'payment_gateway' as const,
        framework: 'kthulu',
        createdBy: 'test-user'
      };

      const pattern = await manager.createServicePattern(serviceData);

      expect(pattern.id).toBeDefined();
      expect(pattern.type).toBe('payment_gateway');
      expect(pattern.framework).toBe('kthulu');
      expect(pattern.version).toBe('1.0.0');
      expect(pattern.integrationPoints).toEqual([]);
      expect(pattern.securityRequirements).toEqual([]);
      expect(pattern.complianceStandards).toEqual([]);
      expect(pattern.dataFlow).toBeDefined();
      expect(pattern.errorHandling).toBeDefined();
      expect(pattern.monitoring).toBeDefined();
    });

    it('should validate ServicePattern with integration points', async () => {
      const serviceData = {
        type: 'payment_processor' as const,
        framework: 'tuetano',
        createdBy: 'test-user',
        integrationPoints: [{
          name: 'stripe-api',
          type: 'api' as const,
          protocol: 'https',
          authentication: 'api-key',
          dataFormat: 'json',
          errorHandling: 'retry-with-backoff'
        }],
        complianceStandards: ['pci-dss', 'gdpr']
      };

      const pattern = await manager.createServicePattern(serviceData);
      const validation = manager.validateServicePattern(pattern);

      expect(validation.success).toBe(true);
      expect(pattern.integrationPoints).toHaveLength(1);
      expect(pattern.complianceStandards).toContain('pci-dss');
    });
  });

  describe('RequirementChain Management', () => {
    it('should create a valid RequirementChain with default values', async () => {
      const requirementData = {
        sourceRequirement: 'Implement 2FA for payment processing',
        createdBy: 'test-user'
      };

      const pattern = await manager.createRequirementChain(requirementData);

      expect(pattern.id).toBeDefined();
      expect(pattern.sourceRequirement).toBe('Implement 2FA for payment processing');
      expect(pattern.version).toBe('1.0.0');
      expect(pattern.linkedRequirements).toEqual([]);
      expect(pattern.dependencies).toEqual([]);
      expect(pattern.traceabilityMatrix).toBeDefined();
      expect(pattern.riskAssessment).toBeDefined();
      expect(pattern.implementationGuidance).toBeDefined();
    });

    it('should validate RequirementChain with linked requirements', async () => {
      const requirementData = {
        sourceRequirement: 'Payment service security requirements',
        createdBy: 'test-user',
        linkedRequirements: [{
          id: 'req-001',
          description: 'Implement TOTP authentication',
          type: 'security' as const,
          priority: 'high' as const,
          status: 'draft' as const,
          stakeholders: ['security-team', 'dev-team'],
          acceptanceCriteria: [{
            id: 'ac-001',
            description: 'TOTP tokens must be valid for 30 seconds',
            testable: true,
            automatable: true,
            priority: 1,
            validationMethod: 'automated-test'
          }]
        }]
      };

      const pattern = await manager.createRequirementChain(requirementData);
      const validation = manager.validateRequirementChain(pattern);

      expect(validation.success).toBe(true);
      expect(pattern.linkedRequirements).toHaveLength(1);
      expect(pattern.linkedRequirements[0].type).toBe('security');
    });
  });

  describe('Pattern Serialization', () => {
    it('should serialize and deserialize AuthPattern correctly', async () => {
      const originalPattern = await manager.createAuthPattern({
        type: 'jwt',
        framework: 'generic',
        createdBy: 'test-user',
        tags: ['authentication', 'stateless']
      });

      const serialized = manager.serializePattern(originalPattern);
      expect(serialized).toContain('"type":"jwt"');
      expect(serialized).toContain('"framework":"generic"');

      const deserialized = manager.deserializePattern(serialized);
      expect(deserialized.id).toBe(originalPattern.id);
      expect(deserialized.type).toBe(originalPattern.type);
      expect((deserialized as AuthPattern).framework).toBe(originalPattern.framework);
    });

    it('should handle date serialization correctly', async () => {
      const pattern = await manager.createAuthPattern({
        type: 'session',
        framework: 'tuetano',
        createdBy: 'test-user'
      });

      const serialized = manager.serializePattern(pattern);
      const deserialized = manager.deserializePattern(serialized);

      expect(deserialized.createdAt).toBeInstanceOf(Date);
      expect(deserialized.updatedAt).toBeInstanceOf(Date);
    });
  });

  describe('Pattern Search and Filtering', () => {
    beforeEach(async () => {
      // Create test patterns
      await manager.createAuthPattern({
        type: '2fa',
        framework: 'tuetano',
        createdBy: 'user1',
        tags: ['security', 'authentication'],
        successRate: 0.9
      });

      await manager.createAuthPattern({
        type: 'oauth',
        framework: 'kthulu',
        createdBy: 'user2',
        tags: ['authentication', 'third-party'],
        successRate: 0.7
      });

      await manager.createServicePattern({
        type: 'payment_gateway',
        framework: 'ferrum',
        createdBy: 'user3',
        tags: ['payment', 'integration'],
        successRate: 0.8
      });
    });

    it('should search patterns by type', () => {
      const authPatterns = manager.searchPatterns({ type: 'auth' });
      const servicePatterns = manager.searchPatterns({ type: 'service' });

      expect(authPatterns).toHaveLength(2);
      expect(servicePatterns).toHaveLength(1);
    });

    it('should search patterns by framework', () => {
      const tuetanoPatterns = manager.searchPatterns({ framework: 'tuetano' });
      const kthuluhPatterns = manager.searchPatterns({ framework: 'kthulu' });

      expect(tuetanoPatterns).toHaveLength(1);
      expect(kthuluhPatterns).toHaveLength(1);
    });

    it('should search patterns by tags', () => {
      const authenticationPatterns = manager.searchPatterns({ 
        tags: ['authentication'] 
      });
      const securityPatterns = manager.searchPatterns({ 
        tags: ['security'] 
      });

      expect(authenticationPatterns).toHaveLength(2);
      expect(securityPatterns).toHaveLength(1);
    });

    it('should search patterns by minimum success rate', () => {
      const highSuccessPatterns = manager.searchPatterns({ 
        minSuccessRate: 0.8 
      });
      const allPatterns = manager.searchPatterns({ 
        minSuccessRate: 0.5 
      });

      expect(highSuccessPatterns).toHaveLength(2);
      expect(allPatterns).toHaveLength(3);
    });
  });

  describe('Pattern Statistics', () => {
    beforeEach(async () => {
      await manager.createAuthPattern({
        type: '2fa',
        framework: 'tuetano',
        createdBy: 'user1',
        successRate: 0.9
      });

      await manager.createServicePattern({
        type: 'payment_gateway',
        framework: 'kthulu',
        createdBy: 'user2',
        successRate: 0.8,
        deprecated: true
      });

      await manager.createRequirementChain({
        sourceRequirement: 'Test requirement',
        createdBy: 'user3',
        successRate: 0.7
      });
    });

    it('should calculate pattern statistics correctly', () => {
      const stats = manager.getPatternStatistics();

      expect(stats.totalPatterns).toBe(3);
      expect(stats.authPatterns).toBe(1);
      expect(stats.servicePatterns).toBe(1);
      expect(stats.requirementChains).toBe(1);
      expect(stats.deprecatedPatterns).toBe(1);
      expect(stats.averageSuccessRate).toBeCloseTo(0.8, 1);
    });
  });

  describe('Pattern Evolution Tracking', () => {
    it('should track pattern evolution through updates', async () => {
      const pattern = await manager.createAuthPattern({
        type: 'totp',
        framework: 'generic',
        createdBy: 'test-user'
      });

      // First update
      await manager.updatePattern(
        pattern.id,
        { successRate: 0.5 },
        'Initial success rate data'
      );

      // Second update
      await manager.updatePattern(
        pattern.id,
        { successRate: 0.8, usageCount: 10 },
        'Improved success rate with more usage'
      );

      const evolution = manager.getPatternEvolution(pattern.id);
      expect(evolution).toBeDefined();
      expect(evolution!.versions).toHaveLength(3); // Initial + 2 updates
      expect(evolution!.evolutionMetrics.totalVersions).toBe(3);
      expect(evolution!.evolutionMetrics.breakingChangeFrequency).toBe(0);
    });

    it('should detect breaking changes', async () => {
      const pattern = await manager.createAuthPattern({
        type: 'jwt',
        framework: 'tuetano',
        createdBy: 'test-user',
        dependencies: [{
          name: 'jwt-lib',
          version: '1.0.0',
          type: 'required',
          securityImplications: []
        }]
      });

      // Breaking change - modify dependencies
      await manager.updatePattern(
        pattern.id,
        { 
          dependencies: [{
            name: 'jwt-lib',
            version: '2.0.0',
            type: 'required',
            securityImplications: []
          }, {
            name: 'crypto-lib',
            version: '1.0.0',
            type: 'required',
            securityImplications: []
          }]
        },
        'Updated to new JWT library version'
      );

      const evolution = manager.getPatternEvolution(pattern.id);
      expect(evolution!.migrationPaths).toHaveLength(1);
      expect(evolution!.migrationPaths[0].riskLevel).toBe('medium');
    });
  });
});