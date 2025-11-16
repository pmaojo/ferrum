import type { Template } from '@shared/schema';

import { analyzeCodebase as basicAnalyze } from '../ast-analyzer';
import { EnhancedASTAnalyzer } from '../enhanced-ast-analyzer';
import { SemanticAnalyzer, type ParsedCodeFile } from '../semantic-analyzer';
import { LoggerFactory } from '../services/logging/LoggerFactory';

import type { ICodeAnalyzer, AnalysisResult, ParsedFile } from './types';

/** Basic analyzer wrapper. */
export class BasicASTAnalyzerAdapter implements ICodeAnalyzer {
  constructor(
    private template: Template,
    private projectId: string
  ) {}

  async analyze(files: ParsedFile[]): Promise<AnalysisResult> {
    const multerFiles = files.map(f => ({
      originalname: f.filePath,
      buffer: Buffer.from(f.content),
    })) as Express.Multer.File[];

    const result = await basicAnalyze(
      multerFiles,
      this.template,
      this.projectId
    );

    return {
      nodes: result.nodes,
      edges: result.edges,
      patterns: result.validationResults.map(v => ({
        id: `pattern_${Date.now()}_${Math.random()}`,
        type: v.type,
        confidence: v.severity / 5,
        description: v.message,
        files: v.filePath ? [v.filePath] : [],
      })),
      validationResults: result.validationResults,
    };
  }

  getAnalyzerType(): string {
    return 'BasicASTAnalyzer';
  }
}

/** Enhanced analyzer wrapper adding AI based checks. */
export class EnhancedASTAnalyzerAdapter implements ICodeAnalyzer {
  private analyzer: EnhancedASTAnalyzer;

  constructor(
    private template: Template,
    private projectId: string
  ) {
    this.analyzer = new EnhancedASTAnalyzer(template);
  }

  async analyze(files: ParsedFile[]): Promise<AnalysisResult> {
    const enhancedFiles = files.map(f => ({
      name: f.filePath,
      content: f.content,
    }));
    const result = await this.analyzer.analyzeCodebase(
      enhancedFiles,
      this.projectId
    );
    return {
      nodes: result.nodes,
      edges: result.edges,
      patterns: result.patterns as any,
      validationResults: [],
      businessRules: result.businessRules,
      suggestions: result.suggestions,
    };
  }

  getAnalyzerType(): string {
    return 'EnhancedASTAnalyzer';
  }
}

/** Semantic analyzer wrapper for deep semantic insights. */
export class SemanticAnalyzerAdapter implements ICodeAnalyzer {
  private analyzer: SemanticAnalyzer;

  constructor(
    private template: Template,
    private projectId: string
  ) {
    this.analyzer = new SemanticAnalyzer(template);
  }

  async analyze(files: ParsedFile[]): Promise<AnalysisResult> {
    const semanticFiles: ParsedCodeFile[] = files.map(f => ({
      path: f.filePath,
      content: f.content,
      imports: f.imports,
      exports: f.exports,
      classes: this.extractClasses(f.content),
      functions: this.extractFunctions(f.content),
      interfaces: this.extractInterfaces(f.content),
      decorators: f.metadata.decorators.map(d => ({
        name: d,
        target: '',
        parameters: [],
      })),
      dependencies: f.metadata.dependencies,
      complexity: f.metadata.complexity,
      loc: f.metadata.loc,
    }));

    const result = await this.analyzer.analyzeCodebase(
      semanticFiles,
      this.projectId
    );

    return {
      nodes: result.nodes,
      edges: result.edges,
      patterns: result.patterns,
      validationResults: result.violations.map(v => ({
        type:
          v.severity === 'high'
            ? 'error'
            : v.severity === 'medium'
              ? 'warning'
              : 'info',
        message: v.description,
        filePath: v.file,
        severity: v.severity === 'high' ? 5 : v.severity === 'medium' ? 3 : 1,
      })),
      suggestions: result.suggestions.map(s => s.description),
    };
  }

  private extractClasses(content: string): any[] {
    const matches = content.match(/class\s+(\w+)/g);
    return matches
      ? matches.map(m => ({
          name: m.split(/\s+/)[1],
          decorators: [],
          methods: [],
          properties: [],
        }))
      : [];
  }

  private extractFunctions(content: string): any[] {
    const matches = content.match(/(?:function\s+(\w+)|(\w+)\s*\(.*\)\s*{)/g);
    return matches
      ? matches
          .map(m => {
            const match = m.match(/(?:function\s+(\w+)|(\w+)\s*\()/);
            return {
              name: match ? match[1] || match[2] : '',
              parameters: [],
              isAsync: m.includes('async'),
              decorators: [],
            };
          })
          .filter(f => f.name)
      : [];
  }

  private extractInterfaces(content: string): any[] {
    const matches = content.match(/interface\s+(\w+)/g);
    return matches
      ? matches.map(m => ({
          name: m.split(/\s+/)[1],
          methods: [],
          properties: [],
        }))
      : [];
  }

  getAnalyzerType(): string {
    return 'SemanticAnalyzer';
  }
}

/** Kthulu analyzer wrapper for Go projects with hexagonal architecture. */
export class KthuluAnalyzerAdapter implements ICodeAnalyzer {
  private goParser: any; // Will be imported dynamically
  private logger = LoggerFactory.createUtilityLogger('kthulu-analyzer');

  constructor(
    private template: Template,
    private projectId: string
  ) {}

  async analyze(files: ParsedFile[]): Promise<AnalysisResult> {
    // Check if this is a Kthulu project by looking for Go files and Kthulu structure
    const goFiles = files.filter(f => f.filePath.endsWith('.go'));
    if (goFiles.length === 0) {
      return this.createEmptyResult();
    }

    // Initialize Go parser if not already done
    if (!this.goParser) {
      const { GoASTParser } = await import('../services/go-ast-parser');
      this.goParser = new GoASTParser('.');
    }

    const nodes: any[] = [];
    const edges: any[] = [];
    const patterns: any[] = [];
    const validationResults: any[] = [];

    // Try to detect project root from file paths
    const projectRoot = this.detectProjectRoot(files);

    if (projectRoot) {
      try {
        // Use real AST analysis for comprehensive project analysis
        const elements = await this.goParser.analyzeKthuluProject(projectRoot);

        // Convert architectural elements to SCG format
        elements.forEach((element: any, index: number) => {
          const node = {
            id: element.id,
            name: element.name,
            type: element.type,
            filePath: element.filePath,
            description: `${element.type}: ${element.name}`,
            position: this.calculatePosition(element, index),
            metadata: {
              packagePath: element.packagePath,
              isExported: element.metadata.isExported,
              hasTests: element.metadata.hasTests,
              complexity: element.metadata.complexity,
              kthuluTags: element.metadata.kthuluTags,
              componentType: this.getComponentType(element.type),
            },
            templateId: this.template.id,
            projectId: this.projectId,
          };
          nodes.push(node);
        });

        // Create edges from real dependencies
        elements.forEach((element: any) => {
          element.dependencies.forEach((dep: string, depIndex: number) => {
            const targetElement = elements.find(
              (e: any) =>
                e.packagePath === dep || e.name === dep || dep.includes(e.name)
            );

            if (targetElement) {
              edges.push({
                id: `dep-${element.id}-${targetElement.id}-${depIndex}`,
                sourceNodeId: element.id,
                targetNodeId: targetElement.id,
                type: 'depends',
                metadata: { dependency: dep },
                projectId: this.projectId,
              });
            }
          });
        });

        // Detect architectural patterns
        patterns.push(...this.detectArchitecturalPatterns(elements));
      } catch (error) {
        this.logger.error(
          'Failed to analyze Kthulu project with AST parser',
          error as Error
        );
        // Fallback to simple file-by-file analysis
        return this.fallbackAnalysis(goFiles);
      }
    } else {
      // Fallback to simple file-by-file analysis
      return this.fallbackAnalysis(goFiles);
    }

    // Apply Kthulu-specific validations
    const kthuluValidations = this.validateKthuluArchitecture(nodes, edges);
    validationResults.push(...kthuluValidations);

    return {
      nodes,
      edges,
      patterns,
      validationResults,
      suggestions: this.generateKthuluSuggestions(nodes, edges),
    };
  }

  private detectProjectRoot(files: ParsedFile[]): string | null {
    // Look for Kthulu project indicators
    const indicators = [
      'backend/internal/modules',
      'backend/cmd/kthulu-cli',
      'go.mod',
    ];

    for (const file of files) {
      for (const indicator of indicators) {
        if (file.filePath.includes(indicator)) {
          // Extract project root from file path
          const parts = file.filePath.split('/');
          const indicatorParts = indicator.split('/');
          const rootParts = parts.slice(
            0,
            parts.length - indicatorParts.length
          );
          return rootParts.join('/') || '.';
        }
      }
    }

    return null;
  }

  private fallbackAnalysis(goFiles: ParsedFile[]): AnalysisResult {
    const nodes: any[] = [];
    const edges: any[] = [];
    const patterns: any[] = [];
    const validationResults: any[] = [];

    // Analyze Go files for Kthulu patterns using simple regex
    for (const file of goFiles) {
      const analysis = this.analyzeGoFile(file);
      nodes.push(...analysis.nodes);
      edges.push(...analysis.edges);
      patterns.push(...analysis.patterns);
      validationResults.push(...analysis.validations);
    }

    return {
      nodes,
      edges,
      patterns,
      validationResults,
      suggestions: this.generateKthuluSuggestions(nodes, edges),
    };
  }

  private detectArchitecturalPatterns(elements: any[]): any[] {
    const patterns: any[] = [];

    const modules = elements.filter(e => e.type === 'module');
    const usecases = elements.filter(e => e.type === 'usecase');
    const adapters = elements.filter(e => e.type === 'adapter');
    const entities = elements.filter(e => e.type === 'entity');

    // Detect hexagonal architecture pattern
    if (modules.length > 0 && usecases.length > 0 && adapters.length > 0) {
      patterns.push({
        id: 'hexagonal-architecture',
        type: 'hexagonal-architecture',
        confidence: 0.9,
        description: `Hexagonal architecture detected with ${modules.length} modules, ${usecases.length} use cases, and ${adapters.length} adapters`,
        files: elements.map(e => e.filePath),
      });
    }

    // Detect DDD pattern
    if (entities.length > 0 && usecases.length > 0) {
      patterns.push({
        id: 'domain-driven-design',
        type: 'domain-driven-design',
        confidence: 0.8,
        description: `Domain-Driven Design pattern detected with ${entities.length} entities and ${usecases.length} use cases`,
        files: [...entities, ...usecases].map(e => e.filePath),
      });
    }

    // Detect dependency injection pattern (fx.Options)
    const fxModules = elements.filter(e => e.metadata.fxProvides?.length > 0);
    if (fxModules.length > 0) {
      patterns.push({
        id: 'dependency-injection',
        type: 'dependency-injection',
        confidence: 0.95,
        description: `Dependency injection pattern detected using Uber FX in ${fxModules.length} modules`,
        files: fxModules.map(e => e.filePath),
      });
    }

    return patterns;
  }

  private calculatePosition(
    element: any,
    index: number
  ): { x: number; y: number } {
    const baseX = (index % 6) * 200;
    const baseY = Math.floor(index / 6) * 120;

    // Adjust based on type for better layout
    switch (element.type) {
      case 'module':
        return { x: baseX, y: baseY };
      case 'usecase':
        return { x: baseX + 50, y: baseY + 80 };
      case 'adapter':
        return { x: baseX + 150, y: baseY + 80 };
      case 'entity':
        return { x: baseX + 100, y: baseY + 160 };
      default:
        return { x: baseX, y: baseY };
    }
  }

  private getComponentType(elementType: string): string {
    switch (elementType) {
      case 'usecase':
      case 'entity':
      case 'port':
        return 'domain';
      case 'adapter':
      case 'handler':
        return 'infrastructure';
      case 'service':
        return 'application';
      default:
        return 'unknown';
    }
  }

  private analyzeGoFile(file: ParsedFile): any {
    const nodes: any[] = [];
    const edges: any[] = [];
    const patterns: any[] = [];
    const validations: any[] = [];

    const { content } = file;
    const fileName =
      file.filePath.split('/').pop()?.replace('.go', '') || 'unknown';

    // Extract modules (files in internal/modules/)
    if (file.filePath.includes('internal/modules/')) {
      const moduleNode = {
        id: `module-${fileName}`,
        name: fileName,
        type: 'module',
        filePath: file.filePath,
        description: `Kthulu module: ${fileName}`,
        position: { x: Math.random() * 400, y: Math.random() * 300 },
        metadata: {
          framework: 'kthulu',
          language: 'go',
          moduleType: 'domain',
        },
        templateId: this.template.id,
        projectId: this.projectId,
      };
      nodes.push(moduleNode);

      // Extract use cases
      const useCases = this.extractUseCases(content);
      useCases.forEach((useCase, index) => {
        const useCaseNode = {
          id: `usecase-${fileName}-${useCase}`,
          name: useCase,
          type: 'usecase',
          filePath: file.filePath,
          description: `Use case: ${useCase}`,
          position: { x: Math.random() * 400, y: 100 + index * 80 },
          metadata: {
            module: fileName,
            componentType: 'domain',
          },
          templateId: this.template.id,
          projectId: this.projectId,
        };
        nodes.push(useCaseNode);

        // Create edge from module to use case
        edges.push({
          id: `edge-${moduleNode.id}-${useCaseNode.id}`,
          sourceNodeId: moduleNode.id,
          targetNodeId: useCaseNode.id,
          type: 'defines',
          metadata: { relationship: 'definesUseCase' },
          projectId: this.projectId,
        });
      });

      // Extract adapters
      const adapters = this.extractAdapters(content);
      adapters.forEach((adapter, index) => {
        const adapterNode = {
          id: `adapter-${fileName}-${adapter}`,
          name: adapter,
          type: 'adapter',
          filePath: file.filePath,
          description: `Adapter: ${adapter}`,
          position: { x: 300 + Math.random() * 200, y: 100 + index * 80 },
          metadata: {
            module: fileName,
            componentType: 'infrastructure',
          },
          templateId: this.template.id,
          projectId: this.projectId,
        };
        nodes.push(adapterNode);

        edges.push({
          id: `edge-${moduleNode.id}-${adapterNode.id}`,
          sourceNodeId: moduleNode.id,
          targetNodeId: adapterNode.id,
          type: 'contains',
          metadata: { relationship: 'hasAdapter' },
          projectId: this.projectId,
        });
      });

      // Extract ports
      const ports = this.extractPorts(content);
      ports.forEach((port, index) => {
        const portNode = {
          id: `port-${fileName}-${port}`,
          name: port,
          type: 'port',
          filePath: file.filePath,
          description: `Port: ${port}`,
          position: { x: 150 + Math.random() * 200, y: 200 + index * 80 },
          metadata: {
            module: fileName,
            componentType: 'domain',
          },
          templateId: this.template.id,
          projectId: this.projectId,
        };
        nodes.push(portNode);

        edges.push({
          id: `edge-${moduleNode.id}-${portNode.id}`,
          sourceNodeId: moduleNode.id,
          targetNodeId: portNode.id,
          type: 'defines',
          metadata: { relationship: 'hasPort' },
          projectId: this.projectId,
        });
      });

      // Detect hexagonal architecture pattern
      if (useCases.length > 0 && adapters.length > 0 && ports.length > 0) {
        patterns.push({
          id: `hexagonal-${fileName}`,
          type: 'hexagonal-architecture',
          confidence: 0.9,
          description: `Hexagonal architecture detected in module ${fileName}`,
          files: [file.filePath],
        });
      }
    }

    return { nodes, edges, patterns, validations };
  }

  private extractUseCases(content: string): string[] {
    const useCaseRegex = /type\s+(\w+UseCase)\s+struct/g;
    const matches = [];
    let match;

    while ((match = useCaseRegex.exec(content)) !== null) {
      matches.push(match[1]);
    }

    return matches;
  }

  private extractAdapters(content: string): string[] {
    const adapterRegex = /type\s+(\w+Adapter)\s+struct/g;
    const matches = [];
    let match;

    while ((match = adapterRegex.exec(content)) !== null) {
      matches.push(match[1]);
    }

    return matches;
  }

  private extractPorts(content: string): string[] {
    const portRegex = /type\s+(\w+Port)\s+interface/g;
    const matches = [];
    let match;

    while ((match = portRegex.exec(content)) !== null) {
      matches.push(match[1]);
    }

    return matches;
  }

  private validateKthuluArchitecture(nodes: any[], edges: any[]): any[] {
    const validations: any[] = [];

    // Check for DIP violations
    const domainNodes = nodes.filter(
      n => n.metadata?.componentType === 'domain'
    );
    const infraNodes = nodes.filter(
      n => n.metadata?.componentType === 'infrastructure'
    );

    edges.forEach(edge => {
      const source = nodes.find(n => n.id === edge.sourceNodeId);
      const target = nodes.find(n => n.id === edge.targetNodeId);

      if (
        source?.metadata?.componentType === 'domain' &&
        target?.metadata?.componentType === 'infrastructure'
      ) {
        validations.push({
          type: 'error',
          message: `DIP violation: Domain component ${source.name} depends on infrastructure component ${target.name}`,
          filePath: source.filePath,
          severity: 5,
        });
      }
    });

    // Check module completeness
    const modules = nodes.filter(n => n.type === 'module');
    modules.forEach(module => {
      const moduleUseCases = nodes.filter(
        n => n.type === 'usecase' && n.metadata?.module === module.name
      );

      if (moduleUseCases.length === 0) {
        validations.push({
          type: 'warning',
          message: `Module ${module.name} has no use cases defined`,
          filePath: module.filePath,
          severity: 3,
        });
      }
    });

    return validations;
  }

  private generateKthuluSuggestions(nodes: any[], edges: any[]): string[] {
    const suggestions: string[] = [];

    const modules = nodes.filter(n => n.type === 'module');
    const ports = nodes.filter(n => n.type === 'port');
    const adapters = nodes.filter(n => n.type === 'adapter');

    // Suggest creating adapters for ports without implementations
    ports.forEach(port => {
      const hasAdapter = adapters.some(adapter =>
        edges.some(
          edge =>
            edge.sourceNodeId === adapter.id &&
            edge.targetNodeId === port.id &&
            edge.type === 'implements'
        )
      );

      if (!hasAdapter) {
        suggestions.push(
          `Consider creating an adapter to implement port ${port.name}`
        );
      }
    });

    // Suggest creating events for cross-module communication
    if (modules.length > 1) {
      suggestions.push(
        'Consider using domain events for cross-module communication to maintain loose coupling'
      );
    }

    return suggestions;
  }

  private createEmptyResult(): AnalysisResult {
    return { nodes: [], edges: [], patterns: [], validationResults: [] };
  }

  getAnalyzerType(): string {
    return 'KthuluAnalyzer';
  }
}

/** Ferrus analyzer wrapper for Rust projects using Tree-sitter when available. */
export class FerrusAnalyzerAdapter implements ICodeAnalyzer {
  private rustParser: any | null = null;

  constructor(
    private template: Template,
    private projectId: string
  ) {}

  async analyze(files: ParsedFile[]): Promise<AnalysisResult> {
    const rustFiles = files.filter(f => f.filePath.endsWith('.rs'));
    if (rustFiles.length === 0) {
      return this.createEmptyResult();
    }

    if (!this.rustParser) {
      try {
        const Parser = (await import('tree-sitter')).default;
        const Rust = (await import('tree-sitter-rust')).default;
        this.rustParser = new Parser();
        this.rustParser.setLanguage(Rust);
      } catch {
        this.rustParser = null;
      }
    }

    const nodes: any[] = [];
    const edges: any[] = [];
    const validations: any[] = [];
    const funcMap: Record<string, string> = {};

    rustFiles.forEach((file, fileIndex) => {
      const funcs = this.extractFunctions(file.content);
      funcs.forEach((name, fnIndex) => {
        const id = `fn-${name}-${fileIndex}-${fnIndex}`;
        funcMap[name] = id;
        nodes.push({
          id,
          name,
          type: 'function',
          filePath: file.filePath,
          description: `Rust function ${name}`,
          position: { x: fnIndex * 120, y: fileIndex * 80 },
          metadata: { framework: 'ferrus', language: 'rust' },
          templateId: this.template.id,
          projectId: this.projectId,
        });
      });

      if (file.content.includes('unwrap()')) {
        validations.push({
          type: 'warning',
          message: 'Avoid using unwrap() in production code',
          filePath: file.filePath,
          severity: 3,
        });
      }
    });

    rustFiles.forEach(file => {
      const funcs = this.extractFunctions(file.content);
      funcs.forEach(name => {
        const sourceId = funcMap[name];
        const body = this.extractFunctionBody(file.content, name);
        if (!sourceId || !body) return;

        Object.entries(funcMap).forEach(([target, targetId]) => {
          if (target === name) return;
          const callRegex = new RegExp(`\\b${target}\\s*\\(`);
          if (callRegex.test(body)) {
            edges.push({
              id: `call-${sourceId}-${targetId}`,
              sourceNodeId: sourceId,
              targetNodeId: targetId,
              type: 'calls',
              metadata: {},
              projectId: this.projectId,
            });
          }
        });
      });
    });

    return { nodes, edges, patterns: [], validationResults: validations };
  }

  getAnalyzerType(): string {
    return 'FerrusAnalyzer';
  }

  private extractFunctions(content: string): string[] {
    if (this.rustParser) {
      try {
        const tree = this.rustParser.parse(content);
        const result: string[] = [];
        const visit = (node: any): void => {
          if (node.type === 'function_item') {
            const nameNode = node.childForFieldName('name');
            if (nameNode) result.push(nameNode.text);
          }
          node.namedChildren?.forEach((c: any) => visit(c));
        };
        visit(tree.rootNode);
        if (result.length > 0) return result;
      } catch {
        // Fall back to regex
      }
    }

    const regex = /fn\s+([A-Za-z0-9_]+)\s*\(/g;
    const names: string[] = [];
    let match: RegExpExecArray | null;
    while ((match = regex.exec(content))) {
      names.push(match[1]);
    }
    return names;
  }

  private extractFunctionBody(content: string, fn: string): string | null {
    const start = content.indexOf(`fn ${fn}`);
    if (start === -1) return null;
    const bodyMatch = content
      .slice(start)
      .match(/fn\s+[A-Za-z0-9_]+[^]*?{([^]*?)}/);
    return bodyMatch ? bodyMatch[1] : null;
  }

  private createEmptyResult(): AnalysisResult {
    return { nodes: [], edges: [], patterns: [], validationResults: [] };
  }
}

/** Factory for creating analyzers by id. */
export class AnalyzerFactory {
  static createAnalyzer(
    type: string,
    template: Template,
    projectId: string
  ): ICodeAnalyzer {
    switch (type) {
      case 'basic':
        return new BasicASTAnalyzerAdapter(template, projectId);
      case 'enhanced':
        return new EnhancedASTAnalyzerAdapter(template, projectId);
      case 'semantic':
        return new SemanticAnalyzerAdapter(template, projectId);
      case 'kthulu':
        return new KthuluAnalyzerAdapter(template, projectId);
      case 'ferrus':
        return new FerrusAnalyzerAdapter(template, projectId);
      default:
        return new EnhancedASTAnalyzerAdapter(template, projectId);
    }
  }

  static getAvailableAnalyzers(): string[] {
    return ['basic', 'enhanced', 'semantic', 'kthulu', 'ferrus'];
  }
}
