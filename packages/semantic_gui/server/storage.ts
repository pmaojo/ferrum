import {
  projects,
  graphNodes,
  graphEdges,
  templates,
  validationResults,
  type Project,
  type GraphNode,
  type GraphEdge,
  type Template,
  type ValidationResult,
  type InsertProject,
  type InsertGraphNode,
  type InsertGraphEdge,
  type InsertTemplate,
  type InsertValidationResult,
} from '@shared/schema';
import { eq } from 'drizzle-orm';
import { nanoid } from 'nanoid';

import { db } from './db';
import TemplateService from './services/TemplateService';
import { nextjsAppRouterTemplate } from './templates/nextjs-app-router';
import { generateNodeId } from './utils/generateNodeId';

export interface IStorage {
  // Project operations
  getProject(id: string): Promise<Project | undefined>;
  createProject(project: InsertProject): Promise<Project>;
  updateProject(id: string, updates: Partial<InsertProject>): Promise<Project>;
  deleteProject(id: string): Promise<void>;
  listProjects(): Promise<Project[]>;

  // Graph Node operations
  getGraphNode(id: string): Promise<GraphNode | undefined>;
  createGraphNode(node: InsertGraphNode): Promise<GraphNode>;
  updateGraphNode(
    id: string,
    updates: Partial<InsertGraphNode>
  ): Promise<GraphNode>;
  deleteGraphNode(id: string): Promise<void>;
  getNodesByProject(projectId: string): Promise<GraphNode[]>;

  // Graph Edge operations
  getGraphEdge(id: string): Promise<GraphEdge | undefined>;
  createGraphEdge(edge: InsertGraphEdge): Promise<GraphEdge>;
  updateGraphEdge(
    id: string,
    updates: Partial<InsertGraphEdge>
  ): Promise<GraphEdge>;
  deleteGraphEdge(id: string): Promise<void>;
  getEdgesByProject(projectId: string): Promise<GraphEdge[]>;

  // Template operations
  getTemplate(id: string): Promise<Template | undefined>;
  createTemplate(template: InsertTemplate): Promise<Template>;
  listTemplates(): Promise<Template[]>;

  // Validation operations
  createValidationResult(
    result: InsertValidationResult
  ): Promise<ValidationResult>;
  getValidationResultsByProject(projectId: string): Promise<ValidationResult[]>;
  clearValidationResults(projectId: string): Promise<void>;
}

export class DatabaseStorage implements IStorage {
  constructor() {}

  /**
   * Initialize storage by seeding default templates.
   */
  async init() {
    await this.seedTemplates();
  }

  private async seedTemplates() {
    const nestjsTemplate = {
      id: 'nestjs-hexagonal',
      name: 'NestJS Hexagonal Architecture',
      description:
        'Hexagonal architecture pattern for NestJS applications with clean architecture and DDD principles',
      metadata: {
        layers: {
          presentation: ['controller', 'dto', 'guard'],
          application: ['usecase', 'service'],
          domain: ['entity', 'interface'],
          infrastructure: ['adapter', 'repository', 'module'],
        },
        bestPractices: [
          'Follow dependency inversion principle',
          'Implement hexagonal architecture patterns',
          'Maintain clear separation of concerns',
        ],
      },
      nodeTypes: [
        // Presentation Layer
        {
          type: 'controller',
          pattern: 'src/(.*)/(.*)\\.controller\\.ts$',
          color: '#3b82f6',
          icon: '🎮',
        },
        {
          type: 'dto',
          pattern: 'src/(.*)/(.*)\\.dto\\.ts$',
          color: '#8b5cf6',
          icon: '📋',
        },
        {
          type: 'guard',
          pattern: 'src/(.*)/(.*)\\.guard\\.ts$',
          color: '#607D8B',
          icon: '🛡️',
        },

        // Application Layer
        {
          type: 'usecase',
          pattern: 'src/(.*)/(.*)\\.usecase\\.ts$',
          color: '#10b981',
          icon: '⚡',
        },
        {
          type: 'service',
          pattern: 'src/(.*)/(.*)\\.service\\.ts$',
          color: '#059669',
          icon: '⚙️',
        },

        // Domain Layer
        {
          type: 'entity',
          pattern: 'src/(.*)/(.*)\\.entity\\.ts$',
          color: '#ef4444',
          icon: '📦',
        },
        {
          type: 'interface',
          pattern: 'src/(.*)/(.*)\\.interface\\.ts$',
          color: '#f97316',
          icon: '🔗',
        },

        // Infrastructure Layer
        {
          type: 'adapter',
          pattern: 'src/(.*)/(.*)\\.adapter\\.ts$',
          color: '#84cc16',
          icon: '🔌',
        },
        {
          type: 'repository',
          pattern: 'src/(.*)/(.*)\\.repository\\.ts$',
          color: '#f59e0b',
          icon: '💾',
        },
        {
          type: 'module',
          pattern: 'src/(.*)/(.*)\\.module\\.ts$',
          color: '#F44336',
          icon: '📁',
        },

        // CQRS/Event Sourcing (optional)
        {
          type: 'event',
          pattern: 'src/(.*)/events/(.*)\\.event\\.ts$',
          color: '#FFC107',
          icon: '⚡',
        },
        {
          type: 'handler',
          pattern: 'src/(.*)/handlers/(.*)\\.handler\\.ts$',
          color: '#03A9F4',
          icon: '🔄',
        },

        // Cross-cutting concerns
        {
          type: 'middleware',
          pattern: 'src/(.*)/(.*)\\.middleware\\.ts$',
          color: '#06b6d4',
          icon: '🔀',
        },
        {
          type: 'pipe',
          pattern: 'src/(.*)/(.*)\\.pipe\\.ts$',
          color: '#8B5A2B',
          icon: '🧩',
        },
        {
          type: 'interceptor',
          pattern: 'src/(.*)/(.*)\\.interceptor\\.ts$',
          color: '#9C27B0',
          icon: '🎯',
        },
      ],
      validationRules: [
        // Dependency flow rules (outer → inner)
        {
          rule: 'controller-usecase',
          type: 'required' as const,
          description:
            'Controllers should depend on use cases, not services directly',
        },
        {
          rule: 'usecase-entity',
          type: 'required' as const,
          description: 'Use cases should work with domain entities',
        },
        {
          rule: 'adapter-interface',
          type: 'required' as const,
          description: 'Adapters should implement domain interfaces',
        },

        // Prohibited dependencies (maintaining clean architecture)
        {
          rule: 'entity-external',
          type: 'prohibited' as const,
          description: 'Entities must not depend on external concerns',
        },
        {
          rule: 'usecase-adapter',
          type: 'prohibited' as const,
          description: 'Use cases must not directly depend on adapters',
        },
        {
          rule: 'domain-infrastructure',
          type: 'prohibited' as const,
          description: 'Domain layer must not depend on infrastructure',
        },

        // Best practices
        {
          rule: 'dto-validation',
          type: 'required' as const,
          description: 'DTOs should have proper validation decorators',
        },
        {
          rule: 'service-srp',
          type: 'required' as const,
          description: 'Services should follow Single Responsibility Principle',
        },
        {
          rule: 'no-circular-dependencies',
          type: 'prohibited' as const,
          description: 'Circular dependencies are not allowed',
        },

        // Module organization
        {
          rule: 'module-cohesion',
          type: 'required' as const,
          description: 'Modules should group related functionality',
        },
        {
          rule: 'no-direct-db',
          type: 'prohibited' as const,
          description: 'Controllers should not directly access repositories',
        },
      ],
    };

    const nextJsTemplate = {
      ...nextjsAppRouterTemplate,
    };

    try {
      await db.insert(templates).values(nestjsTemplate).onConflictDoNothing();
      await db.insert(templates).values(nextJsTemplate).onConflictDoNothing();
    } catch {
      console.log('Template already exists or database error');
    }
  }

  // Project operations
  async getProject(id: string): Promise<Project | undefined> {
    const [project] = await db
      .select()
      .from(projects)
      .where(eq(projects.id, id));
    return project || undefined;
  }

  async createProject(project: InsertProject): Promise<Project> {
    const newProject = {
      id: nanoid(),
      name: project.name,
      description: project.description || null,
      templateId: project.templateId,
      codebaseUrl: project.codebaseUrl || null,
      projectPath: project.projectPath,
      metadata: project.metadata || {},
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    console.log(
      'About to insert project:',
      JSON.stringify(newProject, null, 2)
    );

    const [created] = await db.insert(projects).values(newProject).returning();
    console.log('Project inserted successfully:', created.id);
    return created;
  }

  async updateProject(
    id: string,
    updates: Partial<InsertProject>
  ): Promise<Project> {
    const updated = {
      ...updates,
      updatedAt: new Date(),
    };

    await db.update(projects).set(updated).where(eq(projects.id, id));
    const [project] = await db
      .select()
      .from(projects)
      .where(eq(projects.id, id));
    return project;
  }

  async deleteProject(id: string): Promise<void> {
    // Clean up related data
    await db.delete(graphNodes).where(eq(graphNodes.projectId, id));
    await db.delete(graphEdges).where(eq(graphEdges.projectId, id));
    await db
      .delete(validationResults)
      .where(eq(validationResults.projectId, id));
    await db.delete(projects).where(eq(projects.id, id));
  }

  async listProjects(): Promise<Project[]> {
    return await db.select().from(projects);
  }

  // Graph Node operations
  async getGraphNode(id: string): Promise<GraphNode | undefined> {
    const [node] = await db
      .select()
      .from(graphNodes)
      .where(eq(graphNodes.id, id));
    return node || undefined;
  }

  async createGraphNode(node: InsertGraphNode): Promise<GraphNode> {
    const id = node.id ?? generateNodeId(node.type, node.filePath ?? '');
    const newNode = {
      id,
      name: node.name,
      type: node.type,
      filePath: node.filePath || null,
      description: node.description || null,
      position: node.position,
      metadata: node.metadata || {},
      sourceMap: node.sourceMap || {},
      templateId: node.templateId,
      projectId: node.projectId,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    const [created] = await db
      .insert(graphNodes)
      .values(newNode)
      .onConflictDoNothing()
      .returning();

    if (created) return created;
    const [existing] = await db
      .select()
      .from(graphNodes)
      .where(eq(graphNodes.id, id));
    return existing;
  }

  async updateGraphNode(
    id: string,
    updates: Partial<InsertGraphNode>
  ): Promise<GraphNode> {
    const updated = {
      ...updates,
      updatedAt: new Date(),
    };

    await db.update(graphNodes).set(updated).where(eq(graphNodes.id, id));
    const [node] = await db
      .select()
      .from(graphNodes)
      .where(eq(graphNodes.id, id));
    return node;
  }

  async deleteGraphNode(id: string): Promise<void> {
    // Clean up related edges
    await db.delete(graphEdges).where(eq(graphEdges.sourceNodeId, id));
    await db.delete(graphEdges).where(eq(graphEdges.targetNodeId, id));
    await db.delete(graphNodes).where(eq(graphNodes.id, id));
  }

  async getNodesByProject(projectId: string): Promise<GraphNode[]> {
    return await db
      .select()
      .from(graphNodes)
      .where(eq(graphNodes.projectId, projectId));
  }

  // Graph Edge operations
  async getGraphEdge(id: string): Promise<GraphEdge | undefined> {
    const [edge] = await db
      .select()
      .from(graphEdges)
      .where(eq(graphEdges.id, id));
    return edge || undefined;
  }

  async createGraphEdge(edge: InsertGraphEdge): Promise<GraphEdge> {
    const newEdge = {
      id: nanoid(),
      sourceNodeId: edge.sourceNodeId,
      targetNodeId: edge.targetNodeId,
      type: edge.type,
      metadata: edge.metadata || {},
      projectId: edge.projectId,
      createdAt: new Date(),
    };

    const [created] = await db.insert(graphEdges).values(newEdge).returning();
    return created;
  }

  async updateGraphEdge(
    id: string,
    data: Partial<GraphEdge>
  ): Promise<GraphEdge> {
    const [updatedEdge] = await db
      .update(graphEdges)
      .set({
        ...data,
        updatedAt: new Date(),
      })
      .where(eq(graphEdges.id, id))
      .returning();

    if (!updatedEdge) {
      throw new Error(`Edge with id ${id} not found`);
    }

    return updatedEdge;
  }

  async deleteGraphEdge(id: string): Promise<void> {
    await db.delete(graphEdges).where(eq(graphEdges.id, id));
  }

  async getEdgesByProject(projectId: string): Promise<GraphEdge[]> {
    return await db
      .select()
      .from(graphEdges)
      .where(eq(graphEdges.projectId, projectId));
  }

  // Template operations
  async getTemplate(id: string): Promise<Template | undefined> {
    const [template] = await db
      .select()
      .from(templates)
      .where(eq(templates.id, id));
    if (!template) {
      return undefined;
    }
    return await TemplateService.mergeTemplate(template);
  }

  async createTemplate(template: InsertTemplate): Promise<Template> {
    const [created] = await db.insert(templates).values(template).returning();
    return created;
  }

  async listTemplates(): Promise<Template[]> {
    const dbTemplates = await db.select().from(templates);
    if (dbTemplates.length === 0) {
      // Seed default template if none exist
      await this.seedTemplates();
      return await db.select().from(templates);
    }
    return dbTemplates;
  }

  // Validation operations
  async createValidationResult(
    result: InsertValidationResult
  ): Promise<ValidationResult> {
    const newResult = {
      id: nanoid(),
      projectId: result.projectId,
      ruleId: result.ruleId,
      status: result.status,
      sourceNodeId: result.sourceNodeId || null,
      targetNodeId: result.targetNodeId || null,
      message: result.message,
      metadata: result.metadata || {},
      createdAt: new Date(),
    };

    const [created] = await db
      .insert(validationResults)
      .values(newResult)
      .returning();
    return created;
  }

  async getValidationResultsByProject(
    projectId: string
  ): Promise<ValidationResult[]> {
    return await db
      .select()
      .from(validationResults)
      .where(eq(validationResults.projectId, projectId));
  }

  async clearValidationResults(projectId: string): Promise<void> {
    await db
      .delete(validationResults)
      .where(eq(validationResults.projectId, projectId));
  }
}

export const storage = new DatabaseStorage();
