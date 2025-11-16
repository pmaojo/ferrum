import type {
  Template,
  InsertGraphNode,
  InsertGraphEdge,
} from '@shared/schema';

export interface SemanticAnalysisResult {
  nodes: InsertGraphNode[];
  edges: InsertGraphEdge[];
  patterns: ArchitecturalPattern[];
  violations: ArchitecturalViolation[];
  suggestions: ArchitecturalSuggestion[];
}

export interface ArchitecturalPattern {
  id: string;
  type: string;
  confidence: number;
  description: string;
  files: string[];
}

export interface ArchitecturalViolation {
  id: string;
  type: string;
  severity: 'high' | 'medium' | 'low';
  description: string;
  file: string;
  suggestion: string;
}

export interface ArchitecturalSuggestion {
  id: string;
  type: string;
  description: string;
  implementation: string;
  priority: number;
}

export interface ParsedCodeFile {
  path: string;
  content: string;
  imports: string[];
  exports: string[];
  classes: ClassDefinition[];
  functions: FunctionDefinition[];
  interfaces: InterfaceDefinition[];
  decorators: DecoratorInfo[];
  dependencies: string[];
  complexity: number;
  loc: number;
}

export interface ClassDefinition {
  name: string;
  decorators: string[];
  methods: string[];
  properties: string[];
  extends?: string;
  implements?: string[];
}

export interface FunctionDefinition {
  name: string;
  parameters: string[];
  returnType?: string;
  isAsync: boolean;
  decorators: string[];
}

export interface InterfaceDefinition {
  name: string;
  methods: string[];
  properties: string[];
  extends?: string[];
}

export interface DecoratorInfo {
  name: string;
  target: string;
  parameters?: string[];
}

export class SemanticAnalyzer {
  private template: Template;

  constructor(template: Template) {
    this.template = template;
  }

  /**
   * Performs comprehensive semantic analysis of codebase
   */
  async analyzeCodebase(
    files: ParsedCodeFile[],
    projectId: string
  ): Promise<SemanticAnalysisResult> {
    // 1. Analyze architectural patterns based on template
    const patterns = this.detectArchitecturalPatterns(files);

    // 2. Generate nodes using template-aware classification
    const nodes = this.generateSemanticNodes(files, projectId, patterns);

    // 3. Detect relationships and dependencies
    const edges = this.generateSemanticEdges(files, nodes, projectId);

    // 4. Validate against template rules
    const violations = this.validateArchitecture(files, nodes, edges);

    // 5. Generate intelligent suggestions
    const suggestions = this.generateArchitecturalSuggestions(
      files,
      patterns,
      violations
    );

    return {
      nodes,
      edges,
      patterns,
      violations,
      suggestions,
    };
  }

  /**
   * Detects architectural patterns using template knowledge
   */
  private detectArchitecturalPatterns(
    files: ParsedCodeFile[]
  ): ArchitecturalPattern[] {
    const patterns: ArchitecturalPattern[] = [];

    // Hexagonal Architecture Detection
    if (this.template.name.toLowerCase().includes('hexagonal')) {
      patterns.push(...this.detectHexagonalPatterns(files));
    }

    // DDD Pattern Detection
    patterns.push(...this.detectDDDPatterns(files));

    // Clean Architecture Detection
    patterns.push(...this.detectCleanArchitecturePatterns(files));

    // CQRS Pattern Detection
    patterns.push(...this.detectCQRSPatterns(files));

    return patterns;
  }

  /**
   * Generates nodes using template-aware semantic analysis
   */
  private generateSemanticNodes(
    files: ParsedCodeFile[],
    projectId: string,
    patterns: ArchitecturalPattern[]
  ): InsertGraphNode[] {
    const nodes: InsertGraphNode[] = [];

    files.forEach((file, index) => {
      // Use template node types for better classification
      const nodeType = this.classifyNodeByTemplate(file);
      const semanticInfo = this.extractSemanticInfo(file, patterns);

      const node: InsertGraphNode = {
        name: this.extractNodeName(file, nodeType),
        type: nodeType,
        projectId,
        templateId: this.template.id,
        position: this.calculateSemanticPosition(
          file,
          nodeType,
          index,
          patterns
        ),
        description: this.generateSemanticDescription(file, semanticInfo),
        filePath: file.path,
        metadata: {
          semanticInfo,
          complexity: file.complexity,
          loc: file.loc,
          dependencies: file.dependencies,
          patterns: patterns
            .filter(p => p.files.includes(file.path))
            .map(p => p.type),
          decorators: file.decorators,
          businessLogic: this.extractBusinessLogic(file),
          architecturalRole: this.determineArchitecturalRole(file, nodeType),
        },
      };

      nodes.push(node);
    });

    return nodes;
  }

  /**
   * Classifies node type using template knowledge
   */
  private classifyNodeByTemplate(file: ParsedCodeFile): string {
    const templateNodeTypes = this.template.nodeTypes || [];

    for (const nodeType of templateNodeTypes) {
      if (this.matchesNodePattern(file, nodeType.pattern)) {
        return nodeType.type;
      }
    }

    // Advanced semantic classification based on content
    return this.advancedNodeClassification(file);
  }

  /**
   * Advanced node classification using semantic analysis
   */
  private advancedNodeClassification(file: ParsedCodeFile): string {
    const content = file.content.toLowerCase();
    const path = file.path.toLowerCase();

    // Use Case Detection
    if (this.isUseCase(file)) return 'usecase';

    // Controller Detection (NestJS, Express, etc.)
    if (this.isController(file)) return 'controller';

    // Service/Domain Service Detection
    if (this.isService(file)) return 'service';

    // Repository/Adapter Detection
    if (this.isRepository(file)) return 'repository';

    // Entity/Domain Model Detection
    if (this.isEntity(file)) return 'entity';

    // DTO/Value Object Detection
    if (this.isDTO(file)) return 'dto';

    // Module/Configuration Detection
    if (this.isModule(file)) return 'module';

    // Guard/Middleware Detection
    if (this.isGuard(file)) return 'guard';

    return 'unknown';
  }

  /**
   * Determines if file represents a use case
   */
  private isUseCase(file: ParsedCodeFile): boolean {
    const indicators = [
      file.path.includes('use-case'),
      file.path.includes('usecase'),
      file.content.includes('UseCase'),
      file.content.includes('execute('),
      file.content.includes('handle('),
      this.hasBusinessLogicPatterns(file),
    ];

    return indicators.filter(Boolean).length >= 2;
  }

  /**
   * Determines if file represents a controller
   */
  private isController(file: ParsedCodeFile): boolean {
    return (
      file.decorators.some(d => d.name === 'Controller') ||
      file.path.includes('controller') ||
      file.classes.some(c => c.decorators.includes('Controller')) ||
      file.content.includes('@Controller') ||
      file.content.includes('router.')
    );
  }

  /**
   * Determines if file represents a service
   */
  private isService(file: ParsedCodeFile): boolean {
    return (
      file.decorators.some(d => d.name === 'Injectable') ||
      file.path.includes('service') ||
      file.classes.some(c => c.decorators.includes('Injectable')) ||
      file.content.includes('@Injectable') ||
      (file.path.includes('domain') && !this.isEntity(file))
    );
  }

  /**
   * Determines if file represents a repository
   */
  private isRepository(file: ParsedCodeFile): boolean {
    return (
      file.path.includes('repository') ||
      file.content.includes('Repository') ||
      file.content.includes('@InjectRepository') ||
      file.content.includes('findOne') ||
      file.content.includes('save(') ||
      file.content.includes('create(') ||
      file.content.includes('delete(')
    );
  }

  /**
   * Determines if file represents an entity
   */
  private isEntity(file: ParsedCodeFile): boolean {
    return (
      file.decorators.some(d => d.name === 'Entity') ||
      file.path.includes('entity') ||
      file.path.includes('entities') ||
      file.content.includes('@Entity') ||
      file.content.includes('@Column') ||
      file.content.includes('@PrimaryGeneratedColumn')
    );
  }

  /**
   * Checks if file has business logic patterns
   */
  private hasBusinessLogicPatterns(file: ParsedCodeFile): boolean {
    const businessPatterns = [
      'validate',
      'process',
      'calculate',
      'apply',
      'transform',
      'business',
      'rule',
      'policy',
      'workflow',
    ];

    return businessPatterns.some(pattern =>
      file.content.toLowerCase().includes(pattern)
    );
  }

  /**
   * Detects hexagonal architecture patterns
   */
  private detectHexagonalPatterns(
    files: ParsedCodeFile[]
  ): ArchitecturalPattern[] {
    const patterns: ArchitecturalPattern[] = [];

    // Port detection
    const ports = files.filter(
      f =>
        f.path.includes('port') ||
        (f.interfaces.length > 0 && f.content.includes('interface'))
    );

    if (ports.length > 0) {
      patterns.push({
        id: 'hexagonal-ports',
        type: 'Hexagonal Ports',
        confidence: 0.8,
        description: 'Detected port interfaces for hexagonal architecture',
        files: ports.map(p => p.path),
      });
    }

    // Adapter detection
    const adapters = files.filter(
      f =>
        f.path.includes('adapter') ||
        f.path.includes('infrastructure') ||
        this.isRepository(f)
    );

    if (adapters.length > 0) {
      patterns.push({
        id: 'hexagonal-adapters',
        type: 'Hexagonal Adapters',
        confidence: 0.7,
        description: 'Detected adapter implementations',
        files: adapters.map(a => a.path),
      });
    }

    return patterns;
  }

  /**
   * Detects Domain-Driven Design patterns
   */
  private detectDDDPatterns(files: ParsedCodeFile[]): ArchitecturalPattern[] {
    const patterns: ArchitecturalPattern[] = [];

    // Domain entities
    const entities = files.filter(f => this.isEntity(f));

    // Value objects
    const valueObjects = files.filter(
      f =>
        f.path.includes('value-object') ||
        f.classes.some(c => c.name.includes('ValueObject'))
    );

    // Aggregates
    const aggregates = files.filter(
      f => f.content.includes('Aggregate') || f.path.includes('aggregate')
    );

    // Domain services
    const domainServices = files.filter(
      f => f.path.includes('domain') && this.isService(f)
    );

    if (entities.length > 0) {
      patterns.push({
        id: 'ddd-entities',
        type: 'DDD Entities',
        confidence: 0.9,
        description: `Found ${entities.length} domain entities`,
        files: entities.map(e => e.path),
      });
    }

    return patterns;
  }

  /**
   * Generates semantic edges based on dependencies and architectural patterns
   */
  private generateSemanticEdges(
    files: ParsedCodeFile[],
    nodes: InsertGraphNode[],
    projectId: string
  ): InsertGraphEdge[] {
    const edges: InsertGraphEdge[] = [];

    // Create dependency edges
    files.forEach(file => {
      const sourceNode = nodes.find(n => n.filePath === file.path);
      if (!sourceNode) return;

      file.dependencies.forEach(dep => {
        const targetNode = nodes.find(
          n =>
            n.filePath?.includes(dep) ||
            n.name.toLowerCase().includes(dep.toLowerCase())
        );

        if (targetNode && sourceNode.name !== targetNode.name) {
          const relationshipType = this.determineRelationshipType(
            sourceNode,
            targetNode,
            file
          );

          edges.push({
            id: `edge_${Date.now()}_${Math.random()}`,
            sourceNodeId: sourceNode.id,
            targetNodeId: targetNode.id,
            type: relationshipType,
            projectId,
            updatedAt: new Date(),
            metadata: {
              strength: this.calculateRelationshipStrength(file, dep),
              semanticType: relationshipType,
              architecturalLayer: this.determineArchitecturalLayer(
                sourceNode,
                targetNode
              ),
            },
          });
        }
      });
    });

    return edges;
  }

  /**
   * Determines relationship type between nodes
   */
  private determineRelationshipType(
    source: InsertGraphNode,
    target: InsertGraphNode,
    file: ParsedCodeFile
  ): string {
    if (source.type === 'controller' && target.type === 'service')
      return 'uses';
    if (source.type === 'service' && target.type === 'repository')
      return 'depends_on';
    if (source.type === 'usecase' && target.type === 'service')
      return 'orchestrates';
    if (source.type === 'repository' && target.type === 'entity')
      return 'manages';
    if (target.type === 'dto') return 'transforms';

    return 'depends_on';
  }

  /**
   * Calculates semantic position based on architectural role
   */
  private calculateSemanticPosition(
    file: ParsedCodeFile,
    nodeType: string,
    index: number,
    patterns: ArchitecturalPattern[]
  ): { x: number; y: number } {
    // Layer-based positioning for better architectural visualization
    const layers = {
      usecase: { y: 100, baseX: 100 },
      controller: { y: 200, baseX: 100 },
      service: { y: 300, baseX: 100 },
      repository: { y: 400, baseX: 100 },
      entity: { y: 500, baseX: 100 },
      dto: { y: 150, baseX: 400 },
      module: { y: 50, baseX: 100 },
      guard: { y: 250, baseX: 400 },
    };

    const layer = layers[nodeType] || { y: 350, baseX: 200 };
    const spacing = 200;

    return {
      x: layer.baseX + (index % 4) * spacing,
      y: layer.y + Math.floor(index / 4) * 80,
    };
  }

  /**
   * Extracts business logic information from file
   */
  private extractBusinessLogic(file: ParsedCodeFile): string[] {
    const businessLogic: string[] = [];

    // Extract business rules from comments
    const ruleMatches = file.content.match(
      /\/\/.*(?:rule|business|logic|validation).*$/gim
    );
    if (ruleMatches) {
      businessLogic.push(...ruleMatches.map(r => r.replace('//', '').trim()));
    }

    // Extract validation patterns
    if (file.content.includes('validate') || file.content.includes('check')) {
      businessLogic.push('Contains validation logic');
    }

    return businessLogic;
  }

  /**
   * Additional helper methods would continue here...
   */
  private matchesNodePattern(file: ParsedCodeFile, pattern: string): boolean {
    return (
      file.path.includes(pattern.toLowerCase()) ||
      file.content.toLowerCase().includes(pattern.toLowerCase())
    );
  }

  private extractSemanticInfo(
    file: ParsedCodeFile,
    patterns: ArchitecturalPattern[]
  ): any {
    return {
      relevantPatterns: patterns.filter(p => p.files.includes(file.path)),
      codeMetrics: {
        complexity: file.complexity,
        loc: file.loc,
        dependencies: file.dependencies.length,
      },
    };
  }

  private generateSemanticDescription(
    file: ParsedCodeFile,
    semanticInfo: any
  ): string {
    return `${file.path} - Complexity: ${file.complexity}, Dependencies: ${file.dependencies.length}`;
  }

  private determineArchitecturalRole(
    file: ParsedCodeFile,
    nodeType: string
  ): string {
    const roles = {
      usecase: 'Business Logic Orchestrator',
      controller: 'Presentation Layer',
      service: 'Business Logic',
      repository: 'Data Access Layer',
      entity: 'Domain Model',
      dto: 'Data Transfer Object',
    };

    return roles[nodeType] || 'Unknown';
  }

  private validateArchitecture(
    files: ParsedCodeFile[],
    nodes: InsertGraphNode[],
    edges: InsertGraphEdge[]
  ): ArchitecturalViolation[] {
    // Implementation for architectural validation
    return [];
  }

  private generateArchitecturalSuggestions(
    files: ParsedCodeFile[],
    patterns: ArchitecturalPattern[],
    violations: ArchitecturalViolation[]
  ): ArchitecturalSuggestion[] {
    // Implementation for architectural suggestions
    return [];
  }

  private detectCleanArchitecturePatterns(
    files: ParsedCodeFile[]
  ): ArchitecturalPattern[] {
    // Implementation for Clean Architecture detection
    return [];
  }

  private detectCQRSPatterns(files: ParsedCodeFile[]): ArchitecturalPattern[] {
    // Implementation for CQRS pattern detection
    return [];
  }

  private isDTO(file: ParsedCodeFile): boolean {
    return (
      file.path.includes('dto') ||
      file.content.includes('Dto') ||
      file.content.includes('DTO')
    );
  }

  private isModule(file: ParsedCodeFile): boolean {
    return file.path.includes('module') || file.content.includes('@Module');
  }

  private isGuard(file: ParsedCodeFile): boolean {
    return (
      file.path.includes('guard') ||
      file.content.includes('@Guard') ||
      file.content.includes('CanActivate')
    );
  }

  private calculateRelationshipStrength(
    file: ParsedCodeFile,
    dependency: string
  ): number {
    const occurrences = (file.content.match(new RegExp(dependency, 'g')) || [])
      .length;
    return Math.min(occurrences / 10, 1);
  }

  private determineArchitecturalLayer(
    source: InsertGraphNode,
    target: InsertGraphNode
  ): string {
    if (source.type === 'controller' && target.type === 'service')
      return 'presentation-to-business';
    if (source.type === 'service' && target.type === 'repository')
      return 'business-to-data';
    return 'same-layer';
  }

  private extractNodeName(file: ParsedCodeFile, nodeType: string): string {
    // Extract class name or meaningful identifier
    if (file.classes.length > 0) {
      return file.classes[0].name;
    }

    const fileName =
      file.path
        .split('/')
        .pop()
        ?.replace(/\.(ts|js)$/, '') || 'Unknown';
    return fileName.split('.')[0];
  }
}
