import type { Request, Response } from 'express';

import { ProjectLockService } from '../../services/project-lock-service';
import type { CliCommandService } from '../../services/projects/CliCommandService';
import type { PermaGraphService } from '../../services/projects/PermaGraphService';

export class ProjectCliController {
  constructor(
    private readonly cliService: CliCommandService,
    private readonly permaGraphService: PermaGraphService,
    private readonly lockService: ProjectLockService
  ) {}

  scaffoldModule = (req: Request, res: Response) =>
    this.runScaffold(req, res, 'make:module', 'scaffold:module');

  scaffoldService = (req: Request, res: Response) =>
    this.runScaffold(req, res, 'make:service', 'scaffold:service');

  scaffoldController = (req: Request, res: Response) =>
    this.runScaffold(req, res, 'make:controller', 'scaffold:controller');

  private async runScaffold(
    req: Request,
    res: Response,
    operation: string,
    traceAction: string
  ): Promise<void> {
    const { id } = req.params;
    const release = await this.lockService.acquire(id);
    if (!release) {
      res.status(409).json({ error: 'Project is locked' });
      return;
    }

    try {
      const result = await this.cliService.execute(
        req.get('host'),
        id,
        operation,
        { ...req.body },
        true
      );

      await this.permaGraphService.recordTraceability(id, traceAction, result);
      res.json({ diffs: result });
    } catch (error) {
      console.error('CLI scaffold error:', error);
      res.status(500).json({ error: 'Failed to scaffold component' });
    } finally {
      release();
    }
  }
}

export default ProjectCliController;
