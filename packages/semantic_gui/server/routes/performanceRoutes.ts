/**
 * Performance API Routes
 * Provides endpoints for performance monitoring and optimization
 */

import { Router } from 'express';
import { performanceMonitor } from '../../shared/utils/performance-monitor';
import { serviceManager } from '../../shared/utils/service-manager';
import { templateCache, projectCache, graphCache } from '../../shared/utils/cache-manager';

const router = Router();

/**
 * GET /api/performance/report
 * Get comprehensive performance report
 */
router.get('/report', async (req, res) => {
  try {
    const report = performanceMonitor.generatePerformanceReport();
    res.json(report);
  } catch (error) {
    console.error('Failed to generate performance report:', error);
    res.status(500).json({ 
      error: 'Failed to generate performance report',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * GET /api/performance/metrics
 * Get raw performance metrics
 */
router.get('/metrics', async (req, res) => {
  try {
    const { service, timeRange } = req.query;
    const timeRangeMs = timeRange ? parseInt(timeRange as string) : undefined;
    
    const metrics = performanceMonitor.getMetrics(
      service as string, 
      timeRangeMs
    );
    
    res.json({ metrics });
  } catch (error) {
    console.error('Failed to get performance metrics:', error);
    res.status(500).json({ 
      error: 'Failed to get performance metrics',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * GET /api/performance/services
 * Get service status information
 */
router.get('/services', async (req, res) => {
  try {
    const services = serviceManager.getServiceStatus();
    const availableServices = serviceManager.getAvailableServices();
    
    res.json({
      services,
      availableServices,
      totalServices: Array.isArray(services) ? services.length : 1
    });
  } catch (error) {
    console.error('Failed to get service status:', error);
    res.status(500).json({ 
      error: 'Failed to get service status',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * GET /api/performance/cache
 * Get cache statistics
 */
router.get('/cache', async (req, res) => {
  try {
    const templateStats = templateCache.getStats();
    const projectStats = projectCache.getStats();
    const graphStats = graphCache.getStats();
    
    res.json({
      template: templateStats,
      project: projectStats,
      graph: graphStats,
      overall: {
        totalEntries: templateStats.memoryEntries + projectStats.memoryEntries + graphStats.memoryEntries,
        totalSize: templateStats.memorySize + projectStats.memorySize + graphStats.memorySize,
        averageHitRate: (templateStats.hitRate + projectStats.hitRate + graphStats.hitRate) / 3,
        redisAvailable: templateStats.redisAvailable
      }
    });
  } catch (error) {
    console.error('Failed to get cache statistics:', error);
    res.status(500).json({ 
      error: 'Failed to get cache statistics',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * POST /api/performance/cache/clear
 * Clear cache data
 */
router.post('/cache/clear', async (req, res) => {
  try {
    const { type } = req.body;
    
    switch (type) {
      case 'template':
        await templateCache.clear();
        break;
      case 'project':
        await projectCache.clear();
        break;
      case 'graph':
        await graphCache.clear();
        break;
      case 'all':
        await Promise.all([
          templateCache.clear(),
          projectCache.clear(),
          graphCache.clear()
        ]);
        break;
      default:
        return res.status(400).json({ 
          error: 'Invalid cache type',
          validTypes: ['template', 'project', 'graph', 'all']
        });
    }
    
    res.json({ success: true, message: `${type} cache cleared` });
  } catch (error) {
    console.error('Failed to clear cache:', error);
    res.status(500).json({ 
      error: 'Failed to clear cache',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * GET /api/performance/recommendations
 * Get optimization recommendations
 */
router.get('/recommendations', async (req, res) => {
  try {
    const recommendations = performanceMonitor.getOptimizationRecommendations();
    
    res.json({
      recommendations,
      count: recommendations.length,
      criticalCount: recommendations.filter(r => r.severity === 'critical').length,
      highCount: recommendations.filter(r => r.severity === 'high').length
    });
  } catch (error) {
    console.error('Failed to get optimization recommendations:', error);
    res.status(500).json({ 
      error: 'Failed to get optimization recommendations',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * GET /api/performance/resource-usage
 * Get current resource usage
 */
router.get('/resource-usage', async (req, res) => {
  try {
    const resourceUsage = performanceMonitor.getResourceUsage();
    
    res.json(resourceUsage);
  } catch (error) {
    console.error('Failed to get resource usage:', error);
    res.status(500).json({ 
      error: 'Failed to get resource usage',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * POST /api/performance/service/wait
 * Wait for a service to become available
 */
router.post('/service/wait', async (req, res) => {
  try {
    const { serviceName, timeout = 30000 } = req.body;
    
    if (!serviceName) {
      return res.status(400).json({ 
        error: 'Service name is required' 
      });
    }
    
    const isAvailable = await serviceManager.waitForService(serviceName, timeout);
    
    res.json({
      serviceName,
      available: isAvailable,
      timeout: timeout
    });
  } catch (error) {
    console.error('Failed to wait for service:', error);
    res.status(500).json({ 
      error: 'Failed to wait for service',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * GET /api/performance/health
 * Health check endpoint for performance monitoring
 */
router.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    version: process.version
  });
});

export default router;