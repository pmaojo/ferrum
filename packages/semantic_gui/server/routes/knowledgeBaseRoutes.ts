/**
 * Knowledge Base API Routes
 *
 * Provides REST API endpoints for accessing the semantic knowledge base
 * from the SCG frontend, including pattern search, practice recommendations,
 * and architectural insights.
 */

import type { Request, Response } from 'express';
import { Router } from 'express';
import { z } from 'zod';

import { authMiddleware } from '../middleware/auth';
import { requireRole } from '../middleware/requireRole';
import { validateRequest } from '../middleware/validation';
import { KnowledgeBaseService } from '../services/knowledge-base-service';
import type { SCGTag } from '../types/universal-tag-system';
import { logger } from '../utils/logger';

const router = Router();
const knowledgeBaseService = new KnowledgeBaseService();

// Validation schemas
const QuerySchema = z.object({
  queryType: z.enum([
    'pattern_search',
    'practice_search',
    'violation_analysis',
    'improvement_suggestions',
    'community_content',
    'architectural_guidance',
  ]),
  queryText: z.string().min(1).max(500),
  context: z.record(z.any()).optional(),
  filters: z.record(z.any()).optional(),
  maxResults: z.number().int().min(1).max(50).default(10),
});

const ComponentsSchema = z.array(
  z.object({
    iri: z.string(),
    componentType: z.string(),
    name: z.string(),
    moduleNamespace: z.string(),
    properties: z.record(z.any()),
    relationships: z.array(
      z.object({
        subjectIri: z.string(),
        predicateIri: z.string(),
        objectIri: z.string(),
        relationshipType: z.string(),
      })
    ),
  })
);

const InsightsRequestSchema = z.object({
  components: ComponentsSchema,
  projectContext: z.array(z.string()),
});

/**
 * List available knowledge base queries
 * GET /api/knowledge-base/queries
 */
router.get('/queries', async (_req: Request, res: Response) => {
  try {
    const queries = await knowledgeBaseService.listQueries();
    res.json({ success: true, queries });
  } catch (error) {
    logger.error('Error fetching knowledge base queries', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch knowledge base queries',
    });
  }
});

/**
 * Search the knowledge base
 * POST /api/knowledge-base/search
 */
router.post(
  '/search',
  validateRequest(QuerySchema),
  async (req: Request, res: Response) => {
    try {
      const query = req.body;

      logger.info('Knowledge base search request', {
        queryType: query.queryType,
        queryText: query.queryText,
        maxResults: query.maxResults,
      });

      const results = await knowledgeBaseService.queryKnowledgeBase(query);

      res.json({
        success: true,
        data: {
          results,
          totalResults: results.length,
          queryId: generateQueryId(),
          timestamp: new Date().toISOString(),
        },
      });
    } catch (error) {
      logger.error('Knowledge base search error', error);
      res.status(500).json({
        success: false,
        error: 'Failed to search knowledge base',
        details: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  }
);

/**
 * Get architectural patterns
 * GET /api/knowledge-base/patterns
 */
router.get('/patterns', async (req: Request, res: Response) => {
  try {
    const {
      category,
      complexity,
      scgTags,
      framework,
      search,
      limit = 20,
      offset = 0,
    } = req.query as Record<string, any>;

    let parsedTags: SCGTag[] | undefined = undefined;
    if (scgTags) {
      try {
        parsedTags = JSON.parse(scgTags);
      } catch {
        logger.warn('Invalid scgTags parameter');
      }
    }

    const patterns = await knowledgeBaseService.searchPatterns({
      category,
      complexity,
      tags: parsedTags,
      framework,
      search,
      limit: parseInt(limit),
      offset: parseInt(offset),
    });

    res.json({
      success: true,
      data: {
        patterns,
        totalCount: patterns.length,
        hasMore: patterns.length === parseInt(limit),
      },
    });
  } catch (error) {
    logger.error('Error fetching patterns', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch patterns',
    });
  }
});

/**
 * Get specific pattern by ID
 * GET /api/knowledge-base/patterns/:id
 */
router.get('/patterns/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const pattern = await knowledgeBaseService.getPattern(id);

    if (!pattern) {
      return res.status(404).json({
        success: false,
        error: 'Pattern not found',
      });
    }

    // Get related patterns
    const relatedPatterns = await knowledgeBaseService.getRelatedPatterns(id);

    res.json({
      success: true,
      data: {
        pattern,
        relatedPatterns,
      },
    });
  } catch (error) {
    logger.error('Error fetching pattern', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch pattern',
    });
  }
});

/**
 * Get best practices
 * GET /api/knowledge-base/practices
 */
router.get('/practices', async (req: Request, res: Response) => {
  try {
    const {
      practiceType,
      context,
      severity,
      scgTags,
      framework,
      search,
      limit = 20,
      offset = 0,
    } = req.query as Record<string, any>;

    let parsedTags: SCGTag[] | undefined = undefined;
    if (scgTags) {
      try {
        parsedTags = JSON.parse(scgTags);
      } catch {
        logger.warn('Invalid scgTags parameter');
      }
    }

    const practices = await knowledgeBaseService.searchPractices({
      practiceType,
      context,
      severity,
      tags: parsedTags,
      framework,
      search,
      limit: parseInt(limit),
      offset: parseInt(offset),
    });

    res.json({
      success: true,
      data: {
        practices,
        totalCount: practices.length,
        hasMore: practices.length === parseInt(limit),
      },
    });
  } catch (error) {
    logger.error('Error fetching practices', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch practices',
    });
  }
});

/**
 * Get specific practice by ID
 * GET /api/knowledge-base/practices/:id
 */
router.get('/practices/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const practice = await knowledgeBaseService.getPractice(id);

    if (!practice) {
      return res.status(404).json({
        success: false,
        error: 'Practice not found',
      });
    }

    // Get related practices
    const relatedPractices = await knowledgeBaseService.getRelatedPractices(id);

    res.json({
      success: true,
      data: {
        practice,
        relatedPractices,
      },
    });
  } catch (error) {
    logger.error('Error fetching practice', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch practice',
    });
  }
});

/**
 * Analyze architecture and get insights
 * POST /api/knowledge-base/insights
 */
router.post(
  '/insights',
  validateRequest(InsightsRequestSchema),
  async (req: Request, res: Response) => {
    try {
      const { components, projectContext } = req.body;

      logger.info('Generating architectural insights', {
        componentCount: components.length,
        projectContext,
      });

      const insights = await knowledgeBaseService.generateArchitecturalInsights(
        components,
        projectContext
      );

      res.json({
        success: true,
        data: {
          insights,
          analysisTimestamp: new Date().toISOString(),
          componentCount: components.length,
          contextCount: projectContext.length,
        },
      });
    } catch (error) {
      logger.error('Error generating insights', error);
      res.status(500).json({
        success: false,
        error: 'Failed to generate architectural insights',
      });
    }
  }
);

/**
 * Get pattern matching results for architecture
 * POST /api/knowledge-base/pattern-matching
 */
router.post(
  '/pattern-matching',
  validateRequest(InsightsRequestSchema),
  async (req: Request, res: Response) => {
    try {
      const { components, projectContext } = req.body;

      const matchingResults = await knowledgeBaseService.analyzePatternMatches(
        components,
        projectContext
      );

      res.json({
        success: true,
        data: {
          patternMatches: matchingResults.patternMatches,
          suggestions: matchingResults.suggestions,
          analysisTimestamp: new Date().toISOString(),
        },
      });
    } catch (error) {
      logger.error('Error analyzing pattern matches', error);
      res.status(500).json({
        success: false,
        error: 'Failed to analyze pattern matches',
      });
    }
  }
);

/**
 * Get community contributions
 * GET /api/knowledge-base/community
 */
router.get('/community', async (req: Request, res: Response) => {
  try {
    const {
      contributionType,
      status,
      scgTags,
      framework,
      category,
      search,
      limit = 20,
      offset = 0,
    } = req.query as Record<string, any>;

    let parsedTags: SCGTag[] | undefined = undefined;
    if (scgTags) {
      try {
        parsedTags = JSON.parse(scgTags);
      } catch {
        logger.warn('Invalid scgTags parameter');
      }
    }

    const contributions =
      await knowledgeBaseService.searchCommunityContributions({
        contributionType,
        status,
        tags: parsedTags,
        framework,
        category,
        search,
        limit: parseInt(limit),
        offset: parseInt(offset),
      });

    res.json({
      success: true,
      data: {
        contributions,
        totalCount: contributions.length,
        hasMore: contributions.length === parseInt(limit),
      },
    });
  } catch (error) {
    logger.error('Error fetching community contributions', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch community contributions',
    });
  }
});

/**
 * Get trending community content
 * GET /api/knowledge-base/community/trending
 */
router.get('/community/trending', async (req: Request, res: Response) => {
  try {
    const { limit = 10 } = req.query;

    const trendingContent =
      await knowledgeBaseService.getTrendingCommunityContent(
        parseInt(limit as string)
      );

    res.json({
      success: true,
      data: {
        trending: trendingContent,
        generatedAt: new Date().toISOString(),
      },
    });
  } catch (error) {
    logger.error('Error fetching trending content', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch trending content',
    });
  }
});

/**
 * Submit a new community contribution
 * POST /api/knowledge-base/community/contribute
 */
router.post('/community/contribute', async (req: Request, res: Response) => {
  try {
    const {
      contributorId,
      contributionType,
      title,
      description,
      content,
      tags,
      category,
    } = req.body;

    // Validate required fields
    if (
      !contributorId ||
      !contributionType ||
      !title ||
      !description ||
      !content
    ) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields',
      });
    }

    const contribution = await knowledgeBaseService.submitCommunityContribution(
      {
        contributorId,
        contributionType,
        title,
        description,
        content,
        tags: tags || [],
        category,
      }
    );

    res.status(201).json({
      success: true,
      data: {
        contribution,
        message: 'Contribution submitted successfully',
      },
    });
  } catch (error) {
    logger.error('Error submitting contribution', error);
    res.status(500).json({
      success: false,
      error: 'Failed to submit contribution',
    });
  }
});

/**
 * Vote on a community contribution
 * POST /api/knowledge-base/community/:id/vote
 */
router.post('/community/:id/vote', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { userId, isUpvote } = req.body;

    if (!userId || typeof isUpvote !== 'boolean') {
      return res.status(400).json({
        success: false,
        error: 'Missing userId or isUpvote',
      });
    }

    const success = await knowledgeBaseService.voteOnContribution(
      id,
      userId,
      isUpvote
    );

    if (!success) {
      return res.status(404).json({
        success: false,
        error: 'Contribution not found or vote failed',
      });
    }

    res.json({
      success: true,
      data: {
        message: `${isUpvote ? 'Upvote' : 'Downvote'} recorded successfully`,
      },
    });
  } catch (error) {
    logger.error('Error voting on contribution', error);
    res.status(500).json({
      success: false,
      error: 'Failed to record vote',
    });
  }
});

/**
 * Get knowledge base statistics
 * GET /api/knowledge-base/stats
 */
router.get('/stats', async (req: Request, res: Response) => {
  try {
    const stats = await knowledgeBaseService.getKnowledgeBaseStatistics();

    res.json({
      success: true,
      data: {
        statistics: stats,
        generatedAt: new Date().toISOString(),
      },
    });
  } catch (error) {
    logger.error('Error fetching knowledge base stats', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch statistics',
    });
  }
});

/**
 * Get architectural guidance for a specific query
 * POST /api/knowledge-base/guidance
 */
router.post('/guidance', async (req: Request, res: Response) => {
  try {
    const { query, context, maxRecommendations = 5 } = req.body;

    if (!query) {
      return res.status(400).json({
        success: false,
        error: 'Query is required',
      });
    }

    const guidance = await knowledgeBaseService.getArchitecturalGuidance(
      query,
      context || {},
      maxRecommendations
    );

    res.json({
      success: true,
      data: {
        guidance,
        query,
        generatedAt: new Date().toISOString(),
      },
    });
  } catch (error) {
    logger.error('Error generating architectural guidance', error);
    res.status(500).json({
      success: false,
      error: 'Failed to generate guidance',
    });
  }
});

/**
 * Apply an improvement suggestion
 * POST /api/knowledge-base/suggestions/:id/apply
 */
router.post(
  '/suggestions/:id/apply',
  authMiddleware,
  requireRole('owner', 'reader'),
  async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const { components } = req.body;

      if (!components) {
        return res.status(400).json({
          success: false,
          error: 'Components are required',
        });
      }

      const result = await knowledgeBaseService.applySuggestion(id, components);

      res.json({
        success: true,
        data: result,
      });
    } catch (error) {
      logger.error('Error applying suggestion', error);
      res.status(500).json({
        success: false,
        error: 'Failed to apply suggestion',
      });
    }
  }
);

// Helper function to generate query IDs
function generateQueryId(): string {
  return `query_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export default router;
