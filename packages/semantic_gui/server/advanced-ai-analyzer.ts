import type { GraphNode, GraphEdge, Template } from '@shared/schema';

export interface AdvancedAIInsights {
  securityVulnerabilities: SecurityVulnerability[];
  performanceBottlenecks: PerformanceBottleneck[];
  architectureDebt: ArchitectureDebt;
  refactoringOpportunities: RefactoringOpportunity[];
  complianceIssues: ComplianceIssue[];
  optimizationSuggestions: OptimizationSuggestion[];
  codeQualityMetrics: CodeQualityMetrics;
}

export interface SecurityVulnerability {
  id: string;
  type:
    | 'injection'
    | 'authentication'
    | 'authorization'
    | 'data_exposure'
    | 'crypto'
    | 'configuration';
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  nodeId: string;
  recommendation: string;
  cweId?: string;
  estimatedFixTime: number; // hours
}

export interface PerformanceBottleneck {
  id: string;
  type: 'database' | 'network' | 'computation' | 'memory' | 'io';
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  nodeId: string;
  impactMetric: string;
  recommendation: string;
  estimatedImprovement: string;
}

export interface ArchitectureDebt {
  totalScore: number; // 0-100, lower is better
  categories: {
    complexity: number;
    coupling: number;
    cohesion: number;
    testability: number;
    maintainability: number;
  };
  estimatedRefactoringCost: number; // hours
  prioritizedIssues: string[];
}

export interface RefactoringOpportunity {
  id: string;
  type:
    | 'extract_service'
    | 'split_responsibility'
    | 'reduce_coupling'
    | 'improve_naming'
    | 'add_abstraction';
  title: string;
  description: string;
  affectedNodes: string[];
  benefitScore: number; // 1-10
  effortEstimate: number; // hours
  businessValue: string;
}

export interface ComplianceIssue {
  id: string;
  standard: 'SOC2' | 'GDPR' | 'HIPAA' | 'PCI_DSS' | 'ISO27001';
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  nodeId: string;
  requirement: string;
  remediation: string;
}

export interface OptimizationSuggestion {
  id: string;
  category:
    | 'performance'
    | 'scalability'
    | 'maintainability'
    | 'security'
    | 'cost';
  title: string;
  description: string;
  implementation: string;
  expectedBenefit: string;
  priority: number; // 1-5
}

export interface CodeQualityMetrics {
  overallScore: number; // 0-100
  maintainabilityIndex: number;
  cyclomaticComplexity: number;
  technicalDebtRatio: number;
  testCoverage: number;
  duplicationRatio: number;
  documentationScore: number;
}

// Placeholder for AI Model Configuration
const aiModelConfig = {
  model: 'llama3-8b-8192',
};

export class AdvancedAIAnalyzer {
  constructor(private template: Template) {}

  async analyzeArchitecture(
    nodes: GraphNode[],
    edges: GraphEdge[],
    projectId: string
  ): Promise<AdvancedAIInsights> {
    const [
      securityVulnerabilities,
      performanceBottlenecks,
      architectureDebt,
      refactoringOpportunities,
      complianceIssues,
      optimizationSuggestions,
      codeQualityMetrics,
    ] = await Promise.all([
      this.analyzeSecurityVulnerabilities(nodes, edges),
      this.analyzePerformanceBottlenecks(nodes, edges),
      this.calculateArchitectureDebt(nodes, edges),
      this.identifyRefactoringOpportunities(nodes, edges),
      this.checkComplianceIssues(nodes, edges),
      this.generateOptimizationSuggestions(nodes, edges),
      this.calculateCodeQualityMetrics(nodes, edges),
    ]);

    return {
      securityVulnerabilities,
      performanceBottlenecks,
      architectureDebt,
      refactoringOpportunities,
      complianceIssues,
      optimizationSuggestions,
      codeQualityMetrics,
    };
  }

  private async analyzeSecurityVulnerabilities(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): Promise<SecurityVulnerability[]> {
    const vulnerabilities: SecurityVulnerability[] = [];

    for (const node of nodes) {
      // Analyze based on node type and template patterns
      if (node.type === 'controller') {
        // Check for authentication/authorization issues
        const hasAuthGuard = this.hasSecurityPattern(node, 'authentication');
        if (!hasAuthGuard) {
          vulnerabilities.push({
            id: `auth-${node.id}`,
            type: 'authentication',
            severity: 'high',
            title: 'Missing Authentication Guard',
            description: `Controller ${node.name} lacks proper authentication mechanisms`,
            nodeId: node.id,
            recommendation:
              'Implement JWT or session-based authentication guard',
            cweId: 'CWE-306',
            estimatedFixTime: 2,
          });
        }

        // Check for input validation
        if (!this.hasInputValidation(node)) {
          vulnerabilities.push({
            id: `injection-${node.id}`,
            type: 'injection',
            severity: 'critical',
            title: 'Potential Injection Vulnerability',
            description: `Controller ${node.name} may be vulnerable to injection attacks`,
            nodeId: node.id,
            recommendation:
              'Implement input validation using DTOs and validation pipes',
            cweId: 'CWE-89',
            estimatedFixTime: 4,
          });
        }
      }

      if (node.type === 'repository') {
        // Check for SQL injection risks
        if (!this.hasParameterizedQueries(node)) {
          vulnerabilities.push({
            id: `sql-${node.id}`,
            type: 'injection',
            severity: 'high',
            title: 'SQL Injection Risk',
            description: `Repository ${node.name} may use unsafe query construction`,
            nodeId: node.id,
            recommendation: 'Use parameterized queries or ORM query builders',
            cweId: 'CWE-89',
            estimatedFixTime: 3,
          });
        }
      }
    }

    return vulnerabilities;
  }

  private async analyzePerformanceBottlenecks(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): Promise<PerformanceBottleneck[]> {
    const bottlenecks: PerformanceBottleneck[] = [];

    // Analyze node relationships for performance issues
    for (const node of nodes) {
      const incomingEdges = edges.filter(e => e.targetNodeId === node.id);
      const outgoingEdges = edges.filter(e => e.sourceNodeId === node.id);

      // High fan-in indicates potential bottleneck
      if (incomingEdges.length > 5) {
        bottlenecks.push({
          id: `fanin-${node.id}`,
          type: 'computation',
          severity: 'medium',
          title: 'High Fan-in Bottleneck',
          description: `${node.name} has ${incomingEdges.length} dependencies, creating potential bottleneck`,
          nodeId: node.id,
          impactMetric: `${incomingEdges.length} incoming dependencies`,
          recommendation:
            'Consider splitting responsibilities or implementing caching',
          estimatedImprovement: '20-40% response time reduction',
        });
      }

      // Repository without caching
      if (node.type === 'repository' && !this.hasCaching(node)) {
        bottlenecks.push({
          id: `cache-${node.id}`,
          type: 'database',
          severity: 'medium',
          title: 'Missing Database Caching',
          description: `Repository ${node.name} lacks caching mechanism`,
          nodeId: node.id,
          impactMetric: 'Database query frequency',
          recommendation:
            'Implement Redis or in-memory caching for frequently accessed data',
          estimatedImprovement: '50-80% database load reduction',
        });
      }

      // Service without async patterns
      if (node.type === 'service' && !this.hasAsyncPatterns(node)) {
        bottlenecks.push({
          id: `async-${node.id}`,
          type: 'io',
          severity: 'low',
          title: 'Synchronous Processing',
          description: `Service ${node.name} may benefit from asynchronous processing`,
          nodeId: node.id,
          impactMetric: 'Request processing time',
          recommendation: 'Implement async/await patterns for I/O operations',
          estimatedImprovement: '15-30% throughput increase',
        });
      }
    }

    return bottlenecks;
  }

  private async calculateArchitectureDebt(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): Promise<ArchitectureDebt> {
    const complexity = this.calculateComplexityScore(nodes, edges);
    const coupling = this.calculateCouplingScore(nodes, edges);
    const cohesion = this.calculateCohesionScore(nodes, edges);
    const testability = this.calculateTestabilityScore(nodes);
    const maintainability = this.calculateMaintainabilityScore(nodes, edges);

    const totalScore =
      (complexity + coupling + cohesion + testability + maintainability) / 5;
    const estimatedRefactoringCost = Math.ceil(
      nodes.length * 0.5 + edges.length * 0.3
    );

    return {
      totalScore,
      categories: {
        complexity,
        coupling,
        cohesion,
        testability,
        maintainability,
      },
      estimatedRefactoringCost,
      prioritizedIssues: this.getPrioritizedIssues(nodes, edges),
    };
  }

  private async identifyRefactoringOpportunities(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): Promise<RefactoringOpportunity[]> {
    const opportunities: RefactoringOpportunity[] = [];

    // Identify large services that should be split
    const largeServices = nodes.filter(
      n =>
        n.type === 'service' &&
        edges.filter(e => e.sourceNodeId === n.id).length > 3
    );

    for (const service of largeServices) {
      opportunities.push({
        id: `split-${service.id}`,
        type: 'split_responsibility',
        title: `Split ${service.name} Service`,
        description:
          'Large service with multiple responsibilities should be decomposed',
        affectedNodes: [service.id],
        benefitScore: 8,
        effortEstimate: 16,
        businessValue: 'Improved maintainability and team productivity',
      });
    }

    // Identify tightly coupled components
    const coupledPairs = this.findTightlyCoupledNodes(nodes, edges);
    for (const pair of coupledPairs) {
      opportunities.push({
        id: `decouple-${pair[0]}-${pair[1]}`,
        type: 'reduce_coupling',
        title: 'Reduce Coupling Between Components',
        description: 'High coupling detected between components',
        affectedNodes: pair,
        benefitScore: 7,
        effortEstimate: 8,
        businessValue: 'Increased flexibility and reduced change impact',
      });
    }

    return opportunities;
  }

  private async checkComplianceIssues(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): Promise<ComplianceIssue[]> {
    const issues: ComplianceIssue[] = [];

    for (const node of nodes) {
      // GDPR compliance checks
      if (node.type === 'entity' && this.containsPersonalData(node)) {
        if (!this.hasDataEncryption(node)) {
          issues.push({
            id: `gdpr-encryption-${node.id}`,
            standard: 'GDPR',
            category: 'Data Protection',
            severity: 'high',
            description: `Entity ${node.name} contains personal data without encryption`,
            nodeId: node.id,
            requirement: 'Article 32 - Security of processing',
            remediation: 'Implement field-level encryption for personal data',
          });
        }

        if (!this.hasDataRetentionPolicy(node)) {
          issues.push({
            id: `gdpr-retention-${node.id}`,
            standard: 'GDPR',
            category: 'Data Retention',
            severity: 'medium',
            description: `Entity ${node.name} lacks data retention policy`,
            nodeId: node.id,
            requirement: 'Article 5 - Principles relating to processing',
            remediation:
              'Implement automated data retention and deletion policies',
          });
        }
      }

      // SOC2 compliance checks
      if (node.type === 'controller' && !this.hasAuditLogging(node)) {
        issues.push({
          id: `soc2-audit-${node.id}`,
          standard: 'SOC2',
          category: 'Monitoring',
          severity: 'medium',
          description: `Controller ${node.name} lacks comprehensive audit logging`,
          nodeId: node.id,
          requirement: 'CC6.1 - Logical and physical access controls',
          remediation: 'Implement detailed audit logging for all user actions',
        });
      }
    }

    return issues;
  }

  private async generateOptimizationSuggestions(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): Promise<OptimizationSuggestion[]> {
    const suggestions: OptimizationSuggestion[] = [];

    // Database optimization suggestions
    const repositories = nodes.filter(n => n.type === 'repository');
    if (repositories.length > 3) {
      suggestions.push({
        id: 'db-connection-pooling',
        category: 'performance',
        title: 'Implement Database Connection Pooling',
        description:
          'Multiple repositories detected - optimize database connections',
        implementation:
          'Configure connection pool with appropriate size limits',
        expectedBenefit: '30-50% reduction in database connection overhead',
        priority: 4,
      });
    }

    // Caching strategy suggestions
    suggestions.push({
      id: 'implement-caching-strategy',
      category: 'performance',
      title: 'Implement Multi-Layer Caching Strategy',
      description: 'Add caching at service and repository layers',
      implementation:
        'Redis for distributed caching, in-memory for frequently accessed data',
      expectedBenefit: '40-70% response time improvement',
      priority: 5,
    });

    // Monitoring and observability
    suggestions.push({
      id: 'add-observability',
      category: 'maintainability',
      title: 'Enhance Observability',
      description: 'Add comprehensive monitoring and tracing',
      implementation: 'Implement OpenTelemetry with metrics, traces, and logs',
      expectedBenefit: 'Faster debugging and performance optimization',
      priority: 3,
    });

    return suggestions;
  }

  private async calculateCodeQualityMetrics(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): Promise<CodeQualityMetrics> {
    const maintainabilityIndex = this.calculateMaintainabilityIndex(
      nodes,
      edges
    );
    const cyclomaticComplexity = this.calculateCyclomaticComplexity(
      nodes,
      edges
    );
    const technicalDebtRatio = this.calculateTechnicalDebtRatio(nodes, edges);
    const testCoverage = this.estimateTestCoverage(nodes);
    const duplicationRatio = this.calculateDuplicationRatio(nodes);
    const documentationScore = this.calculateDocumentationScore(nodes);

    const overallScore =
      (maintainabilityIndex +
        (100 - cyclomaticComplexity) +
        (100 - technicalDebtRatio) +
        testCoverage +
        (100 - duplicationRatio) +
        documentationScore) /
      6;

    return {
      overallScore,
      maintainabilityIndex,
      cyclomaticComplexity,
      technicalDebtRatio,
      testCoverage,
      duplicationRatio,
      documentationScore,
    };
  }

  // Helper methods for analysis
  private hasSecurityPattern(node: GraphNode, pattern: string): boolean {
    return (
      node.metadata &&
      typeof node.metadata === 'object' &&
      'securityPatterns' in node.metadata
    );
  }

  private hasInputValidation(node: GraphNode): boolean {
    return (
      node.name.toLowerCase().includes('validation') ||
      (node.metadata && 'validation' in (node.metadata as any)) ||
      false
    );
  }

  private hasParameterizedQueries(node: GraphNode): boolean {
    return (
      node.name.toLowerCase().includes('orm') ||
      node.name.toLowerCase().includes('query')
    );
  }

  private hasCaching(node: GraphNode): boolean {
    return (
      node.name.toLowerCase().includes('cache') ||
      (node.metadata && 'caching' in (node.metadata as any))
    );
  }

  private hasAsyncPatterns(node: GraphNode): boolean {
    return (
      node.name.toLowerCase().includes('async') ||
      (node.metadata && 'async' in (node.metadata as any))
    );
  }

  private calculateComplexityScore(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): number {
    const avgConnections = edges.length / nodes.length;
    return Math.min(100, avgConnections * 10);
  }

  private calculateCouplingScore(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): number {
    const maxConnections = Math.max(
      ...nodes.map(
        n =>
          edges.filter(e => e.sourceNodeId === n.id || e.targetNodeId === n.id)
            .length
      )
    );
    return Math.min(100, maxConnections * 5);
  }

  private calculateCohesionScore(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): number {
    // Lower cohesion = higher score (worse)
    const typeGroups = nodes.reduce(
      (acc, node) => {
        acc[node.type] = (acc[node.type] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );

    const cohesionScore =
      Object.values(typeGroups).reduce((sum, count) => sum + count * count, 0) /
      (nodes.length * nodes.length);
    return (1 - cohesionScore) * 100;
  }

  private calculateTestabilityScore(nodes: GraphNode[]): number {
    const testableNodes = nodes.filter(
      n =>
        n.type === 'service' ||
        n.type === 'controller' ||
        n.type === 'repository'
    ).length;
    const totalNodes = nodes.length;
    return (testableNodes / totalNodes) * 100;
  }

  private calculateMaintainabilityScore(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): number {
    const complexity = this.calculateComplexityScore(nodes, edges);
    const coupling = this.calculateCouplingScore(nodes, edges);
    return 100 - (complexity + coupling) / 2;
  }

  private getPrioritizedIssues(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): string[] {
    return [
      'High coupling between services',
      'Missing authentication guards',
      'No caching strategy implemented',
      'Limited error handling',
    ];
  }

  private findTightlyCoupledNodes(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): string[][] {
    const pairs: string[][] = [];
    for (const node of nodes) {
      const connections = edges.filter(
        e => e.sourceNodeId === node.id || e.targetNodeId === node.id
      );
      if (connections.length > 3) {
        const connectedNodes = connections.map(e =>
          e.sourceNodeId === node.id ? e.targetNodeId : e.sourceNodeId
        );
        pairs.push([node.id, ...connectedNodes.slice(0, 2)]);
      }
    }
    return pairs;
  }

  private containsPersonalData(node: GraphNode): boolean {
    const personalDataFields = ['email', 'name', 'phone', 'address', 'user'];
    return personalDataFields.some(field =>
      node.name.toLowerCase().includes(field)
    );
  }

  private hasDataEncryption(node: GraphNode): boolean {
    return node.metadata && 'encryption' in (node.metadata as any);
  }

  private hasDataRetentionPolicy(node: GraphNode): boolean {
    return node.metadata && 'retention' in (node.metadata as any);
  }

  private hasAuditLogging(node: GraphNode): boolean {
    return node.metadata && 'audit' in (node.metadata as any);
  }

  private calculateMaintainabilityIndex(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): number {
    // Simplified maintainability index
    const complexity = edges.length / nodes.length;
    return Math.max(0, 100 - complexity * 10);
  }

  private calculateCyclomaticComplexity(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): number {
    // Approximation based on graph structure
    return Math.min(50, edges.length - nodes.length + 2);
  }

  private calculateTechnicalDebtRatio(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): number {
    // Based on coupling and complexity
    const coupling = this.calculateCouplingScore(nodes, edges);
    const complexity = this.calculateComplexityScore(nodes, edges);
    return (coupling + complexity) / 2;
  }

  private estimateTestCoverage(nodes: GraphNode[]): number {
    // Estimate based on node types that typically have tests
    const testableNodes = nodes.filter(n =>
      ['service', 'controller', 'repository'].includes(n.type)
    ).length;
    return Math.min(100, (testableNodes / nodes.length) * 80);
  }

  private calculateDuplicationRatio(nodes: GraphNode[]): number {
    // Simple duplication detection based on similar names
    const nameGroups = nodes.reduce(
      (acc, node) => {
        const baseName = node.name.toLowerCase().replace(/\d+$/, '');
        acc[baseName] = (acc[baseName] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );

    const duplicates = Object.values(nameGroups).filter(
      count => count > 1
    ).length;
    return (duplicates / nodes.length) * 100;
  }

  private calculateDocumentationScore(nodes: GraphNode[]): number {
    const documentedNodes = nodes.filter(
      n => n.description && n.description.trim().length > 10
    ).length;
    return (documentedNodes / nodes.length) * 100;
  }
}
