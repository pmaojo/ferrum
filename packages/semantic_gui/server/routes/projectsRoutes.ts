import type { Router } from 'express';
import multer from 'multer';
import client from 'prom-client';

import { authMiddleware } from '../middleware/auth';
import { requireRole } from '../middleware/requireRole';
import { PermaGraphController } from '../services/permagraph-controller';
import { ProjectLockService } from '../services/project-lock-service';
import type { IStorage } from '../storage';
import { ProjectCliController } from '../controllers/projects/ProjectCliController';
import { ProjectCrudController } from '../controllers/projects/ProjectCrudController';
import { ProjectFilesystemController } from '../controllers/projects/ProjectFilesystemController';
import { ProjectGraphController } from '../controllers/projects/ProjectGraphController';
import { CliCommandService } from '../services/projects/CliCommandService';
import ProjectFileService from '../services/projects/ProjectFileService';
import ProjectGraphService from '../services/projects/ProjectGraphService';
import ProjectInitializationService from '../services/projects/ProjectInitializationService';
import PermaGraphService from '../services/projects/PermaGraphService';
import ProjectMetricsService from '../services/projects/ProjectMetricsService';

const upload = multer({ storage: multer.memoryStorage() });

const changesAppliedCounter =
  (client.register.getSingleMetric('changes_applied_total') as client.Counter) ||
  new client.Counter({
    name: 'changes_applied_total',
    help: 'Number of file or graph changes applied',
    labelNames: ['projectId'],
  });

const linesModifiedCounter =
  (client.register.getSingleMetric('lines_modified_total') as client.Counter) ||
  new client.Counter({
    name: 'lines_modified_total',
    help: 'Total lines modified when applying changes',
    labelNames: ['projectId'],
  });

const permagraphSyncHistogram =
  (client.register.getSingleMetric('permagraph_sync_seconds') as client.Histogram) ||
  new client.Histogram({
    name: 'permagraph_sync_seconds',
    help: 'Duration of PermaGraph synchronization in seconds',
    labelNames: ['projectId', 'mode'],
  });

export function attachProjectRoutes(app: Router, storageImpl: IStorage) {
  let controllers = app.get('permagraphControllers') as
    | Map<string, PermaGraphController>
    | undefined;
  if (!controllers) {
    controllers = new Map<string, PermaGraphController>();
    (app as any).set?.('permagraphControllers', controllers);
  }

  const metricsService = new ProjectMetricsService(
    changesAppliedCounter,
    linesModifiedCounter,
    permagraphSyncHistogram
  );

  const permaGraphService = new PermaGraphService(
    controllers,
    metricsService,
    projectId => new PermaGraphController(projectId)
  );

  const initializationService = new ProjectInitializationService(permaGraphService);
  const cliService = new CliCommandService();
  const fileService = new ProjectFileService(storageImpl);
  const graphStream = app.get('graphStream') as
    | { send_batch: (events: unknown) => void }
    | undefined;
  const graphService = new ProjectGraphService(
    storageImpl,
    cliService,
    permaGraphService,
    metricsService,
    graphStream
  );

  const lockService = new ProjectLockService();
  const wsManager = app.get('wsManager') as { unsubscribeProject?: (id: string) => void } | undefined;

  const crudController = new ProjectCrudController(
    storageImpl,
    initializationService,
    permaGraphService,
    wsManager
  );
  const filesystemController = new ProjectFilesystemController(
    fileService,
    graphService,
    metricsService,
    lockService
  );
  const cliController = new ProjectCliController(cliService, permaGraphService, lockService);
  const graphController = new ProjectGraphController(graphService);

  app.get('/projects', crudController.listProjects);
  app.post('/projects/create', crudController.createSystemProject);
  app.post('/projects', crudController.createProject);
  app.post('/projects/import', upload.single('file'), crudController.importProject);
  app.get('/projects/:id', crudController.getProject);
  app.put('/projects/:id', crudController.updateProject);
  app.delete('/projects/:id', crudController.deleteProject);

  app.get('/projects/:id/files/*', filesystemController.getFile);
  app.post(
    '/projects/:id/apply',
    authMiddleware,
    requireRole('owner', 'reader'),
    filesystemController.applyChanges
  );
  app.post(
    '/projects/:id/rollback',
    authMiddleware,
    requireRole('owner', 'reader'),
    filesystemController.rollback
  );

  app.post('/projects/:id/scaffold/module', cliController.scaffoldModule);
  app.post('/projects/:id/scaffold/service', cliController.scaffoldService);
  app.post('/projects/:id/scaffold/controller', cliController.scaffoldController);

  app.get('/projects/:projectId/graph', graphController.getGraph);
  app.post('/projects/:id/graph/refresh', graphController.refreshGraph);
  app.post('/projects/:projectId/analyze-github', graphController.analyzeGitHub);
  app.post(
    '/projects/:projectId/analyze',
    upload.array('files'),
    graphController.analyzeUpload
  );
  app.post('/projects/:projectId/confirm-nodes', graphController.confirmNodes);
  app.get('/projects/:projectId/validation', graphController.getValidationResults);
  app.post('/projects/:projectId/validate', graphController.validateProject);
  app.get('/projects/:projectId/score', graphController.getScore);
  app.get('/projects/:projectId/export', graphController.exportProject);
  app.get('/projects/:projectId/ai-insights', graphController.getAiInsights);
  app.post('/projects/:projectId/ai-analyze-request', graphController.analyzeAiRequest);
}
