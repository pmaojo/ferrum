import {
  AuthPattern,
  RequirementChain,
  ServicePattern,
} from '../../../pattern-models';

const FIXTURE_TIMESTAMP = new Date('2024-01-01T00:00:00.000Z');

export function createAuthPattern(
  id: string,
  framework: AuthPattern['framework'],
  overrides: Partial<AuthPattern> = {}
): AuthPattern {
  return {
    id,
    version: '1.0.0',
    createdAt: FIXTURE_TIMESTAMP,
    updatedAt: FIXTURE_TIMESTAMP,
    createdBy: 'test-suite',
    usageCount: 10,
    successRate: 0.92,
    tags: ['2fa', framework],
    deprecated: false,
    type: '2fa',
    framework,
    securityCompliance: {
      owasp: true,
      pciDss: true,
      gdpr: true,
      sox: false,
      score: 88,
    },
    dependencies: [],
    codeTemplates: [],
    historicalUsage: {
      totalImplementations: 25,
      successfulImplementations: 22,
      averageImplementationTime: 3600000,
      commonIssues: [],
      lastUsed: FIXTURE_TIMESTAMP,
    },
    architecturalFit: 0.84,
    securityStrength: {
      authenticationFactors: 2,
      encryptionStrength: 'strong',
      vulnerabilityResistance: {
        bruteForce: 0.9,
        phishing: 0.85,
        manInTheMiddle: 0.88,
        sessionHijacking: 0.82,
        crossSiteScripting: 0.8,
      },
      complianceScore: 88,
    },
    implementationComplexity: {
      implementationTime: 7200000,
      linesOfCode: 150,
      cyclomaticComplexity: 4,
      dependencyCount: 3,
      configurationComplexity: 2,
    },
    testingStrategy: {
      unitTestCoverage: 0.85,
      integrationTestCoverage: 0.8,
      securityTestCoverage: 0.9,
      automatedTestSuite: true,
      performanceTestSuite: true,
    },
    ...overrides,
  };
}

export function createServicePattern(
  id: string,
  framework: string,
  overrides: Partial<ServicePattern> = {}
): ServicePattern {
  return {
    id,
    version: '1.0.0',
    createdAt: FIXTURE_TIMESTAMP,
    updatedAt: FIXTURE_TIMESTAMP,
    createdBy: 'test-suite',
    usageCount: 8,
    successRate: 0.9,
    tags: ['payment', framework],
    deprecated: false,
    type: 'payment_gateway',
    framework,
    integrationPoints: [
      {
        name: 'api-endpoint',
        type: 'api',
        protocol: 'https',
        authentication: 'api-key',
        dataFormat: 'json',
        errorHandling: 'retry-with-backoff',
      },
    ],
    securityRequirements: [
      {
        id: 'sec-001',
        type: 'encryption',
        description: 'Encrypt payment payloads',
        severity: 'critical',
        implementation: 'TLS 1.3',
        validationRules: ['tls-check'],
        complianceStandards: ['PCI-DSS'],
      },
    ],
    complianceStandards: ['PCI-DSS'],
    architecturalFit: 0.82,
    ...overrides,
  };
}

export function createRequirementChain(
  id: string,
  overrides: Partial<RequirementChain> = {}
): RequirementChain {
  return {
    id,
    version: '1.0.0',
    createdAt: FIXTURE_TIMESTAMP,
    updatedAt: FIXTURE_TIMESTAMP,
    createdBy: 'test-suite',
    usageCount: 6,
    successRate: 0.88,
    tags: ['compliance'],
    deprecated: false,
    sourceRequirement: 'REQ-001',
    linkedRequirements: [],
    dependencies: [],
    complianceMapping: [],
    validationRules: [],
    ...overrides,
  };
}

export function fullExportBatch() {
  return [
    createAuthPattern('auth-totp-standard', 'tuetano'),
    createAuthPattern('auth-backup-codes', 'kthulu'),
    createServicePattern('service-stripe', 'ferrum'),
  ];
}

export function incrementalExportBatch() {
  return [createAuthPattern('auth-biometric-enhanced', 'kthulu')];
}

export function emergencyExportBatch() {
  return [
    createAuthPattern('auth-basic-totp', 'generic'),
    createServicePattern('service-generic-gateway', 'generic'),
  ];
}

export function recoveryExportBatch() {
  return [createAuthPattern('auth-recovery', 'tuetano')];
}

