import type { Request, Response } from 'express';

import { logger } from '../../utils/logger';
import type {
  CloneProjectPayload,
  CreateProjectPayload,
  MultiProjectClient,
  ProjectActivityParams,
  UpdateProjectPayload,
} from '../../services/permaGraphMultiProjectClient';
import { PermaGraphClientError as ClientError } from '../../services/permaGraphMultiProjectClient';

function mapTags(tags?: string | string[]): string[] | undefined {
  if (!tags) {
    return undefined;
  }

  if (Array.isArray(tags)) {
    return tags.flatMap(tag => tag.split(',').map(item => item.trim()).filter(Boolean));
  }

  return tags
    .split(',')
    .map(tag => tag.trim())
    .filter(Boolean);
}

function parsePaginationParam(value?: string | string[]): number | undefined {
  if (Array.isArray(value)) {
    return parsePaginationParam(value[0]);
  }

  if (value === undefined) {
    return undefined;
  }

  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? undefined : parsed;
}

function handleError(
  res: Response,
  error: unknown,
  fallbackMessage: string
): Response {
  if (error instanceof ClientError) {
    logger.error('PermaGraph multi-project API error', error);
    return res.status(error.statusCode).json({
      success: false,
      error: error.message,
      details: error.details,
    });
  }

  logger.error(fallbackMessage, error);
  return res.status(500).json({
    success: false,
    error: fallbackMessage,
  });
}

export class ProjectController {
  constructor(private readonly client: MultiProjectClient) {}

  listProjects = async (req: Request, res: Response) => {
    try {
      const { tenant_id, status, owner, tags } = req.query;

      logger.info(
        `📋 Listing projects with filters: tenant=${tenant_id}, status=${status}`
      );

      const projects = await this.client.listProjects({
        tenant_id: tenant_id as string | undefined,
        status: status as string | undefined,
        owner: owner as string | undefined,
        tags: mapTags(tags as string | string[] | undefined),
      });

      res.json({
        success: true,
        projects,
        total: projects.length,
      });
    } catch (error) {
      handleError(res, error, 'Failed to list projects');
    }
  };

  getProject = async (req: Request, res: Response) => {
    try {
      const { projectId } = req.params;

      logger.info(`📋 Getting project details: ${projectId}`);

      const project = await this.client.getProject(projectId);
      const statistics = await this.client.getProjectStatistics(projectId);

      res.json({
        success: true,
        project: {
          ...project,
          statistics,
        },
      });
    } catch (error) {
      if (error instanceof ClientError && error.statusCode === 404) {
        return res.status(404).json({
          success: false,
          error: 'Project not found',
        });
      }

      handleError(res, error, 'Failed to retrieve project');
    }
  };

  createProject = async (req: Request, res: Response) => {
    try {
      const payload = req.body as CreateProjectPayload;

      if (!payload.name?.trim()) {
        return res.status(400).json({
          success: false,
          error: 'Project name is required',
        });
      }

      logger.info(`🚀 Creating new project: ${payload.name}`);

      const project = await this.client.createProject({
        ...payload,
        name: payload.name.trim(),
        description: payload.description?.trim(),
        tags: payload.tags || [],
      });

      res.status(201).json({
        success: true,
        project,
        message: `Project "${payload.name}" created successfully`,
      });
    } catch (error) {
      handleError(res, error, 'Failed to create project');
    }
  };

  cloneProject = async (req: Request, res: Response) => {
    try {
      const payload = req.body as CloneProjectPayload;

      if (!payload.source_project_id || !payload.name?.trim()) {
        return res.status(400).json({
          success: false,
          error: 'Source project ID and new name are required',
        });
      }

      logger.info(
        `📋 Cloning project ${payload.source_project_id} to ${payload.name}`
      );

      const project = await this.client.cloneProject({
        ...payload,
        name: payload.name.trim(),
        description: payload.description?.trim(),
      });

      res.status(201).json({
        success: true,
        project,
        message: `Project cloned successfully as "${payload.name}"`,
      });
    } catch (error) {
      handleError(res, error, 'Failed to clone project');
    }
  };

  updateProject = async (req: Request, res: Response) => {
    try {
      const { projectId } = req.params;
      const payload = req.body as UpdateProjectPayload;

      logger.info(`📝 Updating project: ${projectId}`);

      const project = await this.client.updateProject(projectId, {
        ...payload,
        name: payload.name?.trim(),
        description: payload.description?.trim(),
      });

      res.json({
        success: true,
        project,
        message: 'Project updated successfully',
      });
    } catch (error) {
      handleError(res, error, 'Failed to update project');
    }
  };

  archiveProject = async (req: Request, res: Response) => {
    try {
      const { projectId } = req.params;

      logger.info(`📦 Archiving project: ${projectId}`);

      await this.client.archiveProject(projectId);

      res.json({
        success: true,
        message: 'Project archived successfully',
      });
    } catch (error) {
      handleError(res, error, 'Failed to archive project');
    }
  };

  deleteProject = async (req: Request, res: Response) => {
    try {
      const { projectId } = req.params;
      const { force } = req.body as { force?: boolean };

      logger.info(`🗑️ Deleting project: ${projectId} (force: ${force})`);

      await this.client.deleteProject(projectId, force === true);

      res.json({
        success: true,
        message: 'Project deleted successfully',
      });
    } catch (error) {
      handleError(res, error, 'Failed to delete project');
    }
  };

  compareProjects = async (req: Request, res: Response) => {
    try {
      const { project_a, project_b } = req.body as {
        project_a?: string;
        project_b?: string;
      };

      if (!project_a || !project_b) {
        return res.status(400).json({
          success: false,
          error: 'Both project_a and project_b are required',
        });
      }

      logger.info(`🔍 Comparing projects: ${project_a} vs ${project_b}`);

      const comparison = await this.client.compareProjects(project_a, project_b);

      res.json({
        success: true,
        comparison,
      });
    } catch (error) {
      handleError(res, error, 'Failed to compare projects');
    }
  };

  bulkOperation = async (req: Request, res: Response) => {
    try {
      const payload = req.body as {
        operation?: string;
        project_ids?: string[];
        options?: Record<string, unknown>;
      };

      if (!payload.operation || !payload.project_ids?.length) {
        return res.status(400).json({
          success: false,
          error: 'Operation and project_ids are required',
        });
      }

      logger.info(
        `🛠️ Performing bulk operation ${payload.operation} on ${payload.project_ids.length} projects`
      );

      const result = await this.client.bulkOperation({
        operation: payload.operation,
        project_ids: payload.project_ids,
        options: payload.options,
      });

      res.json({
        success: true,
        result,
      });
    } catch (error) {
      handleError(res, error, 'Failed to execute bulk operation');
    }
  };

  getProjectStatistics = async (req: Request, res: Response) => {
    try {
      const { projectId } = req.params;

      logger.info(`📊 Getting statistics for project: ${projectId}`);

      const statistics = await this.client.getProjectStatistics(projectId);

      res.json({
        success: true,
        statistics,
      });
    } catch (error) {
      handleError(res, error, 'Failed to retrieve project statistics');
    }
  };

  switchProject = async (req: Request, res: Response) => {
    try {
      const { projectId } = req.params;

      logger.info(`🔄 Switching to project context: ${projectId}`);

      const project = await this.client.getProject(projectId);

      res.json({
        success: true,
        current_project: project,
        message: `Switched to project "${project?.name ?? projectId}"`,
      });
    } catch (error) {
      if (error instanceof ClientError && error.statusCode === 404) {
        return res.status(404).json({
          success: false,
          error: 'Project not found',
        });
      }

      handleError(res, error, 'Failed to switch project');
    }
  };

  getProjectActivity = async (req: Request, res: Response) => {
    try {
      const { projectId } = req.params;
      const limit = parsePaginationParam(req.query.limit as string | string[] | undefined);
      const offset = parsePaginationParam(req.query.offset as string | string[] | undefined);

      logger.info(
        `📈 Getting activity for project: ${projectId} with limit=${limit ?? 'default'} offset=${
          offset ?? 'default'
        }`
      );

      const params: ProjectActivityParams = {};
      if (limit !== undefined) {
        params.limit = limit;
      }
      if (offset !== undefined) {
        params.offset = offset;
      }

      const activity = await this.client.getProjectActivity(projectId, params);

      res.json({
        success: true,
        ...activity,
      });
    } catch (error) {
      handleError(res, error, 'Failed to retrieve project activity');
    }
  };
}
