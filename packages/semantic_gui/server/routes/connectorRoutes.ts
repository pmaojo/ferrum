import { Router } from 'express';

import { authMiddleware } from '../middleware/auth';
import { requireRole } from '../middleware/requireRole';
import { GenericConnector } from '../services/GenericConnector';
import { TemplateService } from '../services/TemplateService';
import { errorResponse } from '../utils/error-response';
import { logger } from '../utils/logger';
import type { IStorage } from '../storage';

const router = Router();
const templateService = new TemplateService();

// Map to store active connectors per project
const connectors = new Map<string, GenericConnector>();

/**
 * Initialize connector for a project based on template configuration
 */
router.post('/projects/:projectId/connector/init', async (req, res) => {
  try {
    const { projectId } = req.params;
    const { templateId } = req.body;

    const storage = req.app.get('storage') as IStorage | undefined;
    if (!storage) {
      return errorResponse(res, 500, 'Storage not configured');
    }

    const project = await storage.getProject(projectId);
    if (!project) {
      return errorResponse(res, 404, 'Project not found');
    }

    const projectPath = project.projectPath;
    const templateToUse = templateId ?? project.templateId;

    // Get template configuration
    const template = await templateService.getTemplate(templateToUse);
    if (!template) {
      return errorResponse(res, 404, 'Template not found');
    }

    if (!template.connector) {
      return errorResponse(
        res,
        400,
        'Template does not have connector configuration'
      );
    }

    // Create new generic connector
    const connector = new GenericConnector(
      template.connector,
      projectPath,
      templateToUse,
      projectId
    );
    connectors.set(projectId, connector);

    // Get WebSocket manager from app
    const wsManager = req.app.get('wsManager');

    // Set up event listeners based on template configuration
    const events = template.connector.fileWatcher?.events || [];
    events.forEach(eventName => {
      connector.on(eventName, data => {
        wsManager?.broadcast(`project:${projectId}`, {
          type: eventName,
          data,
          timestamp: new Date().toISOString(),
        });

        logger.info(`Connector event: ${eventName}`, {
          operation: `connector.${eventName}`,
          projectId,
          data,
        });
      });
    });

    // Start file watcher if configured
    if (template.connector.fileWatcher) {
      await connector.startFileWatcher();
    }

    res.json({
      message: 'Connector initialized successfully',
      templateId: templateToUse,
      projectId,
      projectPath,
      connectorType: template.connector.type,
    });
  } catch (error) {
    logger.error('Failed to initialize connector', {
      operation: 'connector.init',
      error: (error as Error).message,
    });
    errorResponse(res, 500, 'Failed to initialize connector');
  }
});

/**
 * Execute connector command
 */
router.post('/projects/:projectId/connector/execute', async (req, res) => {
  try {
    const { projectId } = req.params;
    const { command, args = [] } = req.body;

    const connector = connectors.get(projectId);
    if (!connector) {
      return errorResponse(
        res,
        404,
        'Connector not initialized for this project'
      );
    }

    const output = await connector.executeCommand(command, args);

    res.json({
      success: true,
      command,
      args,
      output,
    });
  } catch (error) {
    logger.error('Failed to execute connector command', {
      operation: 'connector.execute',
      error: (error as Error).message,
    });
    errorResponse(res, 500, 'Failed to execute command');
  }
});

/**
 * Generate architecture graph
 */
router.get('/projects/:projectId/connector/graph', async (req, res) => {
  try {
    const { projectId } = req.params;

    const connector = connectors.get(projectId);
    if (!connector) {
      return errorResponse(
        res,
        404,
        'Connector not initialized for this project'
      );
    }

    // Generate architecture graph
    const graphData = await connector.generateArchitectureGraph();

    // Convert to SCG format
    const { nodes, edges } = await connector.convertToSCGGraph(projectId);

    res.json({
      success: true,
      graphData,
      scgGraph: { nodes, edges },
    });
  } catch (error) {
    logger.error('Failed to generate architecture graph', {
      operation: 'connector.graph',
      error: (error as Error).message,
    });
    errorResponse(res, 500, 'Failed to generate architecture graph');
  }
});

/**
 * Validate architecture
 */
router.post('/projects/:projectId/connector/validate', async (req, res) => {
  try {
    const { projectId } = req.params;

    const connector = connectors.get(projectId);
    if (!connector) {
      return errorResponse(
        res,
        404,
        'Connector not initialized for this project'
      );
    }

    const validation = await connector.validateArchitecture();

    res.json({
      success: true,
      validation,
    });
  } catch (error) {
    logger.error('Failed to validate architecture', {
      operation: 'connector.validate',
      error: (error as Error).message,
    });
    errorResponse(res, 500, 'Failed to validate architecture');
  }
});

/**
 * Analyze project structure
 */
router.get('/projects/:projectId/connector/analyze', async (req, res) => {
  try {
    const { projectId } = req.params;

    const connector = connectors.get(projectId);
    if (!connector) {
      return errorResponse(
        res,
        404,
        'Connector not initialized for this project'
      );
    }

    const project = await connector.analyzeCodeStructure();

    res.json({
      success: true,
      project,
    });
  } catch (error) {
    logger.error('Failed to analyze project structure', {
      operation: 'connector.analyze',
      error: (error as Error).message,
    });
    errorResponse(res, 500, 'Failed to analyze project structure');
  }
});

/**
 * Apply code changes
 */
router.post(
  '/projects/:projectId/connector/apply',
  authMiddleware,
  requireRole('owner', 'reader'),
  async (req, res) => {
    try {
      const { projectId } = req.params;
      const { changes } = req.body;

      if (!changes || !Array.isArray(changes)) {
        return errorResponse(res, 400, 'Changes array is required');
      }

      const connector = connectors.get(projectId);
      if (!connector) {
        return errorResponse(
          res,
          404,
          'Connector not initialized for this project'
        );
      }

      await connector.applyCodeChanges(changes);

      res.json({
        success: true,
        message: `Applied ${changes.length} changes`,
        changesCount: changes.length,
      });
    } catch (error) {
      logger.error('Failed to apply code changes', {
        operation: 'connector.apply',
        error: (error as Error).message,
      });
      errorResponse(res, 500, 'Failed to apply code changes');
    }
  }
);

/**
 * Get connector status
 */
router.get('/projects/:projectId/connector/status', async (req, res) => {
  try {
    const { projectId } = req.params;

    const connector = connectors.get(projectId);
    if (!connector) {
      return res.json({
        initialized: false,
        projectId,
      });
    }

    res.json({
      initialized: true,
      projectId,
      // Add more status information as needed
    });
  } catch (error) {
    logger.error('Failed to get connector status', {
      operation: 'connector.status',
      error: (error as Error).message,
    });
    errorResponse(res, 500, 'Failed to get connector status');
  }
});

/**
 * Stop connector
 */
router.delete('/projects/:projectId/connector', async (req, res) => {
  try {
    const { projectId } = req.params;

    const connector = connectors.get(projectId);
    if (!connector) {
      return errorResponse(
        res,
        404,
        'Connector not initialized for this project'
      );
    }

    // Stop file watcher
    connector.stopFileWatcher();

    // Remove from map
    connectors.delete(projectId);

    res.json({
      success: true,
      message: 'Connector stopped successfully',
      projectId,
    });
  } catch (error) {
    logger.error('Failed to stop connector', {
      operation: 'connector.stop',
      error: (error as Error).message,
    });
    errorResponse(res, 500, 'Failed to stop connector');
  }
});

export default router;
