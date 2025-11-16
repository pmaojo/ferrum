import fs from 'node:fs';
import path from 'node:path';

import type { Router, Request, Response } from 'express';

import { GoASTParser } from '../services/go-ast-parser';
import { PermaGraphController } from '../services/permagraph-controller';
import { SemanticTripleGenerator } from '../services/semantic-triple-generator';
import type { IStorage } from '../storage';
import { ValidationEngine } from '../validation-engine';

export function attachPermaGraphRoutes(app: Router, storageImpl: IStorage) {
  // Map to store active PermaGraph controllers per project
  const controllers = new Map<string, PermaGraphController>();
  (app as any).set?.('permagraphControllers', controllers);

  const permagraphBaseUrl =
    process.env.PERMAGRAPH_API_URL || 'http://localhost:8000';

  const cleanupController = async (projectId: string) => {
    const controller = controllers.get(projectId);
    if (controller) {
      await controller.shutdown();
      controllers.delete(projectId);
    }
    const wsManager = (app as any).get?.('wsManager');
    wsManager?.unsubscribeProject(projectId);
  };

  const cleanupAllControllers = async () => {
    for (const projectId of Array.from(controllers.keys())) {
      await cleanupController(projectId);
    }
    const wsManager = (app as any).get?.('wsManager');
    wsManager?.unsubscribeAll();
  };

  process.on('SIGINT', cleanupAllControllers);
  process.on('SIGTERM', cleanupAllControllers);

  /**
   * Initialize PermaGraph controller for a project
   */
  app.post(
    '/projects/:projectId/permagraph/init',
    async (req: Request, res: Response) => {
      try {
        const { projectId } = req.params;
        const { kthuluPath } = req.body as { kthuluPath?: string };

        // Create new controller
        const controller = new PermaGraphController(projectId);
        controllers.set(projectId, controller);

        // Set up event listeners for WebSocket broadcasting
        // WebSocket events are now proxied directly from PermaGraph

        // Automatically load ontology if path provided
        if (kthuluPath) {
          (async () => {
            try {
              await fs.promises.access(kthuluPath, fs.constants.R_OK);
              const goParser = new GoASTParser(kthuluPath);
              const elements = await goParser.analyzeKthuluProject(kthuluPath);
              const tripleGenerator = new SemanticTripleGenerator();
              tripleGenerator.on('update', update =>
                controller.updateOntology(update)
              );
              const triples =
                tripleGenerator.generateTriplesFromElements(elements);
              await controller.loadOntology(triples);
            } catch (err) {
              console.error('Automatic ontology loading failed:', err);
            }
          })();
        }

        res.json({
          message: 'PermaGraph controller initialized successfully',
          projectId,
          agentCount: controller.getAgents().length,
        });
      } catch (error) {
        console.error('Failed to initialize PermaGraph controller:', error);
        res
          .status(500)
          .json({ error: 'Failed to initialize PermaGraph controller' });
      }
    }
  );

  /**
   * Load ontology from Kthulu project
   */
  app.post(
    '/projects/:projectId/permagraph/load-ontology',
    async (req: Request, res: Response) => {
      try {
        const { projectId } = req.params;
        const { kthuluPath } = req.body;

        const controller = controllers.get(projectId);
        if (!controller) {
          return res
            .status(404)
            .json({ error: 'PermaGraph controller not initialized' });
        }

        if (!kthuluPath) {
          return res
            .status(400)
            .json({ error: 'Kthulu project path is required' });
        }

        try {
          await fs.promises.access(kthuluPath, fs.constants.R_OK);
        } catch {
          return res.status(400).json({
            error: `Kthulu project path ${kthuluPath} does not exist or is inaccessible`,
          });
        }

        // Analyze Kthulu project and generate triples
        const goParser = new GoASTParser(kthuluPath);
        const elements = await goParser.analyzeKthuluProject(kthuluPath);

        const tripleGenerator = new SemanticTripleGenerator();
        const triples = tripleGenerator.generateTriplesFromElements(elements);

        // Load into PermaGraph
        await controller.loadOntology(triples);

        res.json({
          message: 'Ontology loaded successfully',
          tripleCount: triples.length,
          elementCount: elements.length,
        });
      } catch (error) {
        console.error('Failed to load ontology:', error);
        res.status(500).json({
          error: `Failed to load ontology: ${(error as Error).message}`,
        });
      }
    }
  );

  /**
   * Get all agents
   */
  app.get('/agents', async (_req: Request, res: Response) => {
    try {
      const response = await fetch(`${permagraphBaseUrl}/api/v1/agents`);
      if (!response.ok) {
        return res
          .status(response.status)
          .json({ error: 'Failed to get agents' });
      }
      const data = await response.json();
      res.json(data);
    } catch (error) {
      console.error('Failed to get agents:', error);
      res.status(500).json({ error: 'Failed to get agents' });
    }
  });

  /**
   * Start an agent
   */
  app.post('/agents/:agentId/start', async (req: Request, res: Response) => {
    try {
      const { agentId } = req.params;
      const response = await fetch(
        `${permagraphBaseUrl}/api/v1/agents/${agentId}/start`,
        { method: 'POST' }
      );
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        return res
          .status(response.status)
          .json({ error: data.error || 'Failed to start agent' });
      }
      res.json(data);
    } catch (error) {
      console.error('Failed to start agent:', error);
      res.status(500).json({
        error: `Failed to start agent: ${(error as Error).message}`,
      });
    }
  });

  /**
   * Stop an agent
   */
  app.post('/agents/:agentId/stop', async (req: Request, res: Response) => {
    try {
      const { agentId } = req.params;
      const response = await fetch(
        `${permagraphBaseUrl}/api/v1/agents/${agentId}/stop`,
        { method: 'POST' }
      );
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        return res
          .status(response.status)
          .json({ error: data.error || 'Failed to stop agent' });
      }
      res.json(data);
    } catch (error) {
      console.error('Failed to stop agent:', error);
      res
        .status(500)
        .json({ error: `Failed to stop agent: ${(error as Error).message}` });
    }
  });

  /**
   * Configure an agent
   */
  app.put(
    '/projects/:projectId/permagraph/agents/:agentId/config',
    async (req: Request, res: Response) => {
      try {
        const { projectId, agentId } = req.params;
        const { config } = req.body;

        const controller = controllers.get(projectId);
        if (!controller) {
          return res
            .status(404)
            .json({ error: 'PermaGraph controller not initialized' });
        }

        await controller.configureAgent(agentId, config);
        const agent = controller.getAgent(agentId);

        res.json({
          message: `Agent ${agentId} configured successfully`,
          agent,
        });
      } catch (error) {
        console.error('Failed to configure agent:', error);
        res.status(500).json({
          error: `Failed to configure agent: ${(error as Error).message}`,
        });
      }
    }
  );

  /**
   * Get explanation for a rule violation from an agent
   */
  app.post(
    '/api/v1/projects/:projectId/agents/:agentId/explain',
    async (req: Request, res: Response) => {
      try {
        const { projectId, agentId } = req.params;
        const { violation } = req.body;

        const controller = controllers.get(projectId);
        if (!controller) {
          return res
            .status(404)
            .json({ error: 'PermaGraph controller not initialized' });
        }

        if (!violation) {
          return res.status(400).json({ error: 'Violation is required' });
        }

        const explanation = await controller.explainViolation(
          agentId,
          violation
        );
        res.json({ explanation });
      } catch (error) {
        console.error('Failed to get explanation:', error);
        res.status(500).json({
          error: `Failed to get explanation: ${(error as Error).message}`,
        });
      }
    }
  );

  /**
   * Validate ontology
   */
  app.post(
    '/projects/:projectId/permagraph/validate',
    async (req: Request, res: Response) => {
      try {
        const { projectId } = req.params;

        const controller = controllers.get(projectId);
        if (!controller) {
          return res
            .status(404)
            .json({ error: 'PermaGraph controller not initialized' });
        }
        // Run game validation
        try {
          const project = await storageImpl.getProject(projectId);
          const template = project
            ? await storageImpl.getTemplate(project.templateId)
            : null;
          if (project && template) {
            const [nodes, edges] = await Promise.all([
              storageImpl.getNodesByProject(projectId),
              storageImpl.getEdgesByProject(projectId),
            ]);

            const validationEngine = new ValidationEngine(template);
            validationEngine.validateArchitecture(nodes, edges, projectId);
          }
        } catch (err) {
          console.error('Validation engine error:', err);
        }

        const report = await controller.validateOntology();

        res.json({
          validation: report,
          timestamp: new Date().toISOString(),
        });
      } catch (error) {
        console.error('Failed to validate ontology:', error);
        res
          .status(500)
          .json({ error: `Failed to validate: ${(error as Error).message}` });
      }
    }
  );

  /**
   * Execute SPARQL query
   */
  app.post(
    '/projects/:projectId/permagraph/sparql',
    async (req: Request, res: Response) => {
      try {
        const { projectId } = req.params;
        const { query, parameters } = req.body;

        const controller = controllers.get(projectId);
        if (!controller) {
          return res
            .status(404)
            .json({ error: 'PermaGraph controller not initialized' });
        }

        if (!query) {
          return res.status(400).json({ error: 'SPARQL query is required' });
        }

        const results = await controller.executeSPARQL(query, parameters);

        res.json({
          query,
          results,
          timestamp: new Date().toISOString(),
        });
      } catch (error) {
        console.error('Failed to execute SPARQL query:', error);
        res.status(500).json({
          error: `Failed to execute query: ${(error as Error).message}`,
        });
      }
    }
  );

  /**
   * Get predefined queries
   */
  app.get(
    '/projects/:projectId/permagraph/queries',
    async (req: Request, res: Response) => {
      try {
        const { projectId } = req.params;

        const controller = controllers.get(projectId);
        if (!controller) {
          return res
            .status(404)
            .json({ error: 'PermaGraph controller not initialized' });
        }

        const queries = await controller.listQueries();

        res.json(queries);
      } catch (error) {
        console.error('Failed to get queries:', error);
        res.status(500).json({ error: 'Failed to get queries' });
      }
    }
  );

  /**
   * Execute predefined query
   */
  app.post(
    '/projects/:projectId/permagraph/queries/:queryId/execute',
    async (req: Request, res: Response) => {
      try {
        const { projectId, queryId } = req.params;
        const { parameters } = req.body;

        const controller = controllers.get(projectId);
        if (!controller) {
          return res
            .status(404)
            .json({ error: 'PermaGraph controller not initialized' });
        }

        const results = await controller.executeQueryById(queryId, parameters);

        res.json({
          results,
          timestamp: new Date().toISOString(),
        });
      } catch (error) {
        console.error('Failed to execute predefined query:', error);
        res.status(500).json({
          error: `Failed to execute query: ${(error as Error).message}`,
        });
      }
    }
  );

  /**
   * Add custom query
   */
  app.post(
    '/projects/:projectId/permagraph/queries',
    async (req: Request, res: Response) => {
      try {
        const { projectId } = req.params;
        const { query } = req.body;

        const controller = controllers.get(projectId);
        if (!controller) {
          return res
            .status(404)
            .json({ error: 'PermaGraph controller not initialized' });
        }

        if (!query?.id || !query.name || !query.query) {
          return res
            .status(400)
            .json({ error: 'Query must have id, name, and query fields' });
        }

        controller.addQuery(query);

        res.json({
          message: 'Query added successfully',
          query,
        });
      } catch (error) {
        console.error('Failed to add query:', error);
        res
          .status(500)
          .json({ error: `Failed to add query: ${(error as Error).message}` });
      }
    }
  );

  /**
   * List SPARQL query presets from documentation directory
   */
  app.get(
    '/api/v1/projects/:projectId/sparql/presets',
    async (_req: Request, res: Response) => {
      try {
        const presetsDir = path.join(
          __dirname,
          '..',
          '..',
          '..',
          'docs',
          'sparql-presets'
        );
        const files = await fs.promises.readdir(presetsDir);
        const queries: Array<{ id: string; query: string }> = [];

        for (const file of files) {
          if (file.endsWith('.rq')) {
            const query = await fs.promises.readFile(
              path.join(presetsDir, file),
              'utf-8'
            );
            queries.push({ id: path.basename(file, '.rq'), query });
          }
        }

        res.json({ queries });
      } catch (error) {
        console.error('Failed to list SPARQL presets:', error);
        res.status(500).json({ error: 'Failed to list SPARQL presets' });
      }
    }
  );

  /**
   * List semantic query presets
   */
  app.get(
    '/api/v1/projects/:projectId/semantic/queries',
    async (_req: Request, res: Response) => {
      try {
        const presetsDir = path.join(__dirname, '..', 'semantic', 'presets');
        const files = await fs.promises.readdir(presetsDir);
        const queries: Array<{ id: string; sparql: string }> = [];

        for (const file of files) {
          if (file.endsWith('.rq')) {
            const sparql = await fs.promises.readFile(
              path.join(presetsDir, file),
              'utf-8'
            );
            queries.push({ id: path.basename(file, '.rq'), sparql });
          }
        }

        res.json({ queries });
      } catch (error) {
        console.error('Failed to list semantic query presets:', error);
        res
          .status(500)
          .json({ error: 'Failed to list semantic query presets' });
      }
    }
  );

  /**
   * Execute semantic query preset
   */
  app.post(
    '/api/v1/projects/:projectId/semantic/queries/:queryId',
    async (req: Request, res: Response) => {
      try {
        const { projectId, queryId } = req.params;
        const controllers = app.get('permagraphControllers') as
          | Map<string, PermaGraphController>
          | undefined;
        const controller = controllers?.get(projectId);
        if (!controller) {
          return res
            .status(404)
            .json({ error: 'PermaGraph controller not initialized' });
        }

        const presetsDir = path.join(__dirname, '..', 'semantic', 'presets');
        const filePath = path.join(presetsDir, `${queryId}.rq`);
        try {
          await fs.promises.access(filePath, fs.constants.R_OK);
        } catch {
          return res.status(404).json({ error: 'Query not found' });
        }

        const sparql = await fs.promises.readFile(filePath, 'utf-8');
        const { parameters } = req.body || {};
        const results = await controller.executeSPARQL(sparql, parameters);

        res.json({ rows: results.results.bindings, graph: [] });
      } catch (error) {
        console.error('Failed to execute semantic query:', error);
        res.status(500).json({ error: 'Failed to execute semantic query' });
      }
    }
  );

  /**
   * Get performance metrics
   */
  app.get(
    '/projects/:projectId/permagraph/metrics',
    async (req: Request, res: Response) => {
      try {
        const { projectId } = req.params;

        const controller = controllers.get(projectId);
        if (!controller) {
          return res
            .status(404)
            .json({ error: 'PermaGraph controller not initialized' });
        }

        const metrics = await controller.getPerformanceMetrics();

        res.json({
          metrics,
          timestamp: new Date().toISOString(),
        });
      } catch (error) {
        console.error('Failed to get performance metrics:', error);
        res.status(500).json({ error: 'Failed to get metrics' });
      }
    }
  );

  /**
   * Update ontology
   */
  app.post(
    '/projects/:projectId/permagraph/ontology/update',
    async (req: Request, res: Response) => {
      try {
        const { projectId } = req.params;
        const { type, triples, source } = req.body;

        const controller = controllers.get(projectId);
        if (!controller) {
          return res
            .status(404)
            .json({ error: 'PermaGraph controller not initialized' });
        }

        if (!type || !triples || !Array.isArray(triples)) {
          return res
            .status(400)
            .json({ error: 'Update must have type and triples array' });
        }

        await controller.updateOntology({
          type,
          triples,
          source: source || 'manual',
          timestamp: new Date(),
        });

        res.json({
          message: 'Ontology updated successfully',
          type,
          tripleCount: triples.length,
        });
      } catch (error) {
        console.error('Failed to update ontology:', error);
        res.status(500).json({
          error: `Failed to update ontology: ${(error as Error).message}`,
        });
      }
    }
  );

  /**
   * Get PermaGraph status
   */
  app.get(
    '/projects/:projectId/permagraph/status',
    async (req: Request, res: Response) => {
      try {
        const { projectId } = req.params;

        const controller = controllers.get(projectId);
        const isInitialized = !!controller;

        if (!isInitialized) {
          return res.json({
            projectId,
            isInitialized: false,
            timestamp: new Date().toISOString(),
          });
        }

        const agents = controller.getAgents();
        const metrics = await controller.getPerformanceMetrics();

        res.json({
          projectId,
          isInitialized: true,
          agents: agents.map(a => ({
            id: a.id,
            name: a.name,
            type: a.type,
            status: a.status,
          })),
          metrics,
          timestamp: new Date().toISOString(),
        });
      } catch (error) {
        console.error('Failed to get PermaGraph status:', error);
        res.status(500).json({ error: 'Failed to get status' });
      }
    }
  );

  /**
   * Get Ferrum sync status
   */
  app.get('/api/ferrum/sync-status', async (req: Request, res: Response) => {
    try {
      const { path: projectPath } = req.query;
      const resolvedPath = projectPath ? String(projectPath) : '.';
      
      // Look for the sync status file in the project directory
      const statusFilePath = path.join(resolvedPath, '.ferrum_sync_status.json');
      
      try {
        await fs.promises.access(statusFilePath, fs.constants.R_OK);
        const statusContent = await fs.promises.readFile(statusFilePath, 'utf-8');
        const syncStatus = JSON.parse(statusContent);
        
        res.json(syncStatus);
      } catch (error) {
        // If file doesn't exist, return default status
        res.json({
          status: 'not_started',
          timestamp: new Date().toISOString(),
        });
      }
    } catch (error) {
      console.error('Failed to get Ferrum sync status:', error);
      res.status(500).json({ 
        error: 'Failed to get sync status',
        status: 'not_started',
        timestamp: new Date().toISOString(),
      });
    }
  });

  /**
   * Trigger manual Ferrum sync
   */
  app.post('/api/ferrum/sync', async (req: Request, res: Response) => {
    try {
      const { projectPath, commitMessage } = req.body;
      const resolvedPath = projectPath || '.';
      
      // This would typically trigger a Ferrum compile with sync
      // For now, we'll simulate the sync process
      const syncStatus = {
        status: 'in_progress',
        timestamp: new Date().toISOString(),
      };
      
      // Write initial status
      const statusFilePath = path.join(resolvedPath, '.ferrum_sync_status.json');
      await fs.promises.writeFile(statusFilePath, JSON.stringify(syncStatus, null, 2));
      
      // Simulate async sync process
      setTimeout(async () => {
        try {
          const successStatus = {
            status: 'success',
            version_id: `v${Date.now()}`,
            timestamp: new Date().toISOString(),
            commit_message: commitMessage,
          };
          await fs.promises.writeFile(statusFilePath, JSON.stringify(successStatus, null, 2));
        } catch (error) {
          const failedStatus = {
            status: 'failed',
            error: 'Simulated sync failure',
            timestamp: new Date().toISOString(),
          };
          await fs.promises.writeFile(statusFilePath, JSON.stringify(failedStatus, null, 2));
        }
      }, 2000);
      
      res.json({
        message: 'Sync initiated',
        status: syncStatus,
      });
    } catch (error) {
      console.error('Failed to trigger Ferrum sync:', error);
      res.status(500).json({ error: 'Failed to trigger sync' });
    }
  });

  /**
   * GraphRAG: Find similar architectural patterns
   */
  app.post('/api/v1/graphrag/patterns/similar', async (req: Request, res: Response) => {
    try {
      const { features, similarity_threshold = 0.7, limit = 10 } = req.body;
      
      // Simulate pattern matching based on features
      // In a real implementation, this would use vector similarity search
      const mockPatterns = [
        {
          id: 'hexagonal-arch-1',
          name: 'Hexagonal Architecture with Repository Pattern',
          description: 'Clean architecture with ports and adapters, using repository pattern for data access',
          usage_count: 45,
          similarity_score: 0.85,
        },
        {
          id: 'cqrs-pattern-1',
          name: 'CQRS with Event Sourcing',
          description: 'Command Query Responsibility Segregation with event sourcing for audit trail',
          usage_count: 23,
          similarity_score: 0.72,
        },
        {
          id: 'microservice-1',
          name: 'Microservice with API Gateway',
          description: 'Microservice architecture with centralized API gateway and service discovery',
          usage_count: 67,
          similarity_score: 0.68,
        },
      ].filter(p => p.similarity_score >= similarity_threshold)
       .slice(0, limit);

      res.json({ patterns: mockPatterns });
    } catch (error) {
      console.error('Failed to find similar patterns:', error);
      res.status(500).json({ error: 'Failed to find similar patterns' });
    }
  });

  /**
   * GraphRAG: Get best practices for node types
   */
  app.get('/api/v1/graphrag/best-practices', async (req: Request, res: Response) => {
    try {
      const { node_type, framework } = req.query;
      
      // Mock best practices based on node type
      const mockPractices = {
        usecase: [
          {
            id: 'usecase-single-responsibility',
            title: 'Single Responsibility Principle',
            description: 'Each use case should handle only one business operation',
            applies_to: ['usecase'],
            examples: ['UserRegistration', 'OrderProcessing', 'PaymentValidation'],
          },
          {
            id: 'usecase-error-handling',
            title: 'Comprehensive Error Handling',
            description: 'Use cases should handle all possible error scenarios gracefully',
            applies_to: ['usecase'],
            examples: ['ValidationError', 'BusinessRuleViolation', 'ExternalServiceFailure'],
          },
        ],
        adapter: [
          {
            id: 'adapter-interface-segregation',
            title: 'Interface Segregation',
            description: 'Adapters should implement focused, specific interfaces',
            applies_to: ['adapter'],
            examples: ['DatabaseAdapter', 'EmailAdapter', 'PaymentAdapter'],
          },
        ],
        entity: [
          {
            id: 'entity-immutability',
            title: 'Prefer Immutable Entities',
            description: 'Design entities to be immutable when possible for thread safety',
            applies_to: ['entity'],
            examples: ['ValueObjects', 'ImmutableRecords'],
          },
        ],
      };

      const practices = mockPractices[node_type as string] || [];
      res.json({ best_practices: practices });
    } catch (error) {
      console.error('Failed to get best practices:', error);
      res.status(500).json({ error: 'Failed to get best practices' });
    }
  });

  /**
   * GraphRAG: Get common implementations
   */
  app.get('/api/v1/graphrag/implementations', async (req: Request, res: Response) => {
    try {
      const { node_type, framework, language } = req.query;
      
      // Mock implementations based on parameters
      const mockImplementations = [
        {
          pattern_id: 'repository-pattern',
          language: 'rust',
          framework: 'ferrum',
          code_snippet: `
pub trait UserRepository {
    async fn save(&self, user: User) -> Result<User, Error>;
    async fn find_by_id(&self, id: UserId) -> Result<Option<User>, Error>;
}

pub struct PostgresUserRepository {
    pool: PgPool,
}

impl UserRepository for PostgresUserRepository {
    async fn save(&self, user: User) -> Result<User, Error> {
        // Implementation here
        Ok(user)
    }
}`,
          usage_frequency: 89,
        },
      ];

      res.json({ implementations: mockImplementations });
    } catch (error) {
      console.error('Failed to get implementations:', error);
      res.status(500).json({ error: 'Failed to get implementations' });
    }
  });

  /**
   * GraphRAG: Get anti-patterns to avoid
   */
  app.get('/api/v1/graphrag/anti-patterns', async (req: Request, res: Response) => {
    try {
      const { node_type, framework } = req.query;
      
      // Mock anti-patterns
      const mockAntiPatterns = [
        {
          id: 'god-object',
          name: 'God Object',
          description: 'A single class or module that knows too much or does too much',
          why_avoid: 'Violates single responsibility principle, hard to test and maintain',
          alternatives: ['Split into focused components', 'Use composition over inheritance'],
        },
        {
          id: 'circular-dependencies',
          name: 'Circular Dependencies',
          description: 'Modules that depend on each other creating cycles',
          why_avoid: 'Makes code hard to understand, test, and can cause runtime issues',
          alternatives: ['Dependency injection', 'Event-driven architecture', 'Interface segregation'],
        },
      ];

      res.json({ anti_patterns: mockAntiPatterns });
    } catch (error) {
      console.error('Failed to get anti-patterns:', error);
      res.status(500).json({ error: 'Failed to get anti-patterns' });
    }
  });

  /**
   * GraphRAG: Store successful patterns
   */
  app.post('/api/v1/graphrag/patterns', async (req: Request, res: Response) => {
    try {
      const { project_name, modules, success_metrics, framework } = req.body;
      
      // In a real implementation, this would store the pattern in the knowledge graph
      console.log('Storing successful pattern:', {
        project_name,
        modules: modules?.length || 0,
        success_metrics,
        framework,
      });

      res.json({
        message: 'Pattern stored successfully',
        pattern_id: `pattern_${Date.now()}`,
      });
    } catch (error) {
      console.error('Failed to store pattern:', error);
      res.status(500).json({ error: 'Failed to store pattern' });
    }
  });

  /**
   * Remove PermaGraph controller for a project
   */
  app.delete(
    '/projects/:projectId/permagraph',
    async (req: Request, res: Response) => {
      try {
        const { projectId } = req.params;
        const controller = controllers.get(projectId);
        if (!controller) {
          return res
            .status(404)
            .json({ error: 'PermaGraph controller not initialized' });
        }

        await cleanupController(projectId);

        res.json({
          message: 'PermaGraph controller removed successfully',
          projectId,
        });
      } catch (error) {
        console.error('Failed to remove PermaGraph controller:', error);
        res.status(500).json({ error: 'Failed to remove controller' });
      }
    }
  );
}
