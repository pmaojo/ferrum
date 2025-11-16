import type {
  InsertGraphNode,
  Template,
  GraphNode,
  InsertProject,
  GraphEdge,
  InsertGraphEdge,
  InsertTemplate,
  ValidationResult,
  InsertValidationResult,
  Project,
} from '@shared/schema';

import type { IStorage } from '../server/storage';
import { generateNodeId } from '../server/utils/generateNodeId';

export class MockStorage implements IStorage {
  public nodes: GraphNode[] = [];
  public edges: GraphEdge[] = [];
  public validationResults: ValidationResult[] = [];
  public projects: Record<string, Project> = {};
  public templates: Record<string, Template> = {
    tmpl1: {
      id: 'tmpl1',
      name: 'Test Template',
      description: '',
      nodeTypes: [],
      validationRules: [],
      metadata: {},
    } as any,
  };

  async getTemplate(id: string): Promise<Template | undefined> {
    return this.templates[id];
  }

  async createGraphNode(node: InsertGraphNode): Promise<GraphNode> {
    const id = node.id ?? generateNodeId(node.type, node.filePath ?? '');
    const created: GraphNode = {
      id,
      name: node.name,
      type: node.type,
      filePath: node.filePath ?? null,
      description: node.description ?? null,
      position: node.position,
      metadata: node.metadata ?? {},
      templateId: node.templateId,
      projectId: node.projectId,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    const existing = this.nodes.findIndex(n => n.id === id);
    if (existing >= 0) {
      this.nodes[existing] = created;
    } else {
      this.nodes.push(created);
    }
    return created;
  }

  async getProject(id: string): Promise<Project | undefined> {
    return this.projects[id];
  }
  async createProject(data: InsertProject): Promise<Project> {
    const project: Project = {
      id: (data as any).id ?? `proj_${Object.keys(this.projects).length}`,
      name: data.name,
      description: data.description ?? null,
      templateId: data.templateId,
      codebaseUrl: null,
      projectPath: data.projectPath,
      metadata: data.metadata ?? {},
      createdAt: new Date(),
      updatedAt: new Date(),
    } as any;
    this.projects[project.id] = project;
    return project;
  }
  async updateProject(
    id: string,
    updates: Partial<InsertProject>
  ): Promise<Project> {
    const current = this.projects[id];
    if (!current) throw new Error('project not found');
    const updated = { ...current, ...updates } as Project;
    this.projects[id] = updated;
    return updated;
  }
  async deleteProject(id: string): Promise<void> {
    delete this.projects[id];
  }
  async listProjects(): Promise<Project[]> {
    return Object.values(this.projects);
  }
  async getGraphNode(id: string): Promise<GraphNode | undefined> {
    return this.nodes.find(n => n.id === id);
  }
  async updateGraphNode(
    _: string,
    __: Partial<InsertGraphNode>
  ): Promise<GraphNode> {
    throw new Error('not implemented');
  }
  async deleteGraphNode(id: string): Promise<void> {
    this.nodes = this.nodes.filter(n => n.id !== id);
  }
  async getNodesByProject(projectId: string): Promise<GraphNode[]> {
    return this.nodes.filter(n => n.projectId === projectId);
  }
  async getGraphEdge(_: string): Promise<GraphEdge | undefined> {
    throw new Error('not implemented');
  }
  async createGraphEdge(edge: InsertGraphEdge): Promise<GraphEdge> {
    const created: GraphEdge = {
      id: edge.id ?? `edge_${this.edges.length}`,
      sourceNodeId: edge.sourceNodeId,
      targetNodeId: edge.targetNodeId,
      type: edge.type,
      metadata: edge.metadata ?? {},
      projectId: edge.projectId,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    this.edges.push(created);
    return created;
  }
  async updateGraphEdge(
    _: string,
    __: Partial<InsertGraphEdge>
  ): Promise<GraphEdge> {
    throw new Error('not implemented');
  }
  async deleteGraphEdge(id: string): Promise<void> {
    this.edges = this.edges.filter(e => e.id !== id);
  }
  async getEdgesByProject(_: string): Promise<GraphEdge[]> {
    return this.edges.filter(e => e.projectId === _);
  }
  async createTemplate(_: InsertTemplate): Promise<Template> {
    throw new Error('not implemented');
  }
  async listTemplates(): Promise<Template[]> {
    throw new Error('not implemented');
  }
  async createValidationResult(
    result: InsertValidationResult
  ): Promise<ValidationResult> {
    const created: ValidationResult = {
      id: result.id ?? `vr_${this.validationResults.length}`,
      projectId: result.projectId,
      ruleId: result.ruleId,
      status: result.status,
      message: result.message,
      sourceNodeId: result.sourceNodeId ?? null,
      targetNodeId: result.targetNodeId ?? null,
      metadata: result.metadata ?? {},
      createdAt: new Date(),
    } as any;
    this.validationResults.push(created);
    return created;
  }
  async getValidationResultsByProject(
    projectId: string
  ): Promise<ValidationResult[]> {
    return this.validationResults.filter(v => v.projectId === projectId);
  }
  async clearValidationResults(projectId: string): Promise<void> {
    this.validationResults = this.validationResults.filter(
      v => v.projectId !== projectId
    );
  }
}
