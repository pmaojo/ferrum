/**
 * Pattern Data Models
 * 
 * Implements AuthPattern, ServicePattern, and RequirementChain data models
 * with pattern serialization, validation logic, and pattern versioning and
 * evolution tracking.
 */

import { z } from 'zod';
import { performance } from 'node:perf_hooks';
import { logger } from '../utils/logger';
import { ValidationRule } from './permagraph-query-engine';
import { ComplianceMapping } from './permagraph-query-engine';
import { DependencyLink } from './permagraph-query-engine';
import { HistoricalUsage } from './permagraph-query-engine';
import { TemplateReference } from './permagraph-query-engine';
import { ComplianceLevel } from './permagraph-query-engine';

// Re-export existing interfaces from permagraph-query-engine for compatibility
export type {
  ComplianceLevel,
  TemplateReference,
  HistoricalUsage,
  DependencyLink,
  ComplianceMapping,
  ValidationRule
} from './permagraph-query-engine';

// Base pattern metadata interface
export interface PatternMetadata {
  id: string;
  version: string;
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
  usageCount: number;
  successRate: number;
  tags: string[];
  deprecated: boolean;
  deprecationReason?: string;
  replacedBy?: string;
}

// Enhanced AuthPattern with validation and versioning
export interface AuthPattern extends PatternMetadata {
  type: '2fa' | 'oauth' | 'jwt' | 'session' | 'totp' | 'backup_codes' | 'biometric';
  framework: 'tuetano' | 'kthulu' | 'ferrum' | 'generic';
  securityCompliance: ComplianceLevel;
  dependencies: PatternDependency[];
  codeTemplates: TemplateReference[];
  historicalUsage: HistoricalUsage;
  architecturalFit: number;
  securityStrength: SecurityStrength;
  implementationComplexity: ComplexityMetrics;
  testingStrategy: TestingStrategy;
}

export interface PatternDependency {
  name: string;
  version: string;
  type: 'required' | 'optional' | 'peer';
  framework?: string;
  securityImplications: string[];
}

export interface SecurityStrength {
  authenticationFactors: number;
  encryptionStrength: 'weak' | 'moderate' | 'strong' | 'military';
  vulnerabilityResistance: VulnerabilityResistance;
  complianceScore: number;
}

export interface VulnerabilityResistance {
  bruteForce: number;
  phishing: number;
  manInTheMiddle: number;
  sessionHijacking: number;
  crossSiteScripting: number;
}

export interface ComplexityMetrics {
  implementationTime: number;
  linesOfCode: number;
  cyclomaticComplexity: number;
  dependencyCount: number;
  configurationComplexity: number;
}

export interface TestingStrategy {
  unitTestCoverage: number;
  integrationTestCoverage: number;
  securityTestCoverage: number;
  automatedTestSuite: boolean;
  performanceTestSuite: boolean;
}

// Enhanced ServicePattern with validation and versioning
export interface ServicePattern extends PatternMetadata {
  type: 'payment_gateway' | 'payment_processor' | 'billing' | 'subscription' | 'wallet' | 'fraud_detection';
  framework: string;
  integrationPoints: IntegrationPoint[];
  securityRequirements: SecurityRequirement[];
  complianceStandards: string[];
  architecturalFit: number;
}

export interface IntegrationPoint {
  name: string;
  type: 'api' | 'webhook' | 'queue' | 'database' | 'file';
  protocol: string;
  authentication: string;
  dataFormat: string;
  errorHandling: string;
}

export interface SecurityRequirement {
  id: string;
  type: 'encryption' | 'authentication' | 'authorization' | 'audit' | 'compliance';
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  implementation: string;
  validationRules: string[];
  complianceStandards: string[];
}

// Enhanced RequirementChain with validation and versioning
export interface RequirementChain extends PatternMetadata {
  sourceRequirement: string;
  linkedRequirements: LinkedRequirement[];
  dependencies: DependencyLink[];
  complianceMapping: ComplianceMapping[];
  validationRules: ValidationRule[];
}

export interface LinkedRequirement {
  id: string;
  description: string;
  type: 'functional' | 'non_functional' | 'security' | 'compliance' | 'business';
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: 'draft' | 'approved' | 'implemented' | 'tested' | 'deployed';
  stakeholders: string[];
  acceptanceCriteria: AcceptanceCriterion[];
}

export interface AcceptanceCriterion {
  id: string;
  description: string;
  testable: boolean;
  automatable: boolean;
  priority: number;
  validationMethod: string;
}

// Validation schemas using Zod
export const PatternMetadataSchema = z.object({
  id: z.string().min(1),
  version: z.string().regex(/^\d+\.\d+\.\d+$/),
  createdAt: z.date(),
  updatedAt: z.date(),
  createdBy: z.string().min(1),
  usageCount: z.number().min(0),
  successRate: z.number().min(0).max(1),
  tags: z.array(z.string()),
  deprecated: z.boolean(),
  deprecationReason: z.string().optional(),
  replacedBy: z.string().optional()
});

export const AuthPatternSchema = PatternMetadataSchema.extend({
  type: z.enum(['2fa', 'oauth', 'jwt', 'session', 'totp', 'backup_codes', 'biometric']),
  framework: z.enum(['tuetano', 'kthulu', 'ferrum', 'generic']),
  securityCompliance: z.object({
    owasp: z.boolean(),
    pciDss: z.boolean(),
    gdpr: z.boolean(),
    sox: z.boolean(),
    score: z.number().min(0).max(100)
  }),
  dependencies: z.array(z.object({
    name: z.string(),
    version: z.string(),
    type: z.enum(['required', 'optional', 'peer']),
    framework: z.string().optional(),
    securityImplications: z.array(z.string())
  })),
  architecturalFit: z.number().min(0).max(1)
});/**
 * 
Pattern Manager - Main class for managing pattern data models with validation and versioning
 */
export class PatternManager {
  private patterns: Map<string, AuthPattern | ServicePattern | RequirementChain> = new Map();
  private validationCache: Map<string, boolean> = new Map();

  constructor() {
    logger.info('PatternManager initialized');
  }

  /**
   * Create a new AuthPattern with validation
   */
  async createAuthPattern(data: Partial<AuthPattern>): Promise<AuthPattern> {
    const startTime = performance.now();
    
    try {
      // Generate ID if not provided
      if (!data.id) {
        data.id = this.generatePatternId('auth', data.type || '2fa');
      }

      // Set default metadata
      const now = new Date();
      const patternData: AuthPattern = {
        ...data,
        id: data.id,
        version: data.version || '1.0.0',
        createdAt: data.createdAt || now,
        updatedAt: now,
        createdBy: data.createdBy || 'system',
        usageCount: data.usageCount || 0,
        successRate: data.successRate || 0,
        tags: data.tags || [],
        deprecated: data.deprecated || false,
        type: data.type || '2fa',
        framework: data.framework || 'generic',
        securityCompliance: data.securityCompliance || {
          owasp: false,
          pciDss: false,
          gdpr: false,
          sox: false,
          score: 0
        },
        dependencies: data.dependencies || [],
        codeTemplates: data.codeTemplates || [],
        historicalUsage: data.historicalUsage || {
          totalImplementations: 0,
          successfulImplementations: 0,
          averageImplementationTime: 0,
          commonIssues: [],
          lastUsed: now
        },
        architecturalFit: data.architecturalFit || 0,
        securityStrength: data.securityStrength || {
          authenticationFactors: 1,
          encryptionStrength: 'moderate',
          vulnerabilityResistance: {
            bruteForce: 0.5,
            phishing: 0.5,
            manInTheMiddle: 0.5,
            sessionHijacking: 0.5,
            crossSiteScripting: 0.5
          },
          complianceScore: 0
        },
        implementationComplexity: data.implementationComplexity || {
          implementationTime: 0,
          linesOfCode: 0,
          cyclomaticComplexity: 1,
          dependencyCount: 0,
          configurationComplexity: 0
        },
        testingStrategy: data.testingStrategy || {
          unitTestCoverage: 0,
          integrationTestCoverage: 0,
          securityTestCoverage: 0,
          automatedTestSuite: false,
          performanceTestSuite: false
        }
      } as AuthPattern;

      // Validate the pattern
      const validationResult = this.validateAuthPattern(patternData);
      if (!validationResult.success) {
        throw new Error(`Validation failed: ${validationResult.error?.message}`);
      }

      // Store the pattern
      this.patterns.set(patternData.id, patternData);

      const endTime = performance.now();
      logger.info('AuthPattern created successfully', {
        patternId: patternData.id,
        type: patternData.type,
        framework: patternData.framework,
        duration: endTime - startTime
      });

      return patternData;
    } catch (error) {
      logger.error('Failed to create AuthPattern', { error: (error as Error).message });
      throw error;
    }
  }

  /**
   * Create a new ServicePattern with validation
   */
  async createServicePattern(data: Partial<ServicePattern>): Promise<ServicePattern> {
    const startTime = performance.now();
    
    try {
      // Generate ID if not provided
      if (!data.id) {
        data.id = this.generatePatternId('service', data.type || 'payment_gateway');
      }

      // Set default metadata
      const now = new Date();
      const patternData: ServicePattern = {
        ...data,
        id: data.id,
        version: data.version || '1.0.0',
        createdAt: data.createdAt || now,
        updatedAt: now,
        createdBy: data.createdBy || 'system',
        usageCount: data.usageCount || 0,
        successRate: data.successRate || 0,
        tags: data.tags || [],
        deprecated: data.deprecated || false,
        type: data.type || 'payment_gateway',
        framework: data.framework || 'generic',
        integrationPoints: data.integrationPoints || [],
        securityRequirements: data.securityRequirements || [],
        complianceStandards: data.complianceStandards || [],
        architecturalFit: data.architecturalFit || 0
      } as ServicePattern;

      // Validate the pattern
      const validationResult = this.validateServicePattern(patternData);
      if (!validationResult.success) {
        throw new Error(`Validation failed: ${validationResult.error?.message}`);
      }

      // Store the pattern
      this.patterns.set(patternData.id, patternData);

      const endTime = performance.now();
      logger.info('ServicePattern created successfully', {
        patternId: patternData.id,
        type: patternData.type,
        framework: patternData.framework,
        duration: endTime - startTime
      });

      return patternData;
    } catch (error) {
      logger.error('Failed to create ServicePattern', { error: (error as Error).message });
      throw error;
    }
  }  /**

   * Create a new RequirementChain with validation
   */
  async createRequirementChain(data: Partial<RequirementChain>): Promise<RequirementChain> {
    const startTime = performance.now();
    
    try {
      // Generate ID if not provided
      if (!data.id) {
        data.id = this.generatePatternId('requirement', 'chain');
      }

      // Set default metadata
      const now = new Date();
      const patternData: RequirementChain = {
        ...data,
        id: data.id,
        version: data.version || '1.0.0',
        createdAt: data.createdAt || now,
        updatedAt: now,
        createdBy: data.createdBy || 'system',
        usageCount: data.usageCount || 0,
        successRate: data.successRate || 0,
        tags: data.tags || [],
        deprecated: data.deprecated || false,
        sourceRequirement: data.sourceRequirement || '',
        linkedRequirements: data.linkedRequirements || [],
        dependencies: data.dependencies || [],
        complianceMapping: data.complianceMapping || [],
        validationRules: data.validationRules || []
      } as RequirementChain;

      // Validate the pattern
      const validationResult = this.validateRequirementChain(patternData);
      if (!validationResult.success) {
        throw new Error(`Validation failed: ${validationResult.error?.message}`);
      }

      // Store the pattern
      this.patterns.set(patternData.id, patternData);

      const endTime = performance.now();
      logger.info('RequirementChain created successfully', {
        patternId: patternData.id,
        sourceRequirement: patternData.sourceRequirement,
        linkedCount: patternData.linkedRequirements.length,
        duration: endTime - startTime
      });

      return patternData;
    } catch (error) {
      logger.error('Failed to create RequirementChain', { error: (error as Error).message });
      throw error;
    }
  }

  /**
   * Validate AuthPattern using Zod schema
   */
  validateAuthPattern(pattern: AuthPattern): { success: boolean; error?: z.ZodError } {
    try {
      AuthPatternSchema.parse(pattern);
      this.validationCache.set(`auth-${pattern.id}`, true);
      return { success: true };
    } catch (error) {
      this.validationCache.set(`auth-${pattern.id}`, false);
      return { success: false, error: error as z.ZodError };
    }
  }

  /**
   * Validate ServicePattern (simplified validation)
   */
  validateServicePattern(pattern: ServicePattern): { success: boolean; error?: Error } {
    try {
      if (!pattern.id || !pattern.type || !pattern.framework) {
        throw new Error('Missing required fields: id, type, framework');
      }
      this.validationCache.set(`service-${pattern.id}`, true);
      return { success: true };
    } catch (error) {
      this.validationCache.set(`service-${pattern.id}`, false);
      return { success: false, error: error as Error };
    }
  }

  /**
   * Validate RequirementChain (simplified validation)
   */
  validateRequirementChain(pattern: RequirementChain): { success: boolean; error?: Error } {
    try {
      if (!pattern.id || !pattern.sourceRequirement) {
        throw new Error('Missing required fields: id, sourceRequirement');
      }
      this.validationCache.set(`requirement-${pattern.id}`, true);
      return { success: true };
    } catch (error) {
      this.validationCache.set(`requirement-${pattern.id}`, false);
      return { success: false, error: error as Error };
    }
  }

  /**
   * Serialize pattern to JSON with metadata
   */
  serializePattern(pattern: AuthPattern | ServicePattern | RequirementChain): string {
    const serializedData = {
      ...pattern,
      _serializedAt: new Date().toISOString(),
      _version: '1.0.0',
      _type: this.getPatternType(pattern)
    };

    return JSON.stringify(serializedData, null, 2);
  }

  /**
   * Deserialize pattern from JSON with validation
   */
  deserializePattern(jsonData: string): AuthPattern | ServicePattern | RequirementChain {
    try {
      const data = JSON.parse(jsonData);
      
      // Convert date strings back to Date objects
      if (data.createdAt) data.createdAt = new Date(data.createdAt);
      if (data.updatedAt) data.updatedAt = new Date(data.updatedAt);
      if (data.historicalUsage?.lastUsed) {
        data.historicalUsage.lastUsed = new Date(data.historicalUsage.lastUsed);
      }

      // Validate based on pattern type
      switch (data._type) {
        case 'auth':
          const authValidation = this.validateAuthPattern(data);
          if (!authValidation.success) {
            throw new Error(`Invalid AuthPattern: ${authValidation.error?.message}`);
          }
          return data as AuthPattern;
        
        case 'service':
          const serviceValidation = this.validateServicePattern(data);
          if (!serviceValidation.success) {
            throw new Error(`Invalid ServicePattern: ${serviceValidation.error?.message}`);
          }
          return data as ServicePattern;
        
        case 'requirement':
          const requirementValidation = this.validateRequirementChain(data);
          if (!requirementValidation.success) {
            throw new Error(`Invalid RequirementChain: ${requirementValidation.error?.message}`);
          }
          return data as RequirementChain;
        
        default:
          throw new Error(`Unknown pattern type: ${data._type}`);
      }
    } catch (error) {
      logger.error('Failed to deserialize pattern', error as Error);
      throw error;
    }
  }  
/**
   * Get pattern by ID
   */
  getPattern(patternId: string): AuthPattern | ServicePattern | RequirementChain | undefined {
    return this.patterns.get(patternId);
  }

  /**
   * Get patterns by type
   */
  getPatternsByType(type: 'auth' | 'service' | 'requirement'): (AuthPattern | ServicePattern | RequirementChain)[] {
    const patterns: (AuthPattern | ServicePattern | RequirementChain)[] = [];
    
    for (const pattern of this.patterns.values()) {
      if (this.getPatternType(pattern) === type) {
        patterns.push(pattern);
      }
    }
    
    return patterns;
  }

  /**
   * Search patterns by criteria
   */
  searchPatterns(criteria: {
    type?: 'auth' | 'service' | 'requirement';
    framework?: string;
    tags?: string[];
    deprecated?: boolean;
    minSuccessRate?: number;
  }): (AuthPattern | ServicePattern | RequirementChain)[] {
    const results: (AuthPattern | ServicePattern | RequirementChain)[] = [];
    
    for (const pattern of this.patterns.values()) {
      let matches = true;
      
      if (criteria.type && this.getPatternType(pattern) !== criteria.type) {
        matches = false;
      }
      
      if (criteria.framework && 'framework' in pattern && pattern.framework !== criteria.framework) {
        matches = false;
      }
      
      if (criteria.tags && !criteria.tags.every(tag => pattern.tags.includes(tag))) {
        matches = false;
      }
      
      if (criteria.deprecated !== undefined && pattern.deprecated !== criteria.deprecated) {
        matches = false;
      }
      
      if (criteria.minSuccessRate && pattern.successRate < criteria.minSuccessRate) {
        matches = false;
      }
      
      if (matches) {
        results.push(pattern);
      }
    }
    
    return results;
  }

  /**
   * Get pattern statistics
   */
  getPatternStatistics(): {
    totalPatterns: number;
    authPatterns: number;
    servicePatterns: number;
    requirementChains: number;
    deprecatedPatterns: number;
    averageSuccessRate: number;
  } {
    const authPatterns = this.getPatternsByType('auth').length;
    const servicePatterns = this.getPatternsByType('service').length;
    const requirementChains = this.getPatternsByType('requirement').length;
    const totalPatterns = authPatterns + servicePatterns + requirementChains;
    
    const deprecatedPatterns = Array.from(this.patterns.values())
      .filter(p => p.deprecated).length;
    
    const totalSuccessRate = Array.from(this.patterns.values())
      .reduce((sum, p) => sum + p.successRate, 0);
    const averageSuccessRate = totalPatterns > 0 ? totalSuccessRate / totalPatterns : 0;

    return {
      totalPatterns,
      authPatterns,
      servicePatterns,
      requirementChains,
      deprecatedPatterns,
      averageSuccessRate
    };
  }

  // Private helper methods
  private generatePatternId(type: string, subtype: string): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    return `${type}-${subtype}-${timestamp}-${random}`;
  }

  private getPatternType(pattern: AuthPattern | ServicePattern | RequirementChain): 'auth' | 'service' | 'requirement' {
    if ('type' in pattern && ['2fa', 'oauth', 'jwt', 'session', 'totp', 'backup_codes', 'biometric'].includes(pattern.type)) {
      return 'auth';
    }
    if ('type' in pattern && ['payment_gateway', 'payment_processor', 'billing', 'subscription', 'wallet', 'fraud_detection'].includes(pattern.type)) {
      return 'service';
    }
    if ('sourceRequirement' in pattern) {
      return 'requirement';
    }
    throw new Error('Unable to determine pattern type');
  }
}

// Export singleton instance
export const patternManager = new PatternManager();