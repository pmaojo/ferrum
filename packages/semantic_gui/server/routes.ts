import { createServer, type Server } from 'http';

import { type Express, Router } from 'express';

import traceIdMiddleware from './middleware/traceId';
import { orchestratorRouter } from './orchestrator';
import cliRoutes from './routes/cliRoutes';
import connectorRoutes from './routes/connectorRoutes';
import dashboardRoutes from './routes/dashboardRoutes';
import { attachEdgeRoutes } from './routes/edgesRoutes';
import monitoringRoutes from './routes/monitoringRoutes';
import multiProjectRoutes from './routes/multiProjectRoutes';
import { attachNodeRoutes } from './routes/nodesRoutes';
import performanceRoutes from './routes/performanceRoutes';
import { attachPermaGraphRoutes } from './routes/permagraphRoutes';
import { attachProjectRoutes } from './routes/projectsRoutes';
import semanticRoutes from './routes/semanticRoutes';
import standardsRoutes from './routes/standardsRoutes';
import templateRoutes from './routes/templateRoutes';
import { CLIExecutor } from './services/cli/CLIExecutor';
import { featureFlagService } from './services/FeatureFlagService';
import { graphStreamAdapter } from './services/graphStream';
import { lookupTemplate } from './services/templateLookup';
import { TemplateService } from './services/TemplateService';
import { WebSocketManager } from './services/websocket-manager';
import type { IStorage } from './storage';
import { errorResponse } from './utils/error-response';
import { logger } from './utils/logger';

export async function registerRoutes(
  app: Express,
  storageImpl?: IStorage
): Promise<Server> {
  if (!storageImpl) {
    const mod = await import('./storage');
    storageImpl = mod.storage;
  }

  // Type guard to ensure storageImpl is defined
  if (!storageImpl) {
    throw new Error('Storage implementation is required');
  }

  // Now we can safely use storageImpl as non-undefined
  const storage: IStorage = storageImpl;

  const httpServer = createServer(app);
  const wsManager = new WebSocketManager(httpServer, graphStreamAdapter);
  const templateService = new TemplateService();
  const cliExecutor = new CLIExecutor(wsManager);

  // Make WebSocket manager and graph stream adapter available to routes
  app.set('wsManager', wsManager);
  app.set('graphStream', graphStreamAdapter);
  app.set('cliExecutor', cliExecutor);
  // Expose storage implementation for routers that need direct access
  app.set('storage', storage);

  // Trace ID middleware should run before any routes
  app.use(traceIdMiddleware);

  const api = Router();

  attachProjectRoutes(api, storage);
  attachNodeRoutes(api, storage);
  attachEdgeRoutes(api, storage);
  // Generic connector routes (replaces framework-specific routes)
  api.use(connectorRoutes);
  attachPermaGraphRoutes(api, storage);

  // Orchestrator routes
  api.use(orchestratorRouter);

  // Standards export/import routes
  api.use('/standards', standardsRoutes);

  // Multi-project management routes
  api.use('/projects', multiProjectRoutes);

  // Semantic navigation routes
  api.use('/semantic', semanticRoutes);

  // Performance monitoring routes
  api.use('/performance', performanceRoutes);

  // System monitoring and observability routes
  api.use('/monitoring', monitoringRoutes);

  // Dashboard management routes
  api.use('/dashboard', dashboardRoutes);

  // Template management routes
  api.use('/templates', templateRoutes);

  // CLI operations routes
  api.use(cliRoutes);

  app.get('/config', (_req, res) => {
    res.json({ flags: featureFlagService.getAllFlags() });
  });

  app.get('/api/v1/templates-legacy', async (_req, res) => {
    try {
      const templates = await templateService.listTemplates();
      res.json(templates);
    } catch (error) {
      logger.error('Failed to list templates', {
        operation: 'listTemplates',
        error: (error as Error).message,
      });
      errorResponse(res, 500, 'Failed to fetch templates');
    }
  });

  api.get('/templates/:id', async (req, res) => {
    try {
      const template = await lookupTemplate(
        req.params.id,
        storage,
        templateService
      );
      if (!template) {
        return errorResponse(res, 404, 'Template not found');
      }
      res.json(template);
    } catch (error) {
      logger.error('Failed to fetch template', {
        operation: 'getTemplate',
        templateId: req.params.id,
        error: (error as Error).message,
      });
      errorResponse(res, 500, 'Failed to fetch template');
    }
  });

  app.use('/api/v1', api);
  return httpServer;
}
