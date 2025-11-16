import { Router } from 'express';
import { z } from 'zod';

import { PermaGraphController } from '../services/permagraph-controller';

const router = Router();
const permaGraphController = new PermaGraphController();

// Validation schemas
const SemanticNavigationSchema = z.object({
  query: z.string().min(1),
  tenant_id: z.string(),
  context_id: z.string().optional().default('default'),
  include_patterns: z.boolean().optional().default(true),
  include_impact: z.boolean().optional().default(false),
  include_cross_framework: z.boolean().optional().default(false),
  max_results: z.number().optional().default(20),
});

const ComponentExplorationSchema = z.object({
  component_iri: z.string(),
  tenant_id: z.string(),
  depth: z.number().optional().default(2),
  include_patterns: z.boolean().optional().default(true),
});

const HotspotsAnalysisSchema = z.object({
  tenant_id: z.string(),
  hotspot_type: z
    .enum(['complexity', 'coupling', 'patterns', 'all'])
    .optional()
    .default('all'),
});

const NavigationRecommendationsSchema = z.object({
  current_component_iri: z.string(),
  tenant_id: z.string(),
  context_id: z.string().optional().default('default'),
});

// Semantic navigation endpoint
router.post('/navigate', async (req, res) => {
  try {
    const validatedData = SemanticNavigationSchema.parse(req.body);

    const result = await permaGraphController.executeSemanticNavigation({
      query: validatedData.query,
      tenant_id: validatedData.tenant_id,
      context_id: validatedData.context_id,
      include_patterns: validatedData.include_patterns,
      include_impact: validatedData.include_impact,
      include_cross_framework: validatedData.include_cross_framework,
      max_results: validatedData.max_results,
    });

    res.json(result);
  } catch (error) {
    console.error('Semantic navigation error:', error);
    if (error instanceof z.ZodError) {
      res
        .status(400)
        .json({ error: 'Invalid request data', details: error.errors });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

// Component neighborhood exploration
router.post('/explore-component', async (req, res) => {
  try {
    const validatedData = ComponentExplorationSchema.parse(req.body);

    const result = await permaGraphController.exploreComponentNeighborhood({
      component_iri: validatedData.component_iri,
      tenant_id: validatedData.tenant_id,
      depth: validatedData.depth,
      include_patterns: validatedData.include_patterns,
    });

    res.json(result);
  } catch (error) {
    console.error('Component exploration error:', error);
    if (error instanceof z.ZodError) {
      res
        .status(400)
        .json({ error: 'Invalid request data', details: error.errors });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

// Architectural hotspots analysis
router.post('/hotspots', async (req, res) => {
  try {
    const validatedData = HotspotsAnalysisSchema.parse(req.body);

    const result = await permaGraphController.findArchitecturalHotspots({
      tenant_id: validatedData.tenant_id,
      hotspot_type: validatedData.hotspot_type,
    });

    res.json(result);
  } catch (error) {
    console.error('Hotspots analysis error:', error);
    if (error instanceof z.ZodError) {
      res
        .status(400)
        .json({ error: 'Invalid request data', details: error.errors });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

// Navigation recommendations
router.post('/recommendations', async (req, res) => {
  try {
    const validatedData = NavigationRecommendationsSchema.parse(req.body);

    const result = await permaGraphController.getNavigationRecommendations({
      current_component_iri: validatedData.current_component_iri,
      tenant_id: validatedData.tenant_id,
      context_id: validatedData.context_id,
    });

    res.json(result);
  } catch (error) {
    console.error('Navigation recommendations error:', error);
    if (error instanceof z.ZodError) {
      res
        .status(400)
        .json({ error: 'Invalid request data', details: error.errors });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

// Semantic search endpoint
router.post('/search', async (req, res) => {
  try {
    const { query, tenant_id, scope = 'all', max_results = 50 } = req.body;

    if (!query || !tenant_id) {
      return res
        .status(400)
        .json({ error: 'Query and tenant_id are required' });
    }

    const result = await permaGraphController.executeSemanticSearch({
      query_text: query,
      tenant_id,
      scope,
      max_results,
    });

    res.json(result);
  } catch (error) {
    console.error('Semantic search error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Dependency path analysis
router.post('/dependency-paths', async (req, res) => {
  try {
    const {
      source_iri,
      target_iri,
      tenant_id,
      path_type = 'shortest',
      max_paths = 10,
    } = req.body;

    if (!source_iri || !target_iri || !tenant_id) {
      return res.status(400).json({
        error: 'source_iri, target_iri, and tenant_id are required',
      });
    }

    const result = await permaGraphController.findDependencyPaths({
      source_iri,
      target_iri,
      tenant_id,
      path_type,
      max_paths,
    });

    res.json(result);
  } catch (error) {
    console.error('Dependency paths error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Impact analysis for proposed changes
router.post('/impact-analysis', async (req, res) => {
  try {
    const { change, tenant_id } = req.body;

    if (!change || !tenant_id) {
      return res
        .status(400)
        .json({ error: 'change and tenant_id are required' });
    }

    const result = await permaGraphController.analyzeChangeImpact({
      change,
      tenant_id,
    });

    res.json(result);
  } catch (error) {
    console.error('Impact analysis error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Architectural pattern detection
router.post('/patterns', async (req, res) => {
  try {
    const { tenant_id, pattern_type } = req.body;

    if (!tenant_id) {
      return res.status(400).json({ error: 'tenant_id is required' });
    }

    const result = pattern_type
      ? await permaGraphController.detectSpecificPattern({
          pattern_type,
          tenant_id,
        })
      : await permaGraphController.analyzeArchitecturalPatterns({ tenant_id });

    res.json(result);
  } catch (error) {
    console.error('Pattern detection error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Component dependencies
router.get('/component/:iri/dependencies', async (req, res) => {
  try {
    const { iri } = req.params;
    const { tenant_id, direction = 'both' } = req.query;

    if (!tenant_id) {
      return res.status(400).json({ error: 'tenant_id is required' });
    }

    const result = await permaGraphController.getComponentDependencies({
      component_iri: decodeURIComponent(iri),
      tenant_id: tenant_id as string,
      direction: direction as string,
    });

    res.json(result);
  } catch (error) {
    console.error('Component dependencies error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Circular dependencies detection
router.get('/circular-dependencies', async (req, res) => {
  try {
    const { tenant_id } = req.query;

    if (!tenant_id) {
      return res.status(400).json({ error: 'tenant_id is required' });
    }

    const result = await permaGraphController.findCircularDependencies({
      tenant_id: tenant_id as string,
    });

    res.json(result);
  } catch (error) {
    console.error('Circular dependencies error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Component impact score
router.get('/component/:iri/impact', async (req, res) => {
  try {
    const { iri } = req.params;
    const { tenant_id } = req.query;

    if (!tenant_id) {
      return res.status(400).json({ error: 'tenant_id is required' });
    }

    const result = await permaGraphController.calculateComponentImpact({
      component_iri: decodeURIComponent(iri),
      tenant_id: tenant_id as string,
    });

    res.json(result);
  } catch (error) {
    console.error('Component impact error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Dependency graph analysis
router.get('/dependency-graph', async (req, res) => {
  try {
    const { tenant_id } = req.query;

    if (!tenant_id) {
      return res.status(400).json({ error: 'tenant_id is required' });
    }

    const result = await permaGraphController.analyzeDependencyGraph({
      tenant_id: tenant_id as string,
    });

    res.json(result);
  } catch (error) {
    console.error('Dependency graph analysis error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
