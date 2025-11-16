import type { Express, Request, Response } from 'express';

import type { ProjectGraphService } from '../../services/projects/ProjectGraphService';

export class ProjectGraphController {
  constructor(private readonly graphService: ProjectGraphService) {}

  getGraph = async (req: Request, res: Response): Promise<void> => {
    try {
      const data = await this.graphService.getGraphData(req.params.projectId);
      res.json(data);
    } catch (error) {
      this.handleError(res, error, 'Failed to fetch graph data');
    }
  };

  refreshGraph = async (req: Request, res: Response): Promise<void> => {
    try {
      const result = await this.graphService.refreshGraph(req.params.id, req.get('host'));
      res.json(result);
    } catch (error) {
      this.handleError(res, error, 'Failed to refresh graph');
    }
  };

  analyzeGitHub = async (req: Request, res: Response): Promise<void> => {
    try {
      const { repoUrl } = req.body;
      if (!repoUrl) {
        res.status(400).json({ error: 'Repository URL is required' });
        return;
      }
      const result = await this.graphService.analyzeGitHub(req.params.projectId, repoUrl);
      res.json(result);
    } catch (error) {
      this.handleError(res, error, 'GitHub repository analysis failed');
    }
  };

  analyzeUpload = async (req: Request, res: Response): Promise<void> => {
    try {
      const result = await this.graphService.analyzeUpload(
        req.params.projectId,
        req.files as Express.Multer.File[] | undefined,
        (req.body as any)?.analyzers
      );
      res.json(result);
    } catch (error) {
      this.handleError(res, error, 'Failed to analyze codebase');
    }
  };

  confirmNodes = async (req: Request, res: Response): Promise<void> => {
    try {
      const { confirmedFiles } = req.body as { confirmedFiles: string[] };
      if (!Array.isArray(confirmedFiles)) {
        res.status(400).json({ error: 'confirmedFiles must be an array' });
        return;
      }
      const result = await this.graphService.confirmNodes(
        req.params.projectId,
        confirmedFiles
      );
      res.json(result);
    } catch (error) {
      this.handleError(res, error, 'Failed to confirm nodes');
    }
  };

  getValidationResults = async (req: Request, res: Response): Promise<void> => {
    try {
      const results = await this.graphService.getValidationResults(req.params.projectId);
      res.json(results);
    } catch (error) {
      this.handleError(res, error, 'Failed to fetch validation results');
    }
  };

  validateProject = async (req: Request, res: Response): Promise<void> => {
    try {
      const result = await this.graphService.validateProject(req.params.projectId);
      res.json(result);
    } catch (error) {
      this.handleError(res, error, 'Failed to validate project');
    }
  };

  getScore = async (req: Request, res: Response): Promise<void> => {
    try {
      const result = await this.graphService.calculateScore(req.params.projectId);
      res.json(result);
    } catch (error) {
      this.handleError(res, error, 'Failed to calculate score');
    }
  };

  exportProject = async (req: Request, res: Response): Promise<void> => {
    try {
      const exportData = await this.graphService.exportProject(req.params.projectId);
      res.setHeader('Content-Type', 'application/json');
      res.setHeader(
        'Content-Disposition',
        `attachment; filename="${exportData.project.name}-graph.json"`
      );
      res.json(exportData);
    } catch (error) {
      this.handleError(res, error, 'Failed to export project');
    }
  };

  getAiInsights = async (req: Request, res: Response): Promise<void> => {
    try {
      const insights = await this.graphService.getAiInsights(req.params.projectId);
      res.json(insights);
    } catch (error) {
      console.error('Failed to generate AI insights:', error);
      this.handleError(res, error, 'Failed to generate AI insights');
    }
  };

  analyzeAiRequest = async (req: Request, res: Response): Promise<void> => {
    try {
      const { request: aiRequest, existingNodes, existingEdges, templateId } = req.body;
      const result = await this.graphService.analyzeAiRequest(
        req.params.projectId,
        aiRequest,
        existingNodes,
        existingEdges,
        templateId
      );
      res.json(result);
    } catch (error) {
      this.handleError(res, error, 'Failed to analyze request');
    }
  };

  private handleError(res: Response, error: any, fallback: string): void {
    if (error?.status) {
      res.status(error.status).json({ error: error.message || fallback });
      return;
    }
    console.error(fallback, error);
    res.status(500).json({ error: fallback });
  }
}

export default ProjectGraphController;
