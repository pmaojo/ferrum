import type { Template, GraphNode, GraphEdge } from '@shared/schema';
import type { ParsedFile } from './ast-parser';

export interface TemplateRule {
  id: string;
  type: 'required' | 'prohibited';
  description: string;
  pattern: {
    source: string;
    target: string;
    relationship: string;
  };
}

export class TemplateEngine {
  static matchNodeType(filePath: string, template: Template): string | null {
    for (const nodeType of template.nodeTypes) {
      const regex = new RegExp(nodeType.pattern);
      if (regex.test(filePath)) {
        return nodeType.type;
      }
    }
    return null;
  }

  static generateNodes(
    files: ParsedFile[],
    template: Template,
    projectId: string
  ): GraphNode[] {
    const nodes: GraphNode[] = [];

    for (const file of files) {
      const nodeType = this.matchNodeType(file.path, template);
      if (!nodeType) continue;

      const typeConfig = template.nodeTypes.find((nt) => nt.type === nodeType);
      if (!typeConfig) continue;

      // Extract primary export as node name
      const nodeName =
        file.classes[0] ||
        file.functions[0] ||
        file.interfaces[0] ||
        file.path
          .split('/')
          .pop()
          ?.replace(/\.(ts|tsx|js|jsx)$/, '') ||
        'Unknown';

      const node: GraphNode = {
        id: `node_${Date.now()}_${Math.random()}`,
        name: nodeName,
        type: nodeType,
        filePath: file.path,
        description: this.extractDescription(file.content),
        position: this.generateRandomPosition(),
        metadata: {
          linesOfCode: file.content.split('\n').length,
          complexity: this.calculateComplexity(file.content),
          exports: file.exports,
          imports: file.imports,
        },
        templateId: template.id,
        projectId,
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      nodes.push(node);
    }

    return nodes;
  }

  static generateEdges(
    files: ParsedFile[],
    nodes: GraphNode[],
    projectId: string
  ): GraphEdge[] {
    const edges: GraphEdge[] = [];

    for (const file of files) {
      const sourceNode = nodes.find((n) => n.filePath === file.path);
      if (!sourceNode) continue;

      for (const importPath of file.imports) {
        // Find target node by import path
        const targetNode = nodes.find(
          (n) =>
            n.filePath?.includes(importPath) ||
            n.name.toLowerCase().includes(importPath.toLowerCase())
        );

        if (targetNode && targetNode.id !== sourceNode.id) {
          const edge: GraphEdge = {
            id: `edge_${Date.now()}_${Math.random()}`,
            sourceNodeId: sourceNode.id,
            targetNodeId: targetNode.id,
            type: 'depends',
            metadata: {
              importPath,
            },
            projectId,
            createdAt: new Date(),
            updatedAt: new Date(),
          };

          edges.push(edge);
        }
      }
    }

    return edges;
  }

  static validateArchitecture(
    nodes: GraphNode[],
    edges: GraphEdge[],
    template: Template
  ): Array<{
    rule: string;
    status: 'valid' | 'warning' | 'violation';
    message: string;
    sourceNode?: string;
    targetNode?: string;
  }> {
    const results: Array<{
      rule: string;
      status: 'valid' | 'warning' | 'violation';
      message: string;
      sourceNode?: string;
      targetNode?: string;
    }> = [];

    for (const rule of template.validationRules) {
      if (
        rule.rule === 'usecase-no-direct-adapter' &&
        rule.type === 'prohibited'
      ) {
        // Check for direct dependencies from use cases to adapters
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

          results.push({
            rule: rule.rule,
            status: 'violation',
            message: `${sourceNode?.name} should not directly depend on ${targetNode?.name}`,
            sourceNode: sourceNode?.name,
            targetNode: targetNode?.name,
          });
        }
      }

      if (
        rule.rule === 'controller-calls-usecase' &&
        rule.type === 'required'
      ) {
        // Check that controllers have use case dependencies
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
            results.push({
              rule: rule.rule,
              status: 'warning',
              message: `${controller.name} should depend on at least one use case`,
              sourceNode: controller.name,
            });
          }
        }
      }

      if (
        rule.rule === 'entity-no-dependencies' &&
        rule.type === 'prohibited'
      ) {
        // Check that entities don't have external dependencies
        const entities = nodes.filter((n) => n.type === 'entity');

        for (const entity of entities) {
          const hasDependencies = edges.some(
            (edge) => edge.sourceNodeId === entity.id
          );

          if (hasDependencies) {
            results.push({
              rule: rule.rule,
              status: 'violation',
              message: `${entity.name} should not have external dependencies`,
              sourceNode: entity.name,
            });
          }
        }
      }
    }

    return results;
  }

  private static extractDescription(content: string): string {
    // Extract JSDoc comment
    const jsdocMatch = content.match(/\/\*\*\s*(.*?)\s*\*\//s);
    if (jsdocMatch) {
      return jsdocMatch[1]
        .replace(/\s*\*\s*/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
    }

    // Extract single line comment
    const commentMatch = content.match(/\/\/\s*(.*)/);
    if (commentMatch) {
      return commentMatch[1].trim();
    }

    return '';
  }

  private static calculateComplexity(content: string): string {
    const lines = content.split('\n').length;
    const cyclomaticComplexity = (
      content.match(/if|else|while|for|switch|case|\?/g) || []
    ).length;

    if (cyclomaticComplexity > 10 || lines > 100) return 'High';
    if (cyclomaticComplexity > 5 || lines > 50) return 'Medium';
    return 'Low';
  }

  private static generateRandomPosition(): { x: number; y: number } {
    return {
      x: Math.floor(Math.random() * 800) + 100,
      y: Math.floor(Math.random() * 600) + 100,
    };
  }
}
