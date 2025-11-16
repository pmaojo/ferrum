/**
 * Relationship Analyzer
 * 
 * Implements code dependency analysis using AST parsing and import tracking,
 * requirement linkage detection through semantic similarity, and architectural
 * pattern recognition using graph topology analysis.
 */

import * as ts from 'typescript';
import * as fs from 'fs';
import * as path from 'path';
import { performance } from 'node:perf_hooks';
import { logger } from '../utils/logger';

// Core interfaces for relationship analysis
export interface CodeDependency {
  source: string;
  target: string;
  type: 'import' | 'extends' | 'implements' | 'calls' | 'instantiates';
  strength: number;
  location: SourceLocation;
  metadata: DependencyMetadata;
}

export interface SourceLocation {
  file: string;
  line: number;
  column: number;
  endLine?: number;
  endColumn?: number;
}

export interface DependencyMetadata {
  isExternal: boolean;
  packageName?: string;
  version?: string;
  framework?: string;
  category: 'business' | 'infrastructure' | 'presentation' | 'utility';
  cyclic: boolean;
}

export interface RequirementLinkage {
  sourceRequirement: string;
  targetRequirement: string;
  linkageType: 'depends_on' | 'conflicts_with' | 'enhances' | 'implements';
  similarity: number;
  confidence: number;
  evidence: LinkageEvidence[];
}

export interface LinkageEvidence {
  type: 'semantic' | 'structural' | 'historical' | 'explicit';
  description: string;
  weight: number;
  source: string;
}

export interface ArchitecturalPattern {
  id: string;
  name: string;
  type: 'hexagonal' | 'layered' | 'microservices' | 'event_driven' | 'cqrs';
  confidence: number;
  components: PatternComponent[];
  violations: PatternViolation[];
  compliance: PatternCompliance;
}

export interface PatternComponent {
  name: string;
  role: string;
  files: string[];
  dependencies: string[];
  interfaces: string[];
}

export interface PatternViolation {
  type: string;
  severity: 'high' | 'medium' | 'low';
  description: string;
  location: SourceLocation;
  suggestion: string;
}

export interface PatternCompliance {
  score: number;
  maxScore: number;
  details: ComplianceDetail[];
}

export interface ComplianceDetail {
  rule: string;
  status: 'compliant' | 'partial' | 'violated';
  description: string;
}

export interface DependencyGraph {
  nodes: DependencyNode[];
  edges: DependencyEdge[];
  cycles: DependencyCycle[];
  metrics: GraphMetrics;
}

export interface DependencyNode {
  id: string;
  name: string;
  type: 'module' | 'class' | 'function' | 'interface';
  layer: 'domain' | 'application' | 'infrastructure' | 'presentation';
  framework?: string;
  metadata: NodeMetadata;
}

export interface DependencyEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
  metadata: EdgeMetadata;
}

export interface DependencyCycle {
  nodes: string[];
  length: number;
  severity: 'high' | 'medium' | 'low';
  breakSuggestions: string[];
}

export interface GraphMetrics {
  nodeCount: number;
  edgeCount: number;
  density: number;
  averageDegree: number;
  cycleCount: number;
  maxDepth: number;
}

export interface NodeMetadata {
  loc: number;
  complexity: number;
  fanIn: number;
  fanOut: number;
  stability: number;
}

export interface EdgeMetadata {
  frequency: number;
  lastModified: Date;
  changeImpact: number;
}

/**
 * Relationship Analyzer - Main class for analyzing code relationships and patterns
 */
export class RelationshipAnalyzer {
  private dependencyCache: Map<string, CodeDependency[]> = new Map();
  private requirementCache: Map<string, RequirementLinkage[]> = new Map();
  private patternCache: Map<string, ArchitecturalPattern[]> = new Map();

  constructor(private projectRoot: string) {}

  /**
   * Analyze code dependencies using AST parsing and import tracking
   */
  async analyzeCodeDependencies(filePaths: string[]): Promise<CodeDependency[]> {
    const startTime = performance.now();
    const dependencies: CodeDependency[] = [];

    try {
      for (const filePath of filePaths) {
        const cachedDeps = this.dependencyCache.get(filePath);
        if (cachedDeps) {
          dependencies.push(...cachedDeps);
          continue;
        }

        const fileDependencies = await this.analyzeFileDependencies(filePath);
        dependencies.push(...fileDependencies);
        this.dependencyCache.set(filePath, fileDependencies);
      }

      // Analyze cross-file dependencies
      const crossFileDeps = this.analyzeCrossFileDependencies(dependencies);
      dependencies.push(...crossFileDeps);

      const endTime = performance.now();
      logger.info('Code dependency analysis completed', {
        fileCount: filePaths.length,
        dependencyCount: dependencies.length,
        duration: endTime - startTime
      });

      return dependencies;
    } catch (error) {
      logger.error('Error analyzing code dependencies', error as Error);
      throw error;
    }
  }

  /**
   * Analyze dependencies for a single file using TypeScript AST
   */
  private async analyzeFileDependencies(filePath: string): Promise<CodeDependency[]> {
    const dependencies: CodeDependency[] = [];
    
    try {
      const sourceCode = fs.readFileSync(filePath, 'utf-8');
      const sourceFile = ts.createSourceFile(
        filePath,
        sourceCode,
        ts.ScriptTarget.Latest,
        true
      );

      // Visit AST nodes to extract dependencies
      const visit = (node: ts.Node) => {
        // Import declarations
        if (ts.isImportDeclaration(node)) {
          const importDep = this.extractImportDependency(node, filePath, sourceFile);
          if (importDep) dependencies.push(importDep);
        }

        // Class extends
        if (ts.isClassDeclaration(node) && node.heritageClauses) {
          const extendsDeps = this.extractHeritageDependencies(node, filePath, sourceFile);
          dependencies.push(...extendsDeps);
        }

        // Function calls
        if (ts.isCallExpression(node)) {
          const callDep = this.extractCallDependency(node, filePath, sourceFile);
          if (callDep) dependencies.push(callDep);
        }

        // New expressions
        if (ts.isNewExpression(node)) {
          const newDep = this.extractNewDependency(node, filePath, sourceFile);
          if (newDep) dependencies.push(newDep);
        }

        ts.forEachChild(node, visit);
      };

      visit(sourceFile);
      return dependencies;
    } catch (error) {
      logger.warn(`Failed to analyze dependencies for ${filePath}`, error as Error);
      return [];
    }
  }

  /**
   * Extract import dependency from AST node
   */
  private extractImportDependency(
    node: ts.ImportDeclaration,
    filePath: string,
    sourceFile: ts.SourceFile
  ): CodeDependency | null {
    if (!node.moduleSpecifier || !ts.isStringLiteral(node.moduleSpecifier)) {
      return null;
    }

    const moduleName = node.moduleSpecifier.text;
    const location = this.getSourceLocation(node, sourceFile);
    const isExternal = !moduleName.startsWith('.') && !moduleName.startsWith('/');

    return {
      source: filePath,
      target: moduleName,
      type: 'import',
      strength: 1.0,
      location,
      metadata: {
        isExternal,
        packageName: isExternal ? moduleName.split('/')[0] : undefined,
        framework: this.detectFramework(moduleName),
        category: this.categorizeImport(moduleName),
        cyclic: false // Will be determined later
      }
    };
  }

  /**
   * Extract heritage (extends/implements) dependencies
   */
  private extractHeritageDependencies(
    node: ts.ClassDeclaration,
    filePath: string,
    sourceFile: ts.SourceFile
  ): CodeDependency[] {
    const dependencies: CodeDependency[] = [];

    if (!node.heritageClauses) return dependencies;

    for (const clause of node.heritageClauses) {
      for (const type of clause.types) {
        const typeName = type.expression.getText(sourceFile);
        const location = this.getSourceLocation(type, sourceFile);
        const depType = clause.token === ts.SyntaxKind.ExtendsKeyword ? 'extends' : 'implements';

        dependencies.push({
          source: filePath,
          target: typeName,
          type: depType,
          strength: 0.8,
          location,
          metadata: {
            isExternal: false,
            framework: this.detectFramework(typeName),
            category: 'business',
            cyclic: false
          }
        });
      }
    }

    return dependencies;
  }

  /**
   * Extract call expression dependency
   */
  private extractCallDependency(
    node: ts.CallExpression,
    filePath: string,
    sourceFile: ts.SourceFile
  ): CodeDependency | null {
    const expression = node.expression.getText(sourceFile);
    const location = this.getSourceLocation(node, sourceFile);

    // Skip built-in functions and simple identifiers
    if (!expression.includes('.') || expression.length < 3) {
      return null;
    }

    return {
      source: filePath,
      target: expression,
      type: 'calls',
      strength: 0.6,
      location,
      metadata: {
        isExternal: false,
        framework: this.detectFramework(expression),
        category: 'utility',
        cyclic: false
      }
    };
  }

  /**
   * Extract new expression dependency
   */
  private extractNewDependency(
    node: ts.NewExpression,
    filePath: string,
    sourceFile: ts.SourceFile
  ): CodeDependency | null {
    const expression = node.expression.getText(sourceFile);
    const location = this.getSourceLocation(node, sourceFile);

    return {
      source: filePath,
      target: expression,
      type: 'instantiates',
      strength: 0.7,
      location,
      metadata: {
        isExternal: false,
        framework: this.detectFramework(expression),
        category: 'business',
        cyclic: false
      }
    };
  }

  /**
   * Analyze cross-file dependencies and detect cycles
   */
  private analyzeCrossFileDependencies(dependencies: CodeDependency[]): CodeDependency[] {
    const crossFileDeps: CodeDependency[] = [];
    const fileGraph = this.buildFileGraph(dependencies);

    // Detect cycles
    const cycles = this.detectCycles(fileGraph);
    
    // Mark cyclic dependencies
    for (const cycle of cycles) {
      for (let i = 0; i < cycle.length; i++) {
        const source = cycle[i];
        const target = cycle[(i + 1) % cycle.length];
        
        const dep = dependencies.find(d => 
          d.source.includes(source) && d.target.includes(target)
        );
        
        if (dep) {
          dep.metadata.cyclic = true;
        }
      }
    }

    return crossFileDeps;
  }

  /**
   * Detect requirement linkages through semantic similarity
   */
  async detectRequirementLinkages(
    requirements: string[],
    context: string
  ): Promise<RequirementLinkage[]> {
    const startTime = performance.now();
    const linkages: RequirementLinkage[] = [];

    try {
      for (let i = 0; i < requirements.length; i++) {
        for (let j = i + 1; j < requirements.length; j++) {
          const req1 = requirements[i];
          const req2 = requirements[j];
          
          const linkage = await this.analyzeRequirementSimilarity(req1, req2, context);
          if (linkage && linkage.similarity > 0.3) {
            linkages.push(linkage);
          }
        }
      }

      const endTime = performance.now();
      logger.info('Requirement linkage analysis completed', {
        requirementCount: requirements.length,
        linkageCount: linkages.length,
        duration: endTime - startTime
      });

      return linkages;
    } catch (error) {
      logger.error('Error detecting requirement linkages', error as Error);
      throw error;
    }
  }

  /**
   * Analyze semantic similarity between two requirements
   */
  private async analyzeRequirementSimilarity(
    req1: string,
    req2: string,
    context: string
  ): Promise<RequirementLinkage | null> {
    // Simple keyword-based similarity for now
    // In a real implementation, this would use NLP/ML models
    const keywords1 = this.extractKeywords(req1);
    const keywords2 = this.extractKeywords(req2);
    
    const commonKeywords = keywords1.filter(k => keywords2.includes(k));
    const similarity = commonKeywords.length / Math.max(keywords1.length, keywords2.length);
    
    if (similarity < 0.1) return null;

    const linkageType = this.determineLinkageType(req1, req2, commonKeywords);
    const evidence = this.generateLinkageEvidence(req1, req2, commonKeywords, context);

    return {
      sourceRequirement: req1,
      targetRequirement: req2,
      linkageType,
      similarity,
      confidence: similarity * 0.8, // Adjust confidence based on method reliability
      evidence
    };
  }

  /**
   * Recognize architectural patterns using graph topology analysis
   */
  async recognizeArchitecturalPatterns(
    dependencyGraph: DependencyGraph
  ): Promise<ArchitecturalPattern[]> {
    const startTime = performance.now();
    const patterns: ArchitecturalPattern[] = [];

    try {
      // Detect hexagonal architecture pattern
      const hexagonalPattern = this.detectHexagonalPattern(dependencyGraph);
      if (hexagonalPattern) patterns.push(hexagonalPattern);

      // Detect layered architecture pattern
      const layeredPattern = this.detectLayeredPattern(dependencyGraph);
      if (layeredPattern) patterns.push(layeredPattern);

      // Detect microservices pattern
      const microservicesPattern = this.detectMicroservicesPattern(dependencyGraph);
      if (microservicesPattern) patterns.push(microservicesPattern);

      // Detect event-driven pattern
      const eventDrivenPattern = this.detectEventDrivenPattern(dependencyGraph);
      if (eventDrivenPattern) patterns.push(eventDrivenPattern);

      const endTime = performance.now();
      logger.info('Architectural pattern recognition completed', {
        patternCount: patterns.length,
        duration: endTime - startTime
      });

      return patterns;
    } catch (error) {
      logger.error('Error recognizing architectural patterns', error as Error);
      throw error;
    }
  }

  /**
   * Detect hexagonal architecture pattern
   */
  private detectHexagonalPattern(graph: DependencyGraph): ArchitecturalPattern | null {
    const domainNodes = graph.nodes.filter(n => n.layer === 'domain');
    const applicationNodes = graph.nodes.filter(n => n.layer === 'application');
    const infrastructureNodes = graph.nodes.filter(n => n.layer === 'infrastructure');

    if (domainNodes.length === 0) return null;

    // Check for proper dependency direction (infrastructure -> application -> domain)
    const violations: PatternViolation[] = [];
    let complianceScore = 0;
    const maxScore = 100;

    // Rule 1: Domain should not depend on infrastructure
    const domainToInfraEdges = graph.edges.filter(e => 
      domainNodes.some(n => n.id === e.source) &&
      infrastructureNodes.some(n => n.id === e.target)
    );

    if (domainToInfraEdges.length === 0) {
      complianceScore += 40;
    } else {
      domainToInfraEdges.forEach(edge => {
        violations.push({
          type: 'DIP_VIOLATION',
          severity: 'high',
          description: 'Domain layer depends on infrastructure layer',
          location: { file: edge.source, line: 1, column: 1 },
          suggestion: 'Create a port interface to invert the dependency'
        });
      });
    }

    // Rule 2: Application layer should orchestrate domain
    const appToDomainEdges = graph.edges.filter(e =>
      applicationNodes.some(n => n.id === e.source) &&
      domainNodes.some(n => n.id === e.target)
    );

    if (appToDomainEdges.length > 0) {
      complianceScore += 30;
    }

    // Rule 3: Infrastructure should implement application interfaces
    const infraToAppEdges = graph.edges.filter(e =>
      infrastructureNodes.some(n => n.id === e.source) &&
      applicationNodes.some(n => n.id === e.target)
    );

    if (infraToAppEdges.length > 0) {
      complianceScore += 30;
    }

    const confidence = complianceScore / maxScore;
    if (confidence < 0.5) return null;

    return {
      id: 'hexagonal-architecture',
      name: 'Hexagonal Architecture',
      type: 'hexagonal',
      confidence,
      components: [
        {
          name: 'Domain',
          role: 'Core business logic',
          files: domainNodes.map(n => n.id),
          dependencies: [],
          interfaces: []
        },
        {
          name: 'Application',
          role: 'Use cases and orchestration',
          files: applicationNodes.map(n => n.id),
          dependencies: domainNodes.map(n => n.id),
          interfaces: []
        },
        {
          name: 'Infrastructure',
          role: 'External adapters',
          files: infrastructureNodes.map(n => n.id),
          dependencies: applicationNodes.map(n => n.id),
          interfaces: []
        }
      ],
      violations,
      compliance: {
        score: complianceScore,
        maxScore,
        details: [
          {
            rule: 'Dependency Inversion',
            status: domainToInfraEdges.length === 0 ? 'compliant' : 'violated',
            description: 'Domain should not depend on infrastructure'
          },
          {
            rule: 'Application Orchestration',
            status: appToDomainEdges.length > 0 ? 'compliant' : 'partial',
            description: 'Application should orchestrate domain logic'
          },
          {
            rule: 'Infrastructure Implementation',
            status: infraToAppEdges.length > 0 ? 'compliant' : 'partial',
            description: 'Infrastructure should implement application interfaces'
          }
        ]
      }
    };
  }

  /**
   * Detect layered architecture pattern
   */
  private detectLayeredPattern(graph: DependencyGraph): ArchitecturalPattern | null {
    const layers = ['presentation', 'application', 'domain', 'infrastructure'];
    const layerNodes = layers.map(layer => ({
      layer,
      nodes: graph.nodes.filter(n => n.layer === layer)
    }));

    // Check if we have nodes in multiple layers
    const populatedLayers = layerNodes.filter(l => l.nodes.length > 0);
    if (populatedLayers.length < 3) return null;

    const violations: PatternViolation[] = [];
    let complianceScore = 0;
    const maxScore = 100;

    // Check layer dependency rules
    for (let i = 0; i < layers.length - 1; i++) {
      const upperLayer = layers[i];
      const lowerLayer = layers[i + 1];
      
      const upperNodes = graph.nodes.filter(n => n.layer === upperLayer);
      const lowerNodes = graph.nodes.filter(n => n.layer === lowerLayer);
      
      // Upper layer can depend on lower layer
      const validEdges = graph.edges.filter(e =>
        upperNodes.some(n => n.id === e.source) &&
        lowerNodes.some(n => n.id === e.target)
      );

      // Lower layer should not depend on upper layer
      const invalidEdges = graph.edges.filter(e =>
        lowerNodes.some(n => n.id === e.source) &&
        upperNodes.some(n => n.id === e.target)
      );

      if (invalidEdges.length === 0) {
        complianceScore += 25;
      } else {
        invalidEdges.forEach(edge => {
          violations.push({
            type: 'LAYER_VIOLATION',
            severity: 'high',
            description: `${lowerLayer} layer depends on ${upperLayer} layer`,
            location: { file: edge.source, line: 1, column: 1 },
            suggestion: 'Refactor to follow layered architecture principles'
          });
        });
      }
    }

    const confidence = complianceScore / maxScore;
    if (confidence < 0.6) return null;

    return {
      id: 'layered-architecture',
      name: 'Layered Architecture',
      type: 'layered',
      confidence,
      components: populatedLayers.map(l => ({
        name: l.layer,
        role: `${l.layer} layer`,
        files: l.nodes.map(n => n.id),
        dependencies: [],
        interfaces: []
      })),
      violations,
      compliance: {
        score: complianceScore,
        maxScore,
        details: layers.map(layer => ({
          rule: `${layer} Layer Compliance`,
          status: 'compliant',
          description: `${layer} layer follows architectural rules`
        }))
      }
    };
  }

  // Helper methods
  private getSourceLocation(node: ts.Node, sourceFile: ts.SourceFile): SourceLocation {
    const start = sourceFile.getLineAndCharacterOfPosition(node.getStart());
    const end = sourceFile.getLineAndCharacterOfPosition(node.getEnd());
    
    return {
      file: sourceFile.fileName,
      line: start.line + 1,
      column: start.character + 1,
      endLine: end.line + 1,
      endColumn: end.character + 1
    };
  }

  private detectFramework(moduleName: string): string | undefined {
    const frameworkPatterns = {
      'react': /^react/,
      'angular': /^@angular/,
      'vue': /^vue/,
      'express': /^express/,
      'nestjs': /^@nestjs/,
      'kthulu': /kthulu/,
      'tuetano': /tuetano/,
      'ferrum': /ferrum/
    };

    for (const [framework, pattern] of Object.entries(frameworkPatterns)) {
      if (pattern.test(moduleName)) {
        return framework;
      }
    }

    return undefined;
  }

  private categorizeImport(moduleName: string): 'business' | 'infrastructure' | 'presentation' | 'utility' {
    if (moduleName.includes('ui') || moduleName.includes('component')) {
      return 'presentation';
    }
    if (moduleName.includes('db') || moduleName.includes('api') || moduleName.includes('http')) {
      return 'infrastructure';
    }
    if (moduleName.includes('util') || moduleName.includes('helper')) {
      return 'utility';
    }
    return 'business';
  }

  private buildFileGraph(dependencies: CodeDependency[]): Map<string, string[]> {
    const graph = new Map<string, string[]>();
    
    dependencies.forEach(dep => {
      if (!graph.has(dep.source)) {
        graph.set(dep.source, []);
      }
      graph.get(dep.source)!.push(dep.target);
    });

    return graph;
  }

  private detectCycles(graph: Map<string, string[]>): string[][] {
    const visited = new Set<string>();
    const recursionStack = new Set<string>();
    const cycles: string[][] = [];

    const dfs = (node: string, path: string[]): void => {
      visited.add(node);
      recursionStack.add(node);
      path.push(node);

      const neighbors = graph.get(node) || [];
      for (const neighbor of neighbors) {
        if (recursionStack.has(neighbor)) {
          // Found a cycle
          const cycleStart = path.indexOf(neighbor);
          if (cycleStart !== -1) {
            cycles.push(path.slice(cycleStart));
          }
        } else if (!visited.has(neighbor)) {
          dfs(neighbor, [...path]);
        }
      }

      recursionStack.delete(node);
    };

    for (const node of graph.keys()) {
      if (!visited.has(node)) {
        dfs(node, []);
      }
    }

    return cycles;
  }

  private extractKeywords(text: string): string[] {
    return text
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length > 2)
      .filter(word => !['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'].includes(word));
  }

  private determineLinkageType(
    req1: string,
    req2: string,
    commonKeywords: string[]
  ): 'depends_on' | 'conflicts_with' | 'enhances' | 'implements' {
    const req1Lower = req1.toLowerCase();
    const req2Lower = req2.toLowerCase();

    if (req1Lower.includes('implement') || req2Lower.includes('implement')) {
      return 'implements';
    }
    if (req1Lower.includes('conflict') || req2Lower.includes('conflict')) {
      return 'conflicts_with';
    }
    if (req1Lower.includes('enhance') || req2Lower.includes('enhance')) {
      return 'enhances';
    }
    return 'depends_on';
  }

  private generateLinkageEvidence(
    req1: string,
    req2: string,
    commonKeywords: string[],
    context: string
  ): LinkageEvidence[] {
    return [
      {
        type: 'semantic',
        description: `Common keywords: ${commonKeywords.join(', ')}`,
        weight: 0.6,
        source: 'keyword_analysis'
      },
      {
        type: 'structural',
        description: 'Requirements appear in related context',
        weight: 0.4,
        source: context
      }
    ];
  }

  // Placeholder methods for other pattern detection
  private detectMicroservicesPattern(graph: DependencyGraph): ArchitecturalPattern | null {
    // Implementation would analyze service boundaries and communication patterns
    return null;
  }

  private detectEventDrivenPattern(graph: DependencyGraph): ArchitecturalPattern | null {
    // Implementation would look for event publishers/subscribers
    return null;
  }
}