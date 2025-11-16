import fs from 'node:fs';
import path from 'node:path';

import type { Express } from 'express';

import type { GraphEdge, GraphNode, Project } from '@shared/schema';

import type { GraphStreamEvent } from '../graphStream';
import { GraphStreamEventType } from '../graphStream';
import type { IStorage } from '../../storage';
import { ValidationEngine } from '../../validation-engine';
import type { CliCommandService } from './CliCommandService';
import type { PermaGraphService } from './PermaGraphService';
import type { ProjectMetricsService } from './ProjectMetricsService';

interface GraphStreamAdapter {
  send_batch: (events: GraphStreamEvent[]) => void;
}

export class ProjectGraphService {
  constructor(
    private readonly storage: IStorage,
    private readonly cliService: CliCommandService,
    private readonly permaGraphService: PermaGraphService,
    private readonly metrics: ProjectMetricsService,
    private readonly graphStream?: GraphStreamAdapter
  ) {}

  async getGraphData(projectId: string): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
    const [nodes, edges] = await Promise.all([
      this.storage.getNodesByProject(projectId),
      this.storage.getEdgesByProject(projectId),
    ]);
    return { nodes, edges };
  }

  async refreshGraph(projectId: string, host?: string | null): Promise<{
    nodesCreated: number;
    edgesCreated: number;
  }> {
    let cliData: any = {};
    if (host) {
      try {
        cliData = await this.cliService.execute(host, projectId, 'planGraph');
      } catch (error) {
        console.error('CLI planGraph execution failed:', error);
      }
    }

    const project = await this.getProjectOrThrow(projectId);
    const projectPath = project.projectPath;

    let parsed: any = {};
    try {
      const file = await fs.promises.readFile(
        path.join(projectPath, 'graph', 'project-graph.json'),
        'utf8'
      );
      parsed = JSON.parse(file);
    } catch {
      try {
        parsed = JSON.parse(cliData?.stdout || '{}');
      } catch {
        parsed = {};
      }
    }

    const rawNodes = parsed.nodes || parsed.graph?.nodes || {};
    const rawEdges = parsed.edges || parsed.graph?.edges || {};
    const sourceMap = parsed.sourceMap || parsed.graph?.sourceMap || {};

    const nodes = Array.isArray(rawNodes) ? rawNodes : Object.values(rawNodes);
    const edges = Array.isArray(rawEdges) ? rawEdges : Object.values(rawEdges).flat();

    await this.clearGraph(projectId);

    for (const node of nodes as any[]) {
      const src = sourceMap[node.id];
      if (src) {
        node.sourceMap = src;
        if (!node.filePath && src.file) {
          node.filePath = src.file;
        }
      }
      await this.storage.createGraphNode({ ...node, projectId });
    }

    for (const edge of edges as any[]) {
      await this.storage.createGraphEdge({ ...edge, projectId });
    }

    this.emitGraphStreamEvents(projectId, nodes as any[], edges as any[]);

    this.metrics.incrementChangesApplied(projectId, nodes.length + edges.length);

    return { nodesCreated: nodes.length, edgesCreated: edges.length };
  }

  async handlePostApply(projectId: string, host?: string | null): Promise<void> {
    try {
      await this.refreshGraph(projectId, host);
    } catch (error) {
      console.error('Graph refresh after apply failed:', error);
    }

    try {
      await this.permaGraphService.sync(projectId, 'incremental');
    } catch (error) {
      console.error('PermaGraph incremental sync failed:', error);
    }
  }

  async analyzeGitHub(projectId: string, repoUrl: string): Promise<{
    message: string;
    nodesCreated: number;
    edgesCreated: number;
    filesAnalyzed: number;
    patterns: unknown;
    suggestions: unknown;
  }> {
    const { template } = await this.getProjectAndTemplate(projectId);
    const match = repoUrl.match(/github\.com\/([^/]+)\/([^/]+)/);
    if (!match) {
      const error = new Error('Invalid GitHub URL format');
      (error as any).status = 400;
      throw error;
    }

    const [, owner, repo] = match;
    const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents`;
    const filesData = await this.fetchGitHubFiles(apiUrl);
    const multerFiles = filesData.map(file => ({
      originalname: file.name,
      buffer: Buffer.from(file.content),
    }));

    const { orchestrateCodebaseAnalysis } = await import('../../orchestrator');
    const result = await orchestrateCodebaseAnalysis(
      multerFiles as any,
      template,
      projectId,
      ['enhanced', 'semantic']
    );

    await this.persistAnalysisResults(projectId, result);
    await this.permaGraphService.recordTraceability(projectId, 'analyze-github', result);

    return {
      message: 'GitHub repository analyzed successfully',
      nodesCreated: result.nodes.length,
      edgesCreated: result.edges.length,
      filesAnalyzed: filesData.length,
      patterns: result.patterns,
      suggestions: result.suggestions,
    };
  }

  async analyzeUpload(
    projectId: string,
    files: Express.Multer.File[] | undefined,
    analyzerBodyValue?: string | string[]
  ): Promise<any> {
    if (!files || files.length === 0) {
      const error = new Error('No files provided');
      (error as any).status = 400;
      throw error;
    }

    const { template } = await this.getProjectAndTemplate(projectId);

    const analyzersFromBody = Array.isArray(analyzerBodyValue)
      ? analyzerBodyValue
      : analyzerBodyValue
      ? [analyzerBodyValue]
      : undefined;

    let analyzerTypes = analyzersFromBody || ['enhanced', 'semantic'];

    const hasGoFiles = files.some(file => file.originalname.endsWith('.go'));
    const hasKthuluStructure = files.some(
      file =>
        file.originalname.includes('internal/modules/') ||
        file.originalname.includes('cmd/kthulu-cli/')
    );

    if (hasGoFiles && (hasKthuluStructure || template.id === 'kthulu-hexagonal')) {
      analyzerTypes = ['kthulu', ...analyzerTypes];
    }

    const { orchestrateCodebaseAnalysis } = await import('../../orchestrator');
    const result = await orchestrateCodebaseAnalysis(
      files,
      template,
      projectId,
      analyzerTypes
    );

    await this.persistAnalysisResults(projectId, result);
    await this.permaGraphService.recordTraceability(projectId, 'analyze', result);

    return {
      nodesCreated: result.nodes.length,
      edgesCreated: result.edges.length,
      validationResults: result.validationResults.length,
      orchestratedAnalysis: {
        patterns: result.patterns,
        businessRules: result.businessRules,
        suggestions: result.suggestions,
        insights: result.insights,
        analyzersUsed: analyzerTypes,
      },
    };
  }

  async confirmNodes(projectId: string, confirmedFiles: string[]): Promise<{
    message: string;
    confirmedNodes: number;
  }> {
    const nodes = await this.storage.getNodesByProject(projectId);
    let updated = 0;
    for (const node of nodes) {
      if (node.filePath && confirmedFiles.includes(node.filePath)) {
        await this.storage.updateGraphNode(node.id, {
          metadata: {
            ...node.metadata,
            confirmed: true,
            confirmedAt: new Date().toISOString(),
          },
        } as any);
        updated += 1;
      }
    }
    return {
      message: `Confirmed ${updated} nodes`,
      confirmedNodes: updated,
    };
  }

  async getValidationResults(projectId: string) {
    return this.storage.getValidationResultsByProject(projectId);
  }

  async validateProject(projectId: string) {
    const { template } = await this.getProjectAndTemplate(projectId);
    const [nodes, edges] = await Promise.all([
      this.storage.getNodesByProject(projectId),
      this.storage.getEdgesByProject(projectId),
    ]);
    await this.storage.clearValidationResults(projectId);
    const validationEngine = new ValidationEngine(template);
    const gameValidation = validationEngine.validateArchitecture(
      nodes,
      edges,
      projectId
    );
    for (const violation of gameValidation.violations) {
      await this.storage.createValidationResult(violation);
    }
    return {
      validationResults: gameValidation.violations,
      gameScore: {
        totalScore: gameValidation.totalScore,
        compliance: gameValidation.compliance,
        penalties: gameValidation.penalties,
        rewards: gameValidation.rewards,
      },
    };
  }

  async calculateScore(projectId: string) {
    const { template } = await this.getProjectAndTemplate(projectId);
    const [nodes, edges] = await Promise.all([
      this.storage.getNodesByProject(projectId),
      this.storage.getEdgesByProject(projectId),
    ]);
    const validationEngine = new ValidationEngine(template);
    const gameValidation = validationEngine.validateArchitecture(
      nodes,
      edges,
      projectId
    );
    return {
      score: gameValidation.totalScore,
      compliance: gameValidation.compliance,
      penalties: gameValidation.penalties,
      rewards: gameValidation.rewards,
      totalNodes: nodes.length,
      totalEdges: edges.length,
    };
  }

  async exportProject(projectId: string) {
    const [project, nodes, edges] = await Promise.all([
      this.storage.getProject(projectId),
      this.storage.getNodesByProject(projectId),
      this.storage.getEdgesByProject(projectId),
    ]);
    if (!project) {
      const error = new Error('Project not found');
      (error as any).status = 404;
      throw error;
    }
    return { project, nodes, edges };
  }

  async getAiInsights(projectId: string) {
    const { template } = await this.getProjectAndTemplate(projectId);
    const [nodes, edges] = await Promise.all([
      this.storage.getNodesByProject(projectId),
      this.storage.getEdgesByProject(projectId),
    ]);
    const aiEngine = await import('../../ai-engine');
    return aiEngine.AIEngine.generateArchitectureInsights(nodes, edges, template);
  }

  async analyzeAiRequest(
    projectId: string,
    request: string,
    existingNodes?: any[],
    existingEdges?: any[],
    templateId?: string
  ) {
    if (!request?.trim()) {
      const error = new Error('Request is required');
      (error as any).status = 400;
      throw error;
    }
    const project = await this.getProjectOrThrow(projectId);
    const template = await this.getTemplate(templateId || project.templateId);
    if (!template) {
      const error = new Error('Template not found');
      (error as any).status = 404;
      throw error;
    }
    const aiResult = await import('../../ai-engine').then(mod =>
      mod.AIEngine.generateNodesFromRequest(
        request,
        existingNodes || [],
        existingEdges || [],
        template
      )
    );
    await this.permaGraphService.recordTraceability(
      projectId,
      'ai-analyze-request',
      aiResult
    );
    return aiResult;
  }

  private async getProjectAndTemplate(projectId: string): Promise<{
    project: Project;
    template: any;
  }> {
    const project = await this.getProjectOrThrow(projectId);
    const template = await this.getTemplate(project.templateId);
    if (!template) {
      const error = new Error('Template not found');
      (error as any).status = 404;
      throw error;
    }
    return { project, template };
  }

  private async getTemplate(templateId: string) {
    return this.storage.getTemplate(templateId);
  }

  private async getProjectOrThrow(projectId: string): Promise<Project> {
    const project = await this.storage.getProject(projectId);
    if (!project) {
      const error = new Error('Project not found');
      (error as any).status = 404;
      throw error;
    }
    return project;
  }

  private async clearGraph(projectId: string): Promise<void> {
    const [nodes, edges] = await Promise.all([
      this.storage.getNodesByProject(projectId),
      this.storage.getEdgesByProject(projectId),
    ]);
    for (const node of nodes) {
      await this.storage.deleteGraphNode(node.id);
    }
    for (const edge of edges) {
      await this.storage.deleteGraphEdge(edge.id);
    }
  }

  private emitGraphStreamEvents(
    projectId: string,
    nodes: any[],
    edges: any[]
  ): void {
    if (!this.graphStream) {
      return;
    }
    const events: GraphStreamEvent[] = [];
    const timestamp = new Date().toISOString();
    for (const node of nodes) {
      events.push({
        event_type: GraphStreamEventType.NODE_ADDED,
        data: node,
        timestamp,
        kg_id: projectId,
        tenant_id: projectId,
      });
    }
    for (const edge of edges) {
      events.push({
        event_type: GraphStreamEventType.EDGE_ADDED,
        data: edge,
        timestamp,
        kg_id: projectId,
        tenant_id: projectId,
      });
    }
    this.graphStream.send_batch(events);
  }

  private async fetchGitHubFiles(
    apiUrl: string,
    currentPath = ''
  ): Promise<{ name: string; content: string }[]> {
    const files: { name: string; content: string }[] = [];
    try {
      const response = await fetch(apiUrl + (currentPath ? `/${currentPath}` : ''));
      if (!response.ok) {
        throw new Error(`GitHub API error: ${response.status}`);
      }
      const items = await response.json();
      for (const item of items) {
        if (
          item.type === 'file' &&
          (item.name.endsWith('.ts') || item.name.endsWith('.js'))
        ) {
          const fileResponse = await fetch(item.download_url);
          if (fileResponse.ok) {
            const content = await fileResponse.text();
            files.push({ name: item.path || item.name, content });
          }
        } else if (
          item.type === 'dir' &&
          !item.name.startsWith('.') &&
          item.name !== 'node_modules'
        ) {
          const subFiles = await this.fetchGitHubFiles(apiUrl, item.path);
          files.push(...subFiles);
        }
      }
    } catch (error) {
      console.error('Error fetching GitHub files:', error);
    }
    return files;
  }

  private async persistAnalysisResults(projectId: string, result: any): Promise<void> {
    for (const node of result.nodes) {
      await this.storage.createGraphNode(node);
    }
    for (const edge of result.edges) {
      await this.storage.createGraphEdge(edge);
    }
    for (const validation of result.validationResults as any[]) {
      await this.storage.createValidationResult({
        id: `vr_${Date.now()}_${Math.random()}`,
        projectId,
        ruleId: validation.ruleId || 'unknown',
        status: validation.status || 'warning',
        message: validation.message,
        sourceNodeId: validation.sourceNodeId,
        targetNodeId: validation.targetNodeId,
        metadata: {
          filePath: validation.filePath,
          severity: validation.severity,
          type: validation.type,
        },
      } as any);
    }
  }
}

export default ProjectGraphService;
