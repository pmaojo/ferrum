interface Listener {
  (...args: unknown[]): void;
}

/**
 * Minimal event emitter implementation used to avoid relying on Node's
 * built-in `events` module which requires type definitions that are not
 * available in this environment.
 */
class SimpleEventEmitter {
  private listeners: Record<string, Listener[]> = {};

  on(event: string, listener: Listener): void {
    (this.listeners[event] ??= []).push(listener);
  }

  emit(event: string, ...args: unknown[]): void {
    for (const listener of this.listeners[event] ?? []) {
      listener(...args);
    }
  }
}

interface Template {
  validationRules?: Array<{
    rule: string;
    type: 'required' | 'prohibited';
    description: string;
  }>;
}

interface GraphNode {
  id: string;
  name: string;
  type: string;
  filePath?: string;
  metadata?: {
    decorators?: string[];
    isExported?: boolean;
    dependencies?: unknown[];
  } & Record<string, unknown>;
}

interface GraphEdge {
  id?: string;
  source?: string;
  target?: string;
  sourceNodeId?: string;
  targetNodeId?: string;
}

interface InsertValidationResult {
  projectId: string;
  ruleId: string;
  status: string;
  message: string;
  id?: string;
  sourceNodeId?: string;
  targetNodeId?: string;
  metadata?: Record<string, unknown>;
}

export interface ValidationPenalty {
  ruleId: string;
  description: string;
  severity: 'critical' | 'major' | 'minor';
  pointsLost: number;
  suggestion: string;
}

export interface ValidationReward {
  ruleId: string;
  description: string;
  pointsGained: number;
  achievement?: string;
}

export interface ValidationResult {
  penalties: ValidationPenalty[];
  rewards: ValidationReward[];
  totalScore: number;
  compliance: number; // 0-100%
  violations: InsertValidationResult[];
}

export class ValidationEngine extends SimpleEventEmitter {
  private template: Template;

  constructor(template: Template) {
    super();
    this.template = template;
  }

  private recordViolation(
    violations: InsertValidationResult[],
    violation: InsertValidationResult
  ) {
    violations.push(violation);
    this.emit('violation-found', violation);
  }

  validateArchitecture(
    nodes: GraphNode[],
    edges: GraphEdge[],
    projectId: string
  ): ValidationResult {
    const penalties: ValidationPenalty[] = [];
    const rewards: ValidationReward[] = [];
    const violations: InsertValidationResult[] = [];

    // NestJS Best Practices Validation
    this.validateNestJSConventions(
      nodes,
      penalties,
      rewards,
      violations,
      projectId
    );
    this.validateHexagonalArchitecture(
      nodes,
      edges,
      penalties,
      rewards,
      violations,
      projectId
    );
    this.validateLayerDependencies(
      nodes,
      edges,
      penalties,
      rewards,
      violations,
      projectId
    );
    this.validateNamingConventions(
      nodes,
      penalties,
      rewards,
      violations,
      projectId
    );
    this.validateFileStructure(
      nodes,
      penalties,
      rewards,
      violations,
      projectId
    );

    const totalPenalties = penalties.reduce((sum, p) => sum + p.pointsLost, 0);
    const totalRewards = rewards.reduce((sum, r) => sum + r.pointsGained, 0);
    const totalScore = Math.max(0, 1000 + totalRewards - totalPenalties);

    const totalRules = this.template.validationRules?.length || 1;
    const violatedRules = penalties.length;
    const compliance = Math.max(
      0,
      ((totalRules - violatedRules) / totalRules) * 100
    );

    const result = {
      penalties,
      rewards,
      totalScore,
      compliance,
      violations,
    };

    this.emit('validation-completed', result);
    return result;
  }

  private validateNestJSConventions(
    nodes: GraphNode[],
    penalties: ValidationPenalty[],
    rewards: ValidationReward[],
    violations: InsertValidationResult[],
    projectId: string
  ) {
    nodes.forEach(node => {
      // Controllers must end with .controller.ts
      if (node.type === 'controller') {
        if (!node.filePath?.endsWith('.controller.ts')) {
          penalties.push({
            ruleId: 'controller-naming',
            description: `Controller "${node.name}" must follow NestJS naming convention (.controller.ts)`,
            severity: 'major',
            pointsLost: 50,
            suggestion: 'Rename file to follow pattern: name.controller.ts',
          });

          this.recordViolation(violations, {
            projectId,
            message: `Controller naming violation: ${node.name}`,
            status: 'failed',
            ruleId: 'controller-naming',
            sourceNodeId: node.name,
            metadata: {
              expectedPattern: '*.controller.ts',
              actual: node.filePath,
            },
          });
        } else {
          rewards.push({
            ruleId: 'controller-naming',
            description: `Controller "${node.name}" follows NestJS conventions`,
            pointsGained: 10,
          });
        }

        // Controllers should have @Controller decorator
        if (!node.metadata?.decorators?.includes('Controller')) {
          penalties.push({
            ruleId: 'controller-decorator',
            description: `Controller "${node.name}" missing @Controller decorator`,
            severity: 'critical',
            pointsLost: 100,
            suggestion: 'Add @Controller() decorator to class',
          });

          this.recordViolation(violations, {
            projectId,
            message: `Missing @Controller decorator: ${node.name}`,
            status: 'failed',
            ruleId: 'controller-decorator',
            sourceNodeId: node.name,
            metadata: { required: '@Controller', type: 'decorator' },
          });
        }
      }

      // Services must end with .service.ts and have @Injectable
      if (node.type === 'service') {
        if (!node.filePath?.endsWith('.service.ts')) {
          penalties.push({
            ruleId: 'service-naming',
            description: `Service "${node.name}" must follow NestJS naming convention (.service.ts)`,
            severity: 'major',
            pointsLost: 50,
            suggestion: 'Rename file to follow pattern: name.service.ts',
          });
        }

        if (!node.metadata?.decorators?.includes('Injectable')) {
          penalties.push({
            ruleId: 'service-injectable',
            description: `Service "${node.name}" missing @Injectable decorator`,
            severity: 'critical',
            pointsLost: 100,
            suggestion:
              'Add @Injectable() decorator to enable dependency injection',
          });
        }
      }

      // Modules must export a class decorated with @Module
      if (node.type === 'module') {
        const hasDecorator = node.metadata?.decorators?.includes('Module');
        const isExported = node.metadata?.isExported;
        if (!hasDecorator || !isExported) {
          penalties.push({
            ruleId: 'module-exported-class',
            description: `Module "${node.name}" must export a class decorated with @Module`,
            severity: 'critical',
            pointsLost: 100,
            suggestion:
              'Ensure the module class is exported and decorated with @Module()',
          });

          this.recordViolation(violations, {
            projectId,
            message: `Module export/decorator violation: ${node.name}`,
            status: 'failed',
            ruleId: 'module-exported-class',
            sourceNodeId: node.name,
            metadata: { missingDecorator: !hasDecorator, isExported },
          });
        } else {
          rewards.push({
            ruleId: 'module-exported-class',
            description: `Module "${node.name}" exports a class decorated with @Module`,
            pointsGained: 10,
          });
        }
      }

      // Entities must follow domain patterns
      if (node.type === 'entity') {
        if (
          !node.filePath?.includes('/domain/') &&
          !node.filePath?.endsWith('.entity.ts')
        ) {
          penalties.push({
            ruleId: 'entity-location',
            description: `Entity "${node.name}" should be in domain folder with .entity.ts suffix`,
            severity: 'major',
            pointsLost: 75,
            suggestion: 'Move to src/domain/ and use .entity.ts suffix',
          });
        }

        // Entities should not have external dependencies
        const hasDependencies =
          node.metadata?.dependencies && node.metadata.dependencies.length > 0;
        if (hasDependencies) {
          penalties.push({
            ruleId: 'entity-no-dependencies',
            description: `Entity "${node.name}" should not have external dependencies`,
            severity: 'critical',
            pointsLost: 150,
            suggestion: 'Remove external dependencies from domain entities',
          });
        } else {
          rewards.push({
            ruleId: 'entity-pure',
            description: `Entity "${node.name}" is dependency-free`,
            pointsGained: 25,
            achievement: 'Pure Domain',
          });
        }
      }

      // DTOs must have validation
      if (node.type === 'dto') {
        if (!node.filePath?.endsWith('.dto.ts')) {
          penalties.push({
            ruleId: 'dto-naming',
            description: `DTO "${node.name}" must follow NestJS naming convention (.dto.ts)`,
            severity: 'major',
            pointsLost: 40,
            suggestion: 'Rename file to follow pattern: name.dto.ts',
          });
        }

        const hasValidation = node.metadata?.decorators?.some((d: string) =>
          [
            'IsString',
            'IsNumber',
            'IsEmail',
            'IsOptional',
            'IsNotEmpty',
          ].includes(d)
        );

        if (!hasValidation) {
          penalties.push({
            ruleId: 'dto-validation',
            description: `DTO "${node.name}" missing validation decorators`,
            severity: 'major',
            pointsLost: 60,
            suggestion:
              'Add class-validator decorators (@IsString, @IsNotEmpty, etc.)',
          });
        }
      }
    });
  }

  private validateHexagonalArchitecture(
    nodes: GraphNode[],
    edges: GraphEdge[],
    penalties: ValidationPenalty[],
    rewards: ValidationReward[],
    violations: InsertValidationResult[],
    projectId: string
  ) {
    // Check for proper layer separation
    const controllers = nodes.filter(n => n.type === 'controller');
    const useCases = nodes.filter(n => n.type === 'usecase');
    const repositories = nodes.filter(n => n.type === 'repository');
    const entities = nodes.filter(n => n.type === 'entity');

    // Controllers should call use cases, not services directly
    controllers.forEach(controller => {
      const controllerEdges = edges.filter(e => e.source === controller.name);
      const callsServices = controllerEdges.some(e => {
        const target = nodes.find(n => n.name === e.target);
        return target?.type === 'service';
      });

      const callsUseCases = controllerEdges.some(e => {
        const target = nodes.find(n => n.name === e.target);
        return target?.type === 'usecase';
      });

      if (callsServices && !callsUseCases) {
        penalties.push({
          ruleId: 'controller-calls-usecase',
          description: `Controller "${controller.name}" should delegate to use cases, not services directly`,
          severity: 'major',
          pointsLost: 80,
          suggestion: 'Create use case to orchestrate business logic',
        });

        this.recordViolation(violations, {
          projectId,
          message: `Controller bypassing use case layer: ${controller.name}`,
          status: 'failed',
          ruleId: 'controller-calls-usecase',
          sourceNodeId: controller.name,
          metadata: { violation: 'direct-service-call', layer: 'presentation' },
        });
      } else if (callsUseCases) {
        rewards.push({
          ruleId: 'proper-layering',
          description: `Controller "${controller.name}" properly delegates to use cases`,
          pointsGained: 20,
        });
      }
    });

    // Use cases should not directly depend on repositories
    useCases.forEach(useCase => {
      const useCaseEdges = edges.filter(e => e.sourceNodeId === useCase.id);
      const callsRepositories = useCaseEdges.some(e => {
        const target = nodes.find(n => n.id === e.targetNodeId);
        return target?.type === 'repository';
      });

      if (callsRepositories) {
        penalties.push({
          ruleId: 'usecase-no-direct-repo',
          description: `Use case "${useCase.name}" should not directly depend on repositories`,
          severity: 'critical',
          pointsLost: 120,
          suggestion: 'Use repository interfaces and dependency injection',
        });
      }
    });

    // Reward proper hexagonal structure
    if (
      controllers.length > 0 &&
      useCases.length > 0 &&
      repositories.length > 0 &&
      entities.length > 0
    ) {
      rewards.push({
        ruleId: 'hexagonal-complete',
        description: 'Complete hexagonal architecture layers implemented',
        pointsGained: 100,
        achievement: 'Hexagonal Master',
      });
    }
  }

  private validateLayerDependencies(
    nodes: GraphNode[],
    edges: GraphEdge[],
    penalties: ValidationPenalty[],
    rewards: ValidationReward[],
    violations: InsertValidationResult[],
    projectId: string
  ) {
    const layerHierarchy = {
      controller: 1, // Presentation
      dto: 1,
      usecase: 2, // Application
      service: 2,
      entity: 3, // Domain
      interface: 3,
      repository: 4, // Infrastructure
      adapter: 4,
    };

    edges.forEach(edge => {
      const sourceNode = nodes.find(n => n.id === edge.sourceNodeId);
      const targetNode = nodes.find(n => n.id === edge.targetNodeId);

      if (sourceNode && targetNode) {
        const sourceLayer =
          layerHierarchy[sourceNode.type as keyof typeof layerHierarchy] || 0;
        const targetLayer =
          layerHierarchy[targetNode.type as keyof typeof layerHierarchy] || 0;

        // Dependencies should flow inward (higher layer numbers)
        if (sourceLayer > targetLayer) {
          penalties.push({
            ruleId: 'wrong-dependency-direction',
            description: `"${sourceNode.name}" (${sourceNode.type}) depends on "${targetNode.name}" (${targetNode.type}) - wrong direction`,
            severity: 'critical',
            pointsLost: 200,
            suggestion: 'Dependencies should flow from outer to inner layers',
          });

          this.recordViolation(violations, {
            id: `vr_${Date.now()}_${Math.random()}`,
            projectId,
            message: `Wrong dependency direction: ${sourceNode.name} -> ${targetNode.name}`,
            status: 'failed',
            ruleId: 'layered-dependencies',
            sourceNodeId: sourceNode.id,
            targetNodeId: targetNode.id,
            metadata: {
              sourceLayer,
              targetLayer,
              violation: 'reverse-dependency',
            },
          });
        }
      }
    });
  }

  private validateNamingConventions(
    nodes: GraphNode[],
    penalties: ValidationPenalty[],
    rewards: ValidationReward[],
    violations: InsertValidationResult[],
    projectId: string
  ) {
    const conventions = {
      controller: /^[A-Z][a-zA-Z]*Controller$/,
      service: /^[A-Z][a-zA-Z]*Service$/,
      repository: /^[A-Z][a-zA-Z]*Repository$/,
      entity: /^[A-Z][a-zA-Z]*$/,
      dto: /^[A-Z][a-zA-Z]*Dto$/,
      usecase: /^[A-Z][a-zA-Z]*UseCase$/,
    };

    nodes.forEach(node => {
      const pattern = conventions[node.type as keyof typeof conventions];
      if (pattern && !pattern.test(node.name)) {
        penalties.push({
          ruleId: 'naming-convention',
          description: `"${node.name}" doesn't follow NestJS naming convention for ${node.type}`,
          severity: 'minor',
          pointsLost: 20,
          suggestion: `Rename to follow pattern: ${pattern.toString()}`,
        });

        this.recordViolation(violations, {
          id: `vr_${Date.now()}_${Math.random()}`,
          projectId,
          message: `Naming convention violation: ${node.name}`,
          status: 'failed',
          ruleId: 'naming-convention',
          sourceNodeId: node.id,
          metadata: {
            expectedPattern: pattern.toString(),
            actual: node.name,
            type: node.type,
          },
        });
      } else if (pattern) {
        rewards.push({
          ruleId: 'good-naming',
          description: `"${node.name}" follows NestJS naming conventions`,
          pointsGained: 5,
        });
      }
    });
  }

  private validateFileStructure(
    nodes: GraphNode[],
    penalties: ValidationPenalty[],
    rewards: ValidationReward[],
    violations: InsertValidationResult[],
    projectId: string
  ) {
    const expectedStructure = {
      controller: /src\/(.*\/)?controllers\/.*\.controller\.ts$/,
      service: /src\/(.*\/)?services\/.*\.service\.ts$/,
      repository: /src\/(.*\/)?repositories\/.*\.repository\.ts$/,
      entity: /src\/domain\/.*\.entity\.ts$/,
      dto: /src\/(.*\/)?dto\/.*\.dto\.ts$/,
      usecase: /src\/(.*\/)?use-cases\/.*\.ts$/,
    };

    nodes.forEach(node => {
      const pattern =
        expectedStructure[node.type as keyof typeof expectedStructure];
      if (pattern && node.filePath && !pattern.test(node.filePath)) {
        penalties.push({
          ruleId: 'file-structure',
          description: `"${node.name}" is not in the correct folder structure`,
          severity: 'major',
          pointsLost: 40,
          suggestion: `Move to correct folder following pattern: ${pattern.toString()}`,
        });

        this.recordViolation(violations, {
          id: `vr_${Date.now()}_${Math.random()}`,
          projectId,
          message: `File structure violation: ${node.filePath}`,
          status: 'failed',
          ruleId: 'file-structure',
          sourceNodeId: node.id,
          metadata: {
            expectedPattern: pattern.toString(),
            actual: node.filePath,
            type: node.type,
          },
        });
      } else if (pattern && node.filePath) {
        rewards.push({
          ruleId: 'proper-structure',
          description: `"${node.name}" is properly organized`,
          pointsGained: 10,
        });
      }
    });
  }
}

export interface ValidationIssue {
  id: string;
  type: 'violation' | 'warning' | 'suggestion';
  rule: string;
  message: string;
  severity: 'low' | 'medium' | 'high';
  sourceNodeId?: string;
  targetNodeId?: string;
  metadata?: any;
}

export class GraphValidator {
  static validateGraph(
    nodes: GraphNode[],
    edges: GraphEdge[],
    _template: Template
  ): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    // Basic validation rules
    issues.push(...this.validateCircularDependencies(nodes, edges));
    issues.push(...this.validateOrphanedNodes(nodes, edges));
    issues.push(...this.validateNamingConventions(nodes));

    return issues;
  }

  private static validateCircularDependencies(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): ValidationIssue[] {
    const issues: ValidationIssue[] = [];
    const visited = new Set<string>();
    const recursionStack = new Set<string>();

    const hasCycle = (nodeId: string, path: string[]): boolean => {
      if (recursionStack.has(nodeId)) {
        const cycleStart = path.indexOf(nodeId);
        const cyclePath = path.slice(cycleStart);

        issues.push({
          id: `violation_${Date.now()}_${Math.random()}`,
          type: 'violation',
          rule: 'no-circular-dependencies',
          message: `Circular dependency detected: ${cyclePath.map(id => nodes.find(n => n.id === id)?.name).join(' → ')} → ${nodes.find(n => n.id === nodeId)?.name}`,
          severity: 'high',
          metadata: { cyclePath },
        });

        return true;
      }

      if (visited.has(nodeId)) {
        return false;
      }

      visited.add(nodeId);
      recursionStack.add(nodeId);

      const dependencies = edges.filter(e => e.sourceNodeId === nodeId);
      for (const edge of dependencies) {
        if (hasCycle(edge.targetNodeId, [...path, nodeId])) {
          return true;
        }
      }

      recursionStack.delete(nodeId);
      return false;
    };

    for (const node of nodes) {
      if (!visited.has(node.id)) {
        hasCycle(node.id, []);
      }
    }

    return issues;
  }

  private static validateOrphanedNodes(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): ValidationIssue[] {
    const issues: ValidationIssue[] = [];
    const connectedNodeIds = new Set([
      ...edges.map(e => e.sourceNodeId),
      ...edges.map(e => e.targetNodeId),
    ]);

    const orphanedNodes = nodes.filter(node => !connectedNodeIds.has(node.id));

    for (const node of orphanedNodes) {
      issues.push({
        id: `suggestion_${Date.now()}_${Math.random()}`,
        type: 'suggestion',
        rule: 'no-orphaned-nodes',
        message: `Node "${node.name}" is not connected to any other nodes. Consider adding relationships to integrate it into the architecture.`,
        severity: 'low',
        sourceNodeId: node.id,
      });
    }

    return issues;
  }

  private static validateNamingConventions(
    nodes: GraphNode[]
  ): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    for (const node of nodes) {
      // Check if name follows conventions
      if (node.name && node.name.trim() !== node.name) {
        issues.push({
          id: `warning_${Date.now()}_${Math.random()}`,
          type: 'warning',
          rule: 'naming-conventions',
          message: `Node "${node.name}" has leading/trailing whitespace`,
          severity: 'low',
          sourceNodeId: node.id,
        });
      }

      // Check for very short names
      if (node.name && node.name.length < 3) {
        issues.push({
          id: `suggestion_${Date.now()}_${Math.random()}`,
          type: 'suggestion',
          rule: 'meaningful-names',
          message: `Node "${node.name}" has a very short name. Consider using a more descriptive name.`,
          severity: 'low',
          sourceNodeId: node.id,
        });
      }
    }

    return issues;
  }
}
