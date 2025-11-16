import { Router } from 'express';
import { z } from 'zod';
import { logger } from '../utils/logger';

const router = Router();

// Validation schemas
const FrameworkSwitchSchema = z.object({
  frameworkId: z.string(),
});

const ServiceActionSchema = z.object({
  action: z.enum(['start', 'stop', 'restart']),
});

const CreateProjectSchema = z.object({
  name: z.string(),
  framework: z.string(),
  description: z.string().optional(),
});

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'stopped';
  url: string;
  port: number;
  framework?: string;
  description: string;
  lastCheck: string;
  responseTime?: number;
  version?: string;
  dependencies?: string[];
}

interface Framework {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'error';
  description: string;
  services: string[];
  composeFile: string;
  features: {
    name: string;
    status: 'working' | 'partial' | 'planned' | 'broken';
    description: string;
  }[];
}

// Mock data for frameworks
const frameworks: Framework[] = [
  {
    id: 'ferrum',
    name: 'Ferrum',
    status: 'active',
    description: 'AI-first scaffolding system with Rust/React stack',
    services: ['ferrum-cli', 'ferrum-ai', 'ferrum-postgres', 'qdrant'],
    composeFile: 'docker-compose.ferrum.yml',
    features: [
      { name: 'CLI Tools', status: 'working', description: 'Project initialization and compilation' },
      { name: 'AI Generation', status: 'working', description: 'AI-powered code scaffolding' },
      { name: 'SCG Integration', status: 'working', description: 'Visual architecture editing' },
      { name: 'PermaGraph Sync', status: 'working', description: 'Automatic architecture versioning' },
      { name: 'MCP Tools', status: 'working', description: 'IDE integration via MCP' },
    ],
  },
  {
    id: 'kthulu',
    name: 'Kthulu',
    status: 'inactive',
    description: 'Go backend with React frontend and advanced features',
    services: ['kthulu-backend', 'kthulu-frontend'],
    composeFile: 'docker-compose.kthulu.yml',
    features: [
      { name: 'Backend API', status: 'working', description: 'Go-based REST API' },
      { name: 'Frontend UI', status: 'working', description: 'React-based user interface' },
      { name: 'Authentication', status: 'working', description: 'JWT-based auth system' },
      { name: 'Database ORM', status: 'working', description: 'GORM integration' },
      { name: 'SCG Integration', status: 'partial', description: 'Basic visualization support' },
    ],
  },
  {
    id: 'tuetano',
    name: 'Tuetano',
    status: 'inactive',
    description: 'C++ framework for high-performance applications',
    services: ['tuetano-service', 'tuetano-build'],
    composeFile: 'docker-compose.tuetano.yml',
    features: [
      { name: 'C++ Compiler', status: 'planned', description: 'Modern C++ compilation' },
      { name: 'Build System', status: 'planned', description: 'CMake integration' },
      { name: 'Package Manager', status: 'planned', description: 'Dependency management' },
      { name: 'SCG Integration', status: 'planned', description: 'Architecture visualization' },
    ],
  },
];

// Current active framework
let activeFramework: string | null = 'ferrum';

/**
 * Get dashboard overview data
 */
router.get('/overview', async (req, res) => {
  try {
    const services = await getServiceStatuses();
    const frameworksWithStatus = frameworks.map(f => ({
      ...f,
      status: f.id === activeFramework ? 'active' : 'inactive'
    }));

    res.json({
      success: true,
      data: {
        frameworks: frameworksWithStatus,
        services,
        activeFramework,
        timestamp: new Date().toISOString(),
      },
    });
  } catch (error) {
    logger.error('Error getting dashboard overview:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get dashboard overview',
    });
  }
});

/**
 * Get service statuses
 */
router.get('/services', async (req, res) => {
  try {
    const services = await getServiceStatuses();
    
    res.json({
      success: true,
      data: services,
    });
  } catch (error) {
    logger.error('Error getting service statuses:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get service statuses',
    });
  }
});

/**
 * Get frameworks information
 */
router.get('/frameworks', async (req, res) => {
  try {
    const frameworksWithStatus = frameworks.map(f => ({
      ...f,
      status: f.id === activeFramework ? 'active' : 'inactive'
    }));

    res.json({
      success: true,
      data: frameworksWithStatus,
    });
  } catch (error) {
    logger.error('Error getting frameworks:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get frameworks',
    });
  }
});

/**
 * Switch active framework
 */
router.post('/frameworks/switch', async (req, res) => {
  try {
    const { frameworkId } = FrameworkSwitchSchema.parse(req.body);
    
    const framework = frameworks.find(f => f.id === frameworkId);
    if (!framework) {
      return res.status(404).json({
        success: false,
        error: 'Framework not found',
      });
    }

    activeFramework = frameworkId;
    
    logger.info(`Switched to framework: ${frameworkId}`);
    
    res.json({
      success: true,
      data: {
        activeFramework: frameworkId,
        framework,
      },
    });
  } catch (error) {
    logger.error('Error switching framework:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to switch framework',
    });
  }
});

/**
 * Perform service action (start/stop/restart)
 */
router.post('/services/:serviceName/action', async (req, res) => {
  try {
    const { serviceName } = req.params;
    const { action } = ServiceActionSchema.parse(req.body);
    
    // Simulate service action
    logger.info(`Performing ${action} on service: ${serviceName}`);
    
    // In a real implementation, this would interact with Docker or process management
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    res.json({
      success: true,
      data: {
        serviceName,
        action,
        status: action === 'stop' ? 'stopped' : 'healthy',
        timestamp: new Date().toISOString(),
      },
    });
  } catch (error) {
    logger.error('Error performing service action:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to perform service action',
    });
  }
});

/**
 * Check service health
 */
router.get('/services/:serviceName/health', async (req, res) => {
  try {
    const { serviceName } = req.params;
    
    // Simulate health check
    const isHealthy = Math.random() > 0.1; // 90% chance of being healthy
    const responseTime = Math.floor(Math.random() * 200) + 10;
    
    res.json({
      success: true,
      data: {
        serviceName,
        status: isHealthy ? 'healthy' : 'degraded',
        responseTime,
        timestamp: new Date().toISOString(),
      },
    });
  } catch (error) {
    logger.error('Error checking service health:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to check service health',
    });
  }
});

/**
 * Get framework-specific projects
 */
router.get('/projects', async (req, res) => {
  try {
    const { framework } = req.query;
    
    // Mock project data
    const allProjects = [
      {
        id: 'ferrum-1',
        name: 'E-commerce API',
        framework: 'ferrum',
        status: 'active',
        lastModified: new Date(Date.now() - 86400000).toISOString(),
        description: 'REST API for e-commerce platform',
        path: '/projects/ferrum/ecommerce-api',
        nodeCount: 15,
        edgeCount: 23,
      },
      {
        id: 'kthulu-1',
        name: 'User Management',
        framework: 'kthulu',
        status: 'active',
        lastModified: new Date(Date.now() - 172800000).toISOString(),
        description: 'User authentication and management system',
        path: '/projects/kthulu/user-management',
        nodeCount: 8,
        edgeCount: 12,
      },
      {
        id: 'ferrum-2',
        name: 'Blog Platform',
        framework: 'ferrum',
        status: 'inactive',
        lastModified: new Date(Date.now() - 604800000).toISOString(),
        description: 'Content management system for blogs',
        path: '/projects/ferrum/blog-platform',
        nodeCount: 12,
        edgeCount: 18,
      },
    ];
    
    const filteredProjects = framework 
      ? allProjects.filter(p => p.framework === framework)
      : allProjects;
    
    res.json({
      success: true,
      data: filteredProjects,
    });
  } catch (error) {
    logger.error('Error getting projects:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get projects',
    });
  }
});

/**
 * Create new project
 */
router.post('/projects', async (req, res) => {
  try {
    const { name, framework, description } = CreateProjectSchema.parse(req.body);
    
    const newProject = {
      id: `${framework}-${Date.now()}`,
      name,
      framework,
      status: 'active',
      lastModified: new Date().toISOString(),
      description: description || `New ${framework} project`,
      path: `/projects/${framework}/${name.toLowerCase().replace(/\s+/g, '-')}`,
      nodeCount: 0,
      edgeCount: 0,
    };
    
    logger.info(`Created new project: ${name} (${framework})`);
    
    res.json({
      success: true,
      data: newProject,
    });
  } catch (error) {
    logger.error('Error creating project:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to create project',
    });
  }
});

// Helper function to get service statuses
async function getServiceStatuses(): Promise<ServiceStatus[]> {
  const baseServices: ServiceStatus[] = [
    {
      name: 'SCG UI',
      status: 'healthy',
      url: 'http://localhost:3000',
      port: 3000,
      description: 'Semantic Code Graph User Interface',
      lastCheck: new Date().toISOString(),
      responseTime: 45,
      version: '1.0.0',
    },
    {
      name: 'PermaGraph',
      status: 'healthy',
      url: 'http://localhost:8080',
      port: 8080,
      description: 'Semantic graph storage and reasoning engine',
      lastCheck: new Date().toISOString(),
      responseTime: 120,
      version: '2.1.0',
    },
    {
      name: 'Neo4j',
      status: 'healthy',
      url: 'http://localhost:7474',
      port: 7687,
      description: 'Graph database for architectural storage',
      lastCheck: new Date().toISOString(),
      responseTime: 25,
    },
    {
      name: 'Redis',
      status: 'healthy',
      url: 'redis://localhost:6379',
      port: 6379,
      description: 'Cache and message broker',
      lastCheck: new Date().toISOString(),
      responseTime: 5,
    },
    {
      name: 'MCP Server',
      status: 'healthy',
      url: 'http://localhost:8001',
      port: 8001,
      description: 'Model Context Protocol server for IDE integration',
      lastCheck: new Date().toISOString(),
      responseTime: 35,
    },
  ];

  const frameworkServices: ServiceStatus[] = [
    {
      name: 'Ferrum CLI',
      status: activeFramework === 'ferrum' ? 'healthy' : 'stopped',
      url: 'http://localhost:8002',
      port: 8002,
      framework: 'ferrum',
      description: 'Ferrum command-line interface and API',
      lastCheck: new Date().toISOString(),
      responseTime: 80,
    },
    {
      name: 'Ferrum AI',
      status: activeFramework === 'ferrum' ? 'healthy' : 'stopped',
      url: 'http://localhost:8001',
      port: 8001,
      framework: 'ferrum',
      description: 'AI-powered code generation service',
      lastCheck: new Date().toISOString(),
      responseTime: 200,
    },
    {
      name: 'Kthulu Backend',
      status: activeFramework === 'kthulu' ? 'healthy' : 'stopped',
      url: 'http://localhost:8080',
      port: 8080,
      framework: 'kthulu',
      description: 'Kthulu Go backend service',
      lastCheck: new Date().toISOString(),
      responseTime: 60,
    },
    {
      name: 'Tuetano Service',
      status: activeFramework === 'tuetano' ? 'healthy' : 'stopped',
      url: 'http://localhost:8003',
      port: 8003,
      framework: 'tuetano',
      description: 'Tuetano C++ development service',
      lastCheck: new Date().toISOString(),
      responseTime: 150,
    },
  ];

  return [...baseServices, ...frameworkServices];
}

export default router;