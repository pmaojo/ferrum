import type { Request, Response } from 'express';

import { insertProjectSchema } from '@shared/schema';

import type { IStorage } from '../../storage';
import type { ProjectInitializationService } from '../../services/projects/ProjectInitializationService';
import type { PermaGraphService } from '../../services/projects/PermaGraphService';

type WsManager = {
  unsubscribeProject?: (projectId: string) => void;
};

export class ProjectCrudController {
  constructor(
    private readonly storage: IStorage,
    private readonly initializationService: ProjectInitializationService,
    private readonly permaGraphService: PermaGraphService,
    private readonly wsManager?: WsManager
  ) {}

  listProjects = async (_req: Request, res: Response): Promise<void> => {
    try {
      const projects = await this.storage.listProjects();
      res.json(projects);
    } catch (error) {
      console.error('Failed to list projects:', error);
      res.status(500).json({ error: 'Failed to fetch projects' });
    }
  };

  createSystemProject = async (req: Request, res: Response): Promise<void> => {
    try {
      const { name, description, templateId, config, projectPath } = req.body;
      if (!templateId) {
        res.status(400).json({ error: 'templateId is required' });
        return;
      }
      if (!projectPath) {
        res.status(400).json({ error: 'projectPath is required' });
        return;
      }

      const projectData = {
        name: name || 'ZHUL_SYS_PROJECT',
        description: description || 'Architecture analysis project',
        templateId,
        projectPath,
        metadata: config ? { config } : {},
      };

      const project = await this.storage.createProject(projectData as any);
      res.json(project);

      this.initializationService
        .initialize(project.id, project.projectPath)
        .catch(error => console.error('PermaGraph initialization failed', error));
    } catch (error) {
      console.error('Create project error:', error);
      res.status(500).json({ error: 'Failed to create project' });
    }
  };

  createProject = async (req: Request, res: Response): Promise<void> => {
    try {
      const { name, description, templateId, config, projectPath } = req.body;
      if (!name || !templateId || !projectPath) {
        res.status(400).json({ error: 'Missing required fields' });
        return;
      }
      const projectData = {
        name,
        description: description || null,
        templateId,
        projectPath,
        metadata: config ? { config } : {},
      };
      const project = await this.storage.createProject(projectData as any);
      res.json(project);
    } catch (error) {
      console.error('Create project error:', error);
      res.status(500).json({ error: 'Database error' });
    }
  };

  importProject = async (req: Request, res: Response): Promise<void> => {
    try {
      const { file } = req;
      if (!file) {
        res.status(400).json({ error: 'No file provided' });
        return;
      }
      const importData = JSON.parse(file.buffer.toString());
      if (!importData.project?.projectPath) {
        res
          .status(400)
          .json({ error: 'Imported project is missing projectPath' });
        return;
      }
      const project = await this.storage.createProject(importData.project);
      for (const nodeData of importData.nodes || []) {
        await this.storage.createGraphNode({
          ...nodeData,
          projectId: project.id,
        });
      }
      for (const edgeData of importData.edges || []) {
        await this.storage.createGraphEdge({
          ...edgeData,
          projectId: project.id,
        });
      }
      res.json({
        project,
        nodesImported: (importData.nodes || []).length,
        edgesImported: (importData.edges || []).length,
      });
    } catch (error) {
      console.error('Import project error:', error);
      res.status(500).json({ error: 'Failed to import project' });
    }
  };

  getProject = async (req: Request, res: Response): Promise<void> => {
    try {
      const project = await this.storage.getProject(req.params.id);
      if (!project) {
        res.status(404).json({ error: 'Project not found' });
        return;
      }
      res.json(project);
    } catch (error) {
      console.error('Failed to fetch project:', error);
      res.status(500).json({ error: 'Failed to fetch project' });
    }
  };

  updateProject = async (req: Request, res: Response): Promise<void> => {
    try {
      const updates = insertProjectSchema.partial().parse(req.body);
      const project = await this.storage.updateProject(req.params.id, updates);
      res.json(project);
    } catch (error) {
      console.error('Project update error:', error);
      res.status(400).json({ error: 'Invalid update data' });
    }
  };

  deleteProject = async (req: Request, res: Response): Promise<void> => {
    const { id } = req.params;
    try {
      await this.permaGraphService.shutdown(id, this.wsManager);
      await this.storage.deleteProject(id);
      res.status(204).send();
    } catch (error) {
      console.error('Failed to delete project:', error);
      res.status(500).json({ error: 'Failed to delete project' });
    }
  };
}

export default ProjectCrudController;
