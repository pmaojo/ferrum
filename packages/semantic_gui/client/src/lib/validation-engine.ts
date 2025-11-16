import type { GraphNode, GraphEdge, Template } from '@shared/schema';

export interface ValidationIssue {
  id: string;
  type: 'violation' | 'warning' | 'suggestion';
  rule: string;
  message: string;
  severity: 'high' | 'medium' | 'low';
  sourceNodeId?: string;
  targetNodeId?: string;
  metadata?: Record<string, any>;
}

export class ValidationEngine {
  static validateGraph(
    nodes: GraphNode[],
    edges: GraphEdge[],
    template: Template
  ): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    for (const rule of template.validationRules) {
      const ruleIssues = this.validateRule(nodes, edges, rule);
      issues.push(...ruleIssues);
    }

    // Additional built-in validations
    issues.push(...this.validateOrphanedNodes(nodes, edges));
    issues.push(...this.validateCircularDependencies(nodes, edges));
    issues.push(...this.validateNamingConventions(nodes));

    return issues;
  }

  private static validateRule(
    nodes: GraphNode[],
    edges: GraphEdge[],
    rule: any
  ): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    switch (rule.rule) {
      case 'usecase-no-direct-adapter':
        if (rule.type === 'prohibited') {
          const violations = edges.filter((edge) => {
            const sourceNode = nodes.find((n) => n.id === edge.sourceNodeId);
            const targetNode = nodes.find((n) => n.id === edge.targetNodeId);
            return (
              sourceNode?.type === 'usecase' && targetNode?.type === 'adapter'
            );
          });

          for (const edge of violations) {
            const sourceNode = nodes.find((n) => n.id === edge.sourceNodeId);
            const targetNode = nodes.find((n) => n.id === edge.targetNodeId);

            issues.push({
              id: `violation_${Date.now()}_${Math.random()}`,
              type: 'violation',
              rule: rule.rule,
              message: `Use Case "${sourceNode?.name}" should not directly depend on Adapter "${targetNode?.name}". Consider using a repository interface.`,
              severity: 'high',
              sourceNodeId: edge.sourceNodeId,
              targetNodeId: edge.targetNodeId,
            });
          }
        }
        break;

      case 'controller-calls-usecase':
        if (rule.type === 'required') {
          const controllers = nodes.filter((n) => n.type === 'controller');

          for (const controller of controllers) {
            const hasUseCaseDependency = edges.some((edge) => {
              const targetNode = nodes.find((n) => n.id === edge.targetNodeId);
              return (
                edge.sourceNodeId === controller.id &&
                targetNode?.type === 'usecase'
              );
            });

            if (!hasUseCaseDependency) {
              issues.push({
                id: `warning_${Date.now()}_${Math.random()}`,
                type: 'warning',
                rule: rule.rule,
                message: `Controller "${controller.name}" should depend on at least one Use Case. Controllers should be thin and delegate to domain logic.`,
                severity: 'medium',
                sourceNodeId: controller.id,
              });
            }
          }
        }
        break;

      case 'entity-no-dependencies':
        if (rule.type === 'prohibited') {
          const entities = nodes.filter((n) => n.type === 'entity');

          for (const entity of entities) {
            const dependencies = edges.filter(
              (edge) => edge.sourceNodeId === entity.id
            );

            if (dependencies.length > 0) {
              issues.push({
                id: `violation_${Date.now()}_${Math.random()}`,
                type: 'violation',
                rule: rule.rule,
                message: `Entity "${entity.name}" should not have external dependencies. Entities should be pure domain objects.`,
                severity: 'high',
                sourceNodeId: entity.id,
              });
            }
          }
        }
        break;
    }

    return issues;
  }

  private static validateOrphanedNodes(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): ValidationIssue[] {
    const issues: ValidationIssue[] = [];
    const connectedNodeIds = new Set([
      ...edges.map((e) => e.sourceNodeId),
      ...edges.map((e) => e.targetNodeId),
    ]);

    const orphanedNodes = nodes.filter(
      (node) => !connectedNodeIds.has(node.id)
    );

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

  private static validateCircularDependencies(
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): ValidationIssue[] {
    const issues: ValidationIssue[] = [];
    const visited = new Set<string>();
    const recursionStack = new Set<string>();

    const hasCycle = (nodeId: string, path: string[]): boolean => {
      if (recursionStack.has(nodeId)) {
        // Found a cycle
        const cycleStart = path.indexOf(nodeId);
        const cyclePath = path.slice(cycleStart);

        issues.push({
          id: `violation_${Date.now()}_${Math.random()}`,
          type: 'violation',
          rule: 'no-circular-dependencies',
          message: `Circular dependency detected: ${cyclePath.map((id) => nodes.find((n) => n.id === id)?.name).join(' → ')} → ${nodes.find((n) => n.id === nodeId)?.name}`,
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

      const dependencies = edges.filter((e) => e.sourceNodeId === nodeId);
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

  private static validateNamingConventions(
    nodes: GraphNode[]
  ): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    for (const node of nodes) {
      // Check naming conventions based on node type
      switch (node.type) {
        case 'usecase':
          if (
            !node.name.toLowerCase().includes('usecase') &&
            !node.name.toLowerCase().includes('service')
          ) {
            issues.push({
              id: `suggestion_${Date.now()}_${Math.random()}`,
              type: 'suggestion',
              rule: 'usecase-naming',
              message: `Use Case "${node.name}" should follow naming convention (e.g., "CreateUserUseCase" or "UserService").`,
              severity: 'low',
              sourceNodeId: node.id,
            });
          }
          break;

        case 'controller':
          if (!node.name.toLowerCase().includes('controller')) {
            issues.push({
              id: `suggestion_${Date.now()}_${Math.random()}`,
              type: 'suggestion',
              rule: 'controller-naming',
              message: `Controller "${node.name}" should follow naming convention (e.g., "UserController").`,
              severity: 'low',
              sourceNodeId: node.id,
            });
          }
          break;

        case 'adapter':
          if (
            !node.name.toLowerCase().includes('adapter') &&
            !node.name.toLowerCase().includes('repository')
          ) {
            issues.push({
              id: `suggestion_${Date.now()}_${Math.random()}`,
              type: 'suggestion',
              rule: 'adapter-naming',
              message: `Adapter "${node.name}" should follow naming convention (e.g., "DatabaseAdapter" or "UserRepository").`,
              severity: 'low',
              sourceNodeId: node.id,
            });
          }
          break;

        case 'entity':
          if (
            node.name.toLowerCase().includes('entity') ||
            node.name.toLowerCase().includes('model')
          ) {
            issues.push({
              id: `suggestion_${Date.now()}_${Math.random()}`,
              type: 'suggestion',
              rule: 'entity-naming',
              message: `Entity "${node.name}" should use domain names without technical suffixes (e.g., "User" instead of "UserEntity").`,
              severity: 'low',
              sourceNodeId: node.id,
            });
          }
          break;
      }
    }

    return issues;
  }

  static getSeverityColor(severity: 'high' | 'medium' | 'low'): string {
    switch (severity) {
      case 'high':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low':
        return 'text-blue-600 bg-blue-50 border-blue-200';
    }
  }

  static getTypeIcon(type: 'violation' | 'warning' | 'suggestion'): string {
    switch (type) {
      case 'violation':
        return 'fas fa-times-circle';
      case 'warning':
        return 'fas fa-exclamation-triangle';
      case 'suggestion':
        return 'fas fa-lightbulb';
    }
  }
}
