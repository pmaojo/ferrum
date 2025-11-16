import { Router } from 'express';
import client from 'prom-client';
import { z } from 'zod';

import { PermaGraphController } from '../services/permagraph-controller';
import { logger } from '../utils/logger';

const router = Router();

client.collectDefaultMetrics();

router.get('/metrics', async (_req, res) => {
  res.set('Content-Type', client.register.contentType);
  res.end(await client.register.metrics());
});

// Validation schemas
const AlertResolveSchema = z.object({
  alertId: z.string(),
});

const MetricsQuerySchema = z.object({
  metricName: z.string(),
  startTime: z.string().optional(),
  endTime: z.string().optional(),
  labels: z.record(z.string()).optional(),
});

/**
 * Get system health status
 */
router.get('/health', async (req, res) => {
  try {
    const permagraphController = new PermaGraphController();
    const healthStatus = await permagraphController.getSystemHealth();

    res.json({
      success: true,
      data: healthStatus,
    });
  } catch (error) {
    logger.error('Error getting system health:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get system health',
    });
  }
});

/**
 * Get performance metrics
 */
router.get('/metrics/performance', async (req, res) => {
  try {
    const permagraphController = new PermaGraphController();
    const metrics = await permagraphController.getPerformanceMetrics();

    res.json({
      success: true,
      data: metrics,
    });
  } catch (error) {
    logger.error('Error getting performance metrics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get performance metrics',
    });
  }
});

/**
 * Query specific metrics
 */
router.post('/metrics/query', async (req, res) => {
  try {
    const { metricName, startTime, endTime, labels } = MetricsQuerySchema.parse(
      req.body
    );

    const permagraphController = new PermaGraphController();
    const metrics = await permagraphController.queryMetrics({
      metricName,
      startTime: startTime ? new Date(startTime) : undefined,
      endTime: endTime ? new Date(endTime) : undefined,
      labels,
    });

    res.json({
      success: true,
      data: metrics,
    });
  } catch (error) {
    logger.error('Error querying metrics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to query metrics',
    });
  }
});

/**
 * Get active alerts
 */
router.get('/alerts', async (req, res) => {
  try {
    const permagraphController = new PermaGraphController();
    const alerts = await permagraphController.getActiveAlerts();

    res.json({
      success: true,
      data: alerts,
    });
  } catch (error) {
    logger.error('Error getting alerts:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get alerts',
    });
  }
});

/**
 * Resolve an alert
 */
router.post('/alerts/:alertId/resolve', async (req, res) => {
  try {
    const { alertId } = req.params;

    const permagraphController = new PermaGraphController();
    const success = await permagraphController.resolveAlert(alertId);

    if (success) {
      res.json({
        success: true,
        message: 'Alert resolved successfully',
      });
    } else {
      res.status(404).json({
        success: false,
        error: 'Alert not found',
      });
    }
  } catch (error) {
    logger.error('Error resolving alert:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to resolve alert',
    });
  }
});

/**
 * Get alert history
 */
router.get('/alerts/history', async (req, res) => {
  try {
    const { component, severity, limit } = req.query;

    const permagraphController = new PermaGraphController();
    const history = await permagraphController.getAlertHistory({
      component: component as string,
      severity: severity as string,
      limit: limit ? parseInt(limit as string) : 100,
    });

    res.json({
      success: true,
      data: history,
    });
  } catch (error) {
    logger.error('Error getting alert history:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get alert history',
    });
  }
});

/**
 * Get component health checks
 */
router.get('/health/components', async (req, res) => {
  try {
    const permagraphController = new PermaGraphController();
    const components = await permagraphController.getComponentHealthChecks();

    res.json({
      success: true,
      data: components,
    });
  } catch (error) {
    logger.error('Error getting component health checks:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get component health checks',
    });
  }
});

/**
 * Trigger health check for specific component
 */
router.post('/health/components/:component/check', async (req, res) => {
  try {
    const { component } = req.params;

    const permagraphController = new PermaGraphController();
    const result = await permagraphController.triggerHealthCheck(component);

    res.json({
      success: true,
      data: result,
    });
  } catch (error) {
    logger.error('Error triggering health check:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to trigger health check',
    });
  }
});

/**
 * Get system resource usage
 */
router.get('/system/resources', async (req, res) => {
  try {
    const permagraphController = new PermaGraphController();
    const resources = await permagraphController.getSystemResources();

    res.json({
      success: true,
      data: resources,
    });
  } catch (error) {
    logger.error('Error getting system resources:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get system resources',
    });
  }
});

/**
 * Get monitoring dashboard configuration
 */
router.get('/dashboard/config', async (req, res) => {
  try {
    const permagraphController = new PermaGraphController();
    const config = await permagraphController.getDashboardConfig();

    res.json({
      success: true,
      data: config,
    });
  } catch (error) {
    logger.error('Error getting dashboard config:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get dashboard config',
    });
  }
});

/**
 * Create monitoring dashboard
 */
router.post('/dashboard', async (req, res) => {
  try {
    const { name, config } = req.body;

    const permagraphController = new PermaGraphController();
    const dashboardId = await permagraphController.createDashboard(
      name,
      config
    );

    res.json({
      success: true,
      data: { dashboardId },
    });
  } catch (error) {
    logger.error('Error creating dashboard:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to create dashboard',
    });
  }
});

export default router;
