import type { Request, Response } from 'express';

import type { ProjectFileService } from '../../services/projects/ProjectFileService';
import type { ProjectGraphService } from '../../services/projects/ProjectGraphService';
import type { ProjectMetricsService } from '../../services/projects/ProjectMetricsService';
import { ProjectLockService } from '../../services/project-lock-service';
import { errorResponse } from '../../utils/error-response';

export class ProjectFilesystemController {
  constructor(
    private readonly fileService: ProjectFileService,
    private readonly graphService: ProjectGraphService,
    private readonly metrics: ProjectMetricsService,
    private readonly lockService: ProjectLockService
  ) {}

  getFile = async (req: Request, res: Response): Promise<void> => {
    try {
      const filePath = (req.params as any)[0];
      const content = await this.fileService.readFile(req.params.id, filePath);
      res.type('text/plain').send(content);
    } catch (error: any) {
      if (error.code === 'ENOENT') {
        errorResponse(res, 404, 'File not found');
        return;
      }
      if (error.status === 403) {
        errorResponse(res, 403, 'Access outside project root');
        return;
      }
      errorResponse(res, error.status || 500, 'Failed to read file');
    }
  };

  applyChanges = async (req: Request, res: Response): Promise<void> => {
    const { id } = req.params;
    const release = await this.lockService.acquire(id);
    if (!release) {
      errorResponse(res, 409, 'Project is locked');
      return;
    }
    try {
      const { files } = req.body as { files: { path: string; content: string }[] };
      if (!Array.isArray(files)) {
        errorResponse(res, 400, 'files must be an array');
        return;
      }
      const result = await this.fileService.applyChanges(id, files);
      this.metrics.incrementChangesApplied(id, result.filesApplied);
      this.metrics.incrementLinesModified(id, result.linesModified);
      await this.graphService.handlePostApply(id, req.get('host'));
      res.json({ success: true, applied: result.filesApplied });
    } catch (error: any) {
      console.error('Apply changes error:', error);
      try {
        await this.fileService.rollback(id);
      } catch (rollbackError) {
        console.error('Rollback after apply failed:', rollbackError);
      }
      errorResponse(res, error.status || 500, 'Failed to apply changes');
    } finally {
      release();
    }
  };

  rollback = async (req: Request, res: Response): Promise<void> => {
    try {
      await this.fileService.rollback(req.params.id);
      res.json({ success: true });
    } catch (error: any) {
      if (error.status === 404) {
        errorResponse(res, 404, 'No rollback data');
        return;
      }
      console.error('Rollback error:', error);
      errorResponse(res, 500, 'Failed to rollback');
    }
  };
}

export default ProjectFilesystemController;
