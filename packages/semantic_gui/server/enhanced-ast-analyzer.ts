import type {
  InsertGraphNode,
  InsertGraphEdge,
  Template,
} from '@shared/schema';

export interface EnhancedAnalysisResult {
  nodes: InsertGraphNode[];
  edges: InsertGraphEdge[];
  patterns: ArchitecturalPattern[];
  businessRules: BusinessRule[];
  suggestions: string[];
}

export interface ArchitecturalPattern {
  type: string;
  confidence: number;
  description: string;
  files: string[];
}

export interface BusinessRule {
  id: string;
  description: string;
  location: string;
  type: 'validation' | 'business_logic' | 'constraint';
}

export interface CodeFile {
  path: string;
  content: string;
  imports: string[];
  exports: string[];
  classes: string[];
  functions: string[];
  decorators: string[];
}

export class EnhancedASTAnalyzer {
  private template: Template;

  constructor(template: Template) {
    this.template = template;
  }

  async analyzeCodebase(
    files: { name: string; content: string }[],
    projectId: string
  ): Promise<EnhancedAnalysisResult> {
    const parsedFiles = this.parseFiles(files);

    // 1. Detect architectural patterns using template knowledge
    const patterns = this.detectArchitecturalPatterns(parsedFiles);

    // 2. Generate semantic nodes with business logic
    const nodes = this.generateSemanticNodes(parsedFiles, projectId, patterns);

    // 3. Create intelligent edges
    const edges = this.generateSemanticEdges(parsedFiles, nodes, projectId);

    // 4. Extract business rules
    const businessRules = this.extractBusinessRules(parsedFiles);

    // 5. Generate architectural suggestions
    const suggestions = this.generateSuggestions(patterns, businessRules);

    return {
      nodes,
      edges,
      patterns,
      businessRules,
      suggestions,
    };
  }

  private parseFiles(files: { name: string; content: string }[]): CodeFile[] {
    return files.map(file => ({
      path: file.name,
      content: file.content,
      imports: this.extractImports(file.content),
      exports: this.extractExports(file.content),
      classes: this.extractClasses(file.content),
      functions: this.extractFunctions(file.content),
      decorators: this.extractDecorators(file.content),
    }));
  }

  private detectArchitecturalPatterns(
    files: CodeFile[]
  ): ArchitecturalPattern[] {
    const patterns: ArchitecturalPattern[] = [];

    // Hexagonal Architecture Detection
    const controllers = files.filter(f => this.isController(f));
    const services = files.filter(f => this.isService(f));
    const repositories = files.filter(f => this.isRepository(f));
    const useCases = files.filter(f => this.isUseCase(f));

    if (
      controllers.length > 0 &&
      services.length > 0 &&
      repositories.length > 0
    ) {
      patterns.push({
        type: 'Hexagonal Architecture',
        confidence: 0.9,
        description: `Detected layered architecture: ${controllers.length} controllers, ${services.length} services, ${repositories.length} repositories`,
        files: [...controllers, ...services, ...repositories].map(f => f.path),
      });
    }

    // Domain-Driven Design Detection
    if (useCases.length > 0) {
      patterns.push({
        type: 'Domain-Driven Design',
        confidence: 0.8,
        description: `Found ${useCases.length} use cases indicating DDD approach`,
        files: useCases.map(f => f.path),
      });
    }

    // Clean Architecture Detection
    const entities = files.filter(f => this.isEntity(f));
    if (entities.length > 0 && useCases.length > 0) {
      patterns.push({
        type: 'Clean Architecture',
        confidence: 0.85,
        description: `Clean Architecture with ${entities.length} entities and ${useCases.length} use cases`,
        files: [...entities, ...useCases].map(f => f.path),
      });
    }

    return patterns;
  }

  private generateSemanticNodes(
    files: CodeFile[],
    projectId: string,
    patterns: ArchitecturalPattern[]
  ): InsertGraphNode[] {
    const nodes: InsertGraphNode[] = [];

    files.forEach((file, index) => {
      const nodeType = this.classifyNodeType(file);
      const businessLogic = this.extractFileBusinessLogic(file);
      const position = this.calculateLayerPosition(nodeType, index);

      const node: InsertGraphNode = {
        name: this.extractNodeName(file),
        type: nodeType,
        projectId,
        templateId: this.template.id,
        position,
        description: this.generateNodeDescription(file, nodeType),
        filePath: file.path,
        metadata: {
          businessLogic,
          complexity: this.calculateComplexity(file),
          dependencies: file.imports.length,
          decorators: file.decorators,
          patterns: patterns
            .filter(p => p.files.includes(file.path))
            .map(p => p.type),
          codeMetrics: {
            linesOfCode: file.content.split('\n').length,
            functions: file.functions.length,
            classes: file.classes.length,
          },
          suggestedImplementation: this.generateImplementationSuggestion(
            file,
            nodeType
          ),
        },
      };

      nodes.push(node);
    });

    return nodes;
  }

  private classifyNodeType(file: CodeFile): string {
    // Use Case Detection - Business Logic Orchestration
    if (this.isUseCase(file)) return 'usecase';

    // Controller Detection - Presentation Layer
    if (this.isController(file)) return 'controller';

    // Service Detection - Business Logic
    if (this.isService(file)) return 'service';

    // Repository Detection - Data Access
    if (this.isRepository(file)) return 'repository';

    // Entity Detection - Domain Model
    if (this.isEntity(file)) return 'entity';

    // DTO Detection - Data Transfer
    if (this.isDTO(file)) return 'dto';

    // Module Detection - Configuration
    if (this.isModule(file)) return 'module';

    // Guard Detection - Security
    if (this.isGuard(file)) return 'guard';

    return 'component';
  }

  private isUseCase(file: CodeFile): boolean {
    return (
      file.path.toLowerCase().includes('use-case') ||
      file.path.toLowerCase().includes('usecase') ||
      file.content.includes('UseCase') ||
      file.content.includes('execute(') ||
      file.content.includes('handle(') ||
      this.containsBusinessLogicPatterns(file)
    );
  }

  private isController(file: CodeFile): boolean {
    return (
      file.decorators.includes('Controller') ||
      file.path.toLowerCase().includes('controller') ||
      file.content.includes('@Controller') ||
      file.content.includes('router.')
    );
  }

  private isService(file: CodeFile): boolean {
    return (
      file.decorators.includes('Injectable') ||
      file.path.toLowerCase().includes('service') ||
      file.content.includes('@Injectable') ||
      (file.path.toLowerCase().includes('domain') && !this.isEntity(file))
    );
  }

  private isRepository(file: CodeFile): boolean {
    return (
      file.path.toLowerCase().includes('repository') ||
      file.content.includes('Repository') ||
      file.content.includes('@InjectRepository') ||
      file.content.includes('findOne') ||
      file.content.includes('save(') ||
      file.content.includes('create(') ||
      file.content.includes('delete(')
    );
  }

  private isEntity(file: CodeFile): boolean {
    return (
      file.decorators.includes('Entity') ||
      file.path.toLowerCase().includes('entity') ||
      file.path.toLowerCase().includes('entities') ||
      file.content.includes('@Entity') ||
      file.content.includes('@Column') ||
      file.content.includes('@PrimaryGeneratedColumn')
    );
  }

  private isDTO(file: CodeFile): boolean {
    return (
      file.path.toLowerCase().includes('dto') ||
      file.content.includes('Dto') ||
      file.content.includes('DTO')
    );
  }

  private isModule(file: CodeFile): boolean {
    return (
      file.path.toLowerCase().includes('module') ||
      file.content.includes('@Module')
    );
  }

  private isGuard(file: CodeFile): boolean {
    return (
      file.path.toLowerCase().includes('guard') ||
      file.content.includes('@Guard') ||
      file.content.includes('CanActivate')
    );
  }

  private containsBusinessLogicPatterns(file: CodeFile): boolean {
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
      'orchestrate',
    ];

    return businessPatterns.some(pattern =>
      file.content.toLowerCase().includes(pattern)
    );
  }

  private calculateLayerPosition(
    nodeType: string,
    index: number
  ): { x: number; y: number } {
    const layers = {
      usecase: { y: 50, baseX: 200 }, // Top - Business Logic
      controller: { y: 150, baseX: 100 }, // Presentation Layer
      service: { y: 250, baseX: 200 }, // Business Logic Layer
      repository: { y: 350, baseX: 100 }, // Data Access Layer
      entity: { y: 450, baseX: 200 }, // Domain Model
      dto: { y: 100, baseX: 400 }, // Data Transfer
      module: { y: 0, baseX: 100 }, // Configuration
      guard: { y: 200, baseX: 400 }, // Security
    };

    const layer = layers[nodeType] || { y: 300, baseX: 300 };
    const spacing = 200;

    return {
      x: layer.baseX + (index % 4) * spacing,
      y: layer.y + Math.floor(index / 4) * 80,
    };
  }

  private extractFileBusinessLogic(file: CodeFile): string[] {
    const businessLogic: string[] = [];

    // Extract business rules from comments
    const ruleMatches = file.content.match(
      /\/\/.*(?:rule|business|logic|validation|constraint).*$/gim
    );
    if (ruleMatches) {
      businessLogic.push(...ruleMatches.map(r => r.replace('//', '').trim()));
    }

    // Extract validation patterns
    if (file.content.includes('validate') || file.content.includes('check')) {
      businessLogic.push('Contains validation logic');
    }

    // Extract workflow patterns
    if (file.content.includes('process') || file.content.includes('execute')) {
      businessLogic.push('Contains workflow processing');
    }

    return businessLogic;
  }

  private generateSemanticEdges(
    files: CodeFile[],
    nodes: InsertGraphNode[],
    projectId: string
  ): InsertGraphEdge[] {
    const edges: InsertGraphEdge[] = [];

    files.forEach(file => {
      const sourceNode = nodes.find(n => n.filePath === file.path);
      if (!sourceNode) return;

      file.imports.forEach(imp => {
        const targetNode = nodes.find(
          n =>
            n.filePath?.includes(imp) ||
            n.name.toLowerCase().includes(imp.toLowerCase())
        );

        if (targetNode && sourceNode.name !== targetNode.name) {
          const relationshipType = this.determineRelationshipType(
            sourceNode,
            targetNode
          );

          const parameters = this.extractParameters(
            file,
            imp,
            sourceNode,
            targetNode
          );
          const methodCalls = this.extractMethodCalls(file, imp);

          edges.push({
            source: sourceNode.name,
            target: targetNode.name,
            type: relationshipType,
            projectId,
            metadata: {
              semanticType: relationshipType,
              strength: this.calculateRelationshipStrength(file, imp),
              architecturalLayer: this.getArchitecturalLayer(
                sourceNode.type,
                targetNode.type
              ),
            },
            parameters,
            methodCalls,
          });
        }
      });
    });

    return edges;
  }

  private extractParameters(
    file: CodeFile,
    dependency: string,
    sourceNode: InsertGraphNode,
    targetNode: InsertGraphNode
  ): any[] {
    const parameters: any[] = [];

    // Extract constructor parameters
    const constructorMatch = file.content.match(
      new RegExp(`constructor\\s*\\([^)]*${dependency}[^)]*\\)`, 'i')
    );
    if (constructorMatch) {
      const constructorParams = this.parseConstructorParameters(
        constructorMatch[0]
      );
      parameters.push(...constructorParams);
    }

    // Extract method parameters
    const methodMatches = file.content.match(
      new RegExp(`${dependency}\\.[a-zA-Z_][a-zA-Z0-9_]*\\s*\\([^)]*\\)`, 'g')
    );
    if (methodMatches) {
      for (const match of methodMatches) {
        const methodParams = this.parseMethodParameters(match);
        parameters.push(...methodParams);
      }
    }

    // Extract DTO/Interface parameters based on node types
    if (sourceNode.type === 'controller' && targetNode.type === 'service') {
      const dtoParams = this.extractDTOParameters(file, dependency);
      parameters.push(...dtoParams);
    }

    return parameters;
  }

  private extractMethodCalls(file: CodeFile, dependency: string): any[] {
    const methodCalls: any[] = [];

    // Find all method calls to the dependency
    const methodCallRegex = new RegExp(
      `${dependency}\\.(\\w+)\\s*\\(([^)]*)\\)`,
      'g'
    );
    let match;

    while ((match = methodCallRegex.exec(file.content)) !== null) {
      const methodName = match[1];
      const parameters = match[2] ? match[2].split(',').map(p => p.trim()) : [];

      // Try to determine return type from context
      const returnType = this.inferReturnType(file.content, match[0]);

      methodCalls.push({
        methodName,
        parameters: parameters.filter(p => p.length > 0),
        returnType,
      });
    }

    return methodCalls;
  }

  private parseConstructorParameters(constructorString: string): any[] {
    const params: any[] = [];
    const paramMatch = constructorString.match(/\(([^)]*)\)/);

    if (paramMatch && paramMatch[1]) {
      const paramStrings = paramMatch[1].split(',');

      for (const paramString of paramStrings) {
        const trimmed = paramString.trim();
        const parts = trimmed.split(':');

        if (parts.length >= 2) {
          const name = parts[0]
            .trim()
            .replace(/private|public|protected|readonly/g, '')
            .trim();
          const type = parts[1].trim();

          params.push({
            name,
            type: 'dependency_injection',
            direction: 'input',
            dataType: type,
            required: true,
            description: `Injected dependency: ${name}`,
          });
        }
      }
    }

    return params;
  }

  private parseMethodParameters(methodString: string): any[] {
    const params: any[] = [];
    const methodMatch = methodString.match(/(\w+)\s*\(([^)]*)\)/);

    if (methodMatch) {
      const methodName = methodMatch[1];
      const paramString = methodMatch[2];

      if (paramString.trim()) {
        const paramParts = paramString.split(',');

        for (const part of paramParts) {
          const trimmed = part.trim();

          params.push({
            name: trimmed,
            type: 'method_parameter',
            direction: 'input',
            dataType: this.inferParameterType(trimmed),
            required: true,
            description: `Parameter for ${methodName}()`,
          });
        }
      }
    }

    return params;
  }

  private extractDTOParameters(file: CodeFile, dependency: string): any[] {
    const params: any[] = [];

    // Look for DTO interfaces or classes
    const dtoRegex = new RegExp(
      `(interface|class)\\s+(\\w*DTO?\\w*)\\s*{([^}]*)}`,
      'g'
    );
    let match;

    while ((match = dtoRegex.exec(file.content)) !== null) {
      const dtoName = match[2];
      const dtoBody = match[3];

      // Parse DTO properties
      const propertyRegex = /(\w+)\s*:\s*([^;,\n]+)/g;
      let propMatch;

      while ((propMatch = propertyRegex.exec(dtoBody)) !== null) {
        const propName = propMatch[1];
        const propType = propMatch[2].trim();

        params.push({
          name: propName,
          type: 'dto_property',
          direction: 'bidirectional',
          dataType: propType,
          required: !propType.includes('?'),
          description: `DTO property from ${dtoName}`,
        });
      }
    }

    return params;
  }

  private inferReturnType(content: string, methodCall: string): string {
    // Look for type annotations or return statements near the method call
    const lines = content.split('\n');
    const callLine = lines.find(line => line.includes(methodCall));

    if (callLine) {
      // Check for explicit type annotation
      const typeMatch = callLine.match(/:\s*([^=;,\n]+)/);
      if (typeMatch) {
        return typeMatch[1].trim();
      }

      // Check for Promise return
      if (callLine.includes('await') || methodCall.includes('async')) {
        return 'Promise<unknown>';
      }
    }

    return 'unknown';
  }

  private inferParameterType(paramString: string): string {
    // Simple type inference based on common patterns
    if (paramString.includes("'") || paramString.includes('"')) return 'string';
    if (paramString.match(/^\d+$/)) return 'number';
    if (paramString === 'true' || paramString === 'false') return 'boolean';
    if (paramString.includes('[') || paramString.includes('Array'))
      return 'array';
    if (paramString.includes('{') || paramString.includes('Object'))
      return 'object';

    return 'unknown';
  }

  private determineRelationshipType(
    source: InsertGraphNode,
    target: InsertGraphNode
  ): string {
    const relationships = {
      'usecase-service': 'orchestrates',
      'controller-service': 'uses',
      'service-repository': 'depends_on',
      'repository-entity': 'manages',
      'controller-dto': 'transforms',
      'service-entity': 'processes',
    };

    const key = `${source.type}-${target.type}`;
    return relationships[key] || 'depends_on';
  }

  private extractBusinessRules(files: CodeFile[]): BusinessRule[] {
    const rules: BusinessRule[] = [];

    files.forEach(file => {
      // Extract validation rules
      const validationMatches = file.content.match(/\/\/.*validation.*$/gim);
      if (validationMatches) {
        validationMatches.forEach((match, index) => {
          rules.push({
            id: `${file.path}-validation-${index}`,
            description: match.replace('//', '').trim(),
            location: file.path,
            type: 'validation',
          });
        });
      }

      // Extract business logic rules
      const businessMatches = file.content.match(
        /\/\/.*(?:business|rule).*$/gim
      );
      if (businessMatches) {
        businessMatches.forEach((match, index) => {
          rules.push({
            id: `${file.path}-business-${index}`,
            description: match.replace('//', '').trim(),
            location: file.path,
            type: 'business_logic',
          });
        });
      }
    });

    return rules;
  }

  private generateSuggestions(
    patterns: ArchitecturalPattern[],
    businessRules: BusinessRule[]
  ): string[] {
    const suggestions: string[] = [];

    if (patterns.length === 0) {
      suggestions.push(
        'Consider implementing a clear architectural pattern like Hexagonal Architecture'
      );
    }

    if (businessRules.length === 0) {
      suggestions.push(
        'Add business rule documentation in comments for better understanding'
      );
    }

    const hasUseCases = patterns.some(p => p.type.includes('Domain-Driven'));
    if (!hasUseCases) {
      suggestions.push(
        'Consider creating Use Case classes to organize business logic'
      );
    }

    return suggestions;
  }

  // Helper methods
  private extractImports(content: string): string[] {
    const importMatches = content.match(/import.*from\s+['"](.+)['"]/g);
    return importMatches
      ? importMatches.map(m => m.split("'")[1] || m.split('"')[1])
      : [];
  }

  private extractExports(content: string): string[] {
    const exportMatches = content.match(
      /export\s+(?:class|function|interface)\s+(\w+)/g
    );
    return exportMatches
      ? exportMatches.map(m => m.split(/\s+/).pop() || '')
      : [];
  }

  private extractClasses(content: string): string[] {
    const classMatches = content.match(/class\s+(\w+)/g);
    return classMatches ? classMatches.map(m => m.split(/\s+/)[1]) : [];
  }

  private extractFunctions(content: string): string[] {
    const functionMatches = content.match(
      /(?:function\s+(\w+)|(\w+)\s*\(.*\)\s*{)/g
    );
    return functionMatches
      ? functionMatches
          .map(m => {
            const match = m.match(/(?:function\s+(\w+)|(\w+)\s*\()/);
            return match ? match[1] || match[2] : '';
          })
          .filter(Boolean)
      : [];
  }

  private extractDecorators(content: string): string[] {
    const decoratorMatches = content.match(/@(\w+)/g);
    return decoratorMatches ? decoratorMatches.map(m => m.substring(1)) : [];
  }

  private extractNodeName(file: CodeFile): string {
    if (file.classes.length > 0) {
      return file.classes[0];
    }

    const fileName =
      file.path
        .split('/')
        .pop()
        ?.replace(/\.(ts|js)$/, '') || 'Unknown';
    return fileName.split('.')[0];
  }

  private calculateComplexity(file: CodeFile): number {
    const cyclomaticFactors = [
      'if',
      'else',
      'while',
      'for',
      'switch',
      'case',
      'catch',
      'try',
    ];

    let complexity = 1;
    cyclomaticFactors.forEach(factor => {
      const matches = file.content.match(new RegExp(`\\b${factor}\\b`, 'g'));
      if (matches) complexity += matches.length;
    });

    return complexity;
  }

  private generateNodeDescription(file: CodeFile, nodeType: string): string {
    const roleDescriptions = {
      usecase: 'Orchestrates business logic and workflows',
      controller: 'Handles HTTP requests and responses',
      service: 'Contains business logic and rules',
      repository: 'Manages data persistence and retrieval',
      entity: 'Represents domain model and business entities',
      dto: 'Transfers data between layers',
      module: 'Configures application modules and dependencies',
      guard: 'Handles authentication and authorization',
    };

    const baseDescription =
      roleDescriptions[nodeType] || 'Application component';
    const complexity = this.calculateComplexity(file);

    return `${baseDescription} - Complexity: ${complexity}, Functions: ${file.functions.length}`;
  }

  private generateImplementationSuggestion(
    file: CodeFile,
    nodeType: string
  ): string {
    const suggestions = {
      usecase:
        'Consider implementing execute() method with clear input/output interfaces',
      controller: 'Use proper HTTP status codes and validation decorators',
      service: 'Implement dependency injection and error handling',
      repository: 'Use repository pattern with proper abstractions',
      entity: 'Define proper relationships and validation rules',
      dto: 'Add validation decorators and transformation logic',
    };

    return (
      suggestions[nodeType] ||
      'Follow SOLID principles and clean code practices'
    );
  }

  private calculateRelationshipStrength(
    file: CodeFile,
    dependency: string
  ): number {
    const occurrences = (file.content.match(new RegExp(dependency, 'g')) || [])
      .length;
    return Math.min(occurrences / 10, 1);
  }

  private getArchitecturalLayer(
    sourceType: string,
    targetType: string
  ): string {
    const layers = {
      controller: 'presentation',
      service: 'business',
      repository: 'data',
      entity: 'domain',
      usecase: 'application',
    };

    const sourceLayer = layers[sourceType] || 'unknown';
    const targetLayer = layers[targetType] || 'unknown';

    return `${sourceLayer}-to-${targetLayer}`;
  }
}
