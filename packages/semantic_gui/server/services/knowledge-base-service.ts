/**
 * Knowledge Base Service
 *
 * Service layer that interfaces with PermaGraph's semantic knowledge base
 * to provide architectural patterns, best practices, and intelligent suggestions
 * to the SCG frontend.
 */

import axios from 'axios';

import type { SCGTag } from '../types/universal-tag-system';
import { logger } from '../utils/logger';

import { TagTranslator } from './tagging/TagTranslator';

interface KnowledgeQuery {
  queryType:
    | 'pattern_search'
    | 'practice_search'
    | 'violation_analysis'
    | 'improvement_suggestions'
    | 'community_content'
    | 'architectural_guidance';
  queryText: string;
  context?: Record<string, any>;
  filters?: Record<string, any>;
  maxResults?: number;
}

interface KnowledgeResult {
  queryId: string;
  resultType: string;
  title: string;
  description: string;
  content: Record<string, any>;
  relevanceScore: number;
  source: 'library' | 'community' | 'generated';
  metadata: Record<string, any>;
}

interface ArchitecturalComponent {
  iri: string;
  componentType: string;
  name: string;
  moduleNamespace: string;
  properties: Record<string, any>;
  relationships: Array<{
    subjectIri: string;
    predicateIri: string;
    objectIri: string;
    relationshipType: string;
  }>;
}

interface ArchitecturalInsight {
  id: string;
  title: string;
  description: string;
  insightType:
    | 'pattern_opportunity'
    | 'violation_risk'
    | 'improvement_potential';
  confidence: number;
  supportingEvidence: string[];
  recommendedActions: string[];
  relatedPatterns: string[];
  relatedPractices: string[];
  impactAssessment: Record<string, any>;
  createdAt: string;
}

interface PatternMatch {
  patternId: string;
  patternName: string;
  confidence: number;
  matchedComponents: string[];
  missingComponents: string[];
  violations: string[];
  evidence: Record<string, any>;
  context: Record<string, any>;
}

interface ImprovementSuggestion {
  id: string;
  suggestionType: string;
  priority: string;
  title: string;
  description: string;
  rationale: string;
  affectedComponents: string[];
  implementationSteps: string[];
  codeExamples: Record<string, string>;
  estimatedEffort: string;
  benefits: string[];
  risks: string[];
  relatedPatterns: string[];
  relatedPractices: string[];
  confidence: number;
  createdAt: string;
}

export class KnowledgeBaseService {
  private permagraphBaseUrl: string;
  private requestTimeout: number;
  private tagTranslator: TagTranslator;

  constructor() {
    this.permagraphBaseUrl =
      process.env.PERMAGRAPH_API_URL || 'http://localhost:8000';
    this.requestTimeout = 30000; // 30 seconds
    this.tagTranslator = new TagTranslator();
  }

  private async mapTagsToFramework(
    tags?: SCGTag[],
    framework?: string
  ): Promise<string[] | undefined> {
    if (!tags || tags.length === 0) return undefined;
    if (framework) {
      try {
        const native = await this.tagTranslator.translateFromSCG(
          tags,
          framework
        );
        return native.map(t => t.type);
      } catch {
        return tags.map(t => t.type);
      }
    }
    return tags.map(t => t.type);
  }

  /**
   * Query the semantic knowledge base
   */
  async queryKnowledgeBase(query: KnowledgeQuery): Promise<KnowledgeResult[]> {
    try {
      logger.info('Querying knowledge base', {
        queryType: query.queryType,
        queryText: query.queryText,
      });

      const payload = {
        question: query.queryText,
        kg_id: query.context?.kg_id || 'default',
        tenant_id: query.context?.tenant_id || 'default',
        user_id: query.context?.user_id,
        max_results: query.maxResults,
        query_opts: {
          type: query.queryType,
          filters: query.filters,
          context: query.context,
        },
      };

      const response = await axios.post(
        `${this.permagraphBaseUrl}/api/v1/query`,
        payload,
        {
          timeout: this.requestTimeout,
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.data.metadata?.error) {
        throw new Error('Knowledge base query failed');
      }

      return response.data.results || [];
    } catch (error) {
      logger.error('Knowledge base query error', error);

      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNREFUSED') {
          throw new Error('PermaGraph service is not available');
        }
        if (error.response?.status === 404) {
          throw new Error('Knowledge base endpoint not found');
        }
      }

      throw error;
    }
  }

  /**
   * List available query presets from PermaGraph
   */
  async listQueries(): Promise<any[]> {
    try {
      const response = await axios.get(
        `${this.permagraphBaseUrl}/api/v1/queries`,
        { timeout: this.requestTimeout }
      );
      return response.data.queries || [];
    } catch (error) {
      logger.error('Error fetching query presets', error);
      return [];
    }
  }

  /**
   * Search architectural patterns
   */
  async searchPatterns(params: {
    category?: string;
    complexity?: string;
    tags?: SCGTag[];
    framework?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<any[]> {
    try {
      const mappedTags = await this.mapTagsToFramework(
        params.tags,
        params.framework
      );
      const query: KnowledgeQuery = {
        queryType: 'pattern_search',
        queryText: params.search || '',
        filters: {
          category: params.category,
          complexity: params.complexity,
          tags: mappedTags,
        },
        maxResults: params.limit || 20,
      };

      const results = await this.queryKnowledgeBase(query);
      return results.map(result => ({
        id: result.content.pattern?.id,
        name: result.title,
        description: result.description,
        category: result.metadata.category,
        complexity: result.metadata.complexity,
        tags: result.metadata.tags,
        usageCount: result.metadata.usage_count,
        communityRating: result.metadata.community_rating,
        relevanceScore: result.relevanceScore,
        examples: result.content.examples || [],
        violations: result.content.violations || [],
      }));
    } catch (error) {
      logger.error('Error searching patterns', error);
      throw error;
    }
  }

  /**
   * Get a specific pattern by ID
   */
  async getPattern(patternId: string): Promise<any | null> {
    try {
      const response = await axios.get(
        `${this.permagraphBaseUrl}/api/patterns/${patternId}`,
        { timeout: this.requestTimeout }
      );

      return response.data.success ? response.data.pattern : null;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null;
      }
      logger.error('Error fetching pattern', error);
      throw error;
    }
  }

  /**
   * Get related patterns for a pattern
   */
  async getRelatedPatterns(patternId: string): Promise<any[]> {
    try {
      const response = await axios.get(
        `${this.permagraphBaseUrl}/api/patterns/${patternId}/related`,
        { timeout: this.requestTimeout }
      );

      return response.data.success ? response.data.related_patterns : [];
    } catch (error) {
      logger.error('Error fetching related patterns', error);
      return []; // Return empty array on error
    }
  }

  /**
   * Search best practices
   */
  async searchPractices(params: {
    practiceType?: string;
    context?: string;
    severity?: string;
    tags?: SCGTag[];
    framework?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<any[]> {
    try {
      const mappedTags = await this.mapTagsToFramework(
        params.tags,
        params.framework
      );
      const query: KnowledgeQuery = {
        queryType: 'practice_search',
        queryText: params.search || '',
        filters: {
          practice_type: params.practiceType,
          context: params.context,
          severity: params.severity,
          tags: mappedTags,
        },
        maxResults: params.limit || 20,
      };

      const results = await this.queryKnowledgeBase(query);
      return results.map(result => ({
        id: result.content.practice?.id,
        name: result.title,
        description: result.description,
        practiceType: result.metadata.practice_type,
        context: result.metadata.context,
        severity: result.metadata.severity,
        effortToFix: result.metadata.effort_to_fix,
        tags: result.metadata.tags,
        relevanceScore: result.relevanceScore,
        implementationSteps: result.content.implementation_steps || [],
        codeExamples: result.content.code_examples || {},
        evidence: result.content.evidence || [],
      }));
    } catch (error) {
      logger.error('Error searching practices', error);
      throw error;
    }
  }

  /**
   * Get a specific practice by ID
   */
  async getPractice(practiceId: string): Promise<any | null> {
    try {
      const response = await axios.get(
        `${this.permagraphBaseUrl}/api/practices/${practiceId}`,
        { timeout: this.requestTimeout }
      );

      return response.data.success ? response.data.practice : null;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null;
      }
      logger.error('Error fetching practice', error);
      throw error;
    }
  }

  /**
   * Get related practices for a practice
   */
  async getRelatedPractices(practiceId: string): Promise<any[]> {
    try {
      const response = await axios.get(
        `${this.permagraphBaseUrl}/api/practices/${practiceId}/related`,
        { timeout: this.requestTimeout }
      );

      return response.data.success ? response.data.related_practices : [];
    } catch (error) {
      logger.error('Error fetching related practices', error);
      return []; // Return empty array on error
    }
  }

  /**
   * Generate architectural insights for components
   */
  async generateArchitecturalInsights(
    components: ArchitecturalComponent[],
    projectContext: string[]
  ): Promise<ArchitecturalInsight[]> {
    try {
      logger.info('Generating architectural insights', {
        componentCount: components.length,
        projectContext,
      });

      const response = await axios.post(
        `${this.permagraphBaseUrl}/api/knowledge-base/insights`,
        {
          components,
          project_context: projectContext,
        },
        {
          timeout: this.requestTimeout,
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.data.success) {
        return response.data.insights || [];
      } else {
        throw new Error(response.data.error || 'Failed to generate insights');
      }
    } catch (error) {
      logger.error('Error generating architectural insights', error);
      throw error;
    }
  }

  /**
   * Analyze pattern matches for architecture
   */
  async analyzePatternMatches(
    components: ArchitecturalComponent[],
    projectContext: string[]
  ): Promise<{
    patternMatches: PatternMatch[];
    suggestions: ImprovementSuggestion[];
  }> {
    try {
      const response = await axios.post(
        `${this.permagraphBaseUrl}/api/knowledge-base/pattern-analysis`,
        {
          components,
          project_context: projectContext,
        },
        {
          timeout: this.requestTimeout,
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.data.success) {
        return {
          patternMatches: response.data.pattern_matches || [],
          suggestions: response.data.suggestions || [],
        };
      } else {
        throw new Error(response.data.error || 'Failed to analyze patterns');
      }
    } catch (error) {
      logger.error('Error analyzing pattern matches', error);
      throw error;
    }
  }

  /**
   * Search community contributions
   */
  async searchCommunityContributions(params: {
    contributionType?: string;
    status?: string;
    tags?: SCGTag[];
    framework?: string;
    category?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<any[]> {
    try {
      const mappedTags = await this.mapTagsToFramework(
        params.tags,
        params.framework
      );
      const query: KnowledgeQuery = {
        queryType: 'community_content',
        queryText: params.search || '',
        filters: {
          contribution_type: params.contributionType,
          status: params.status,
          tags: mappedTags,
          category: params.category,
        },
        maxResults: params.limit || 20,
      };

      const results = await this.queryKnowledgeBase(query);
      return results.map(result => ({
        id: result.content.contribution_id,
        title: result.title,
        description: result.description,
        contributionType: result.content.contribution_type,
        contributor: result.content.contributor,
        upvotes: result.content.upvotes,
        downvotes: result.content.downvotes,
        status: result.metadata.status,
        category: result.metadata.category,
        tags: result.metadata.tags,
        createdAt: result.metadata.created_at,
        voteRatio: result.metadata.vote_ratio,
        relevanceScore: result.relevanceScore,
        reviews: result.content.reviews || [],
      }));
    } catch (error) {
      logger.error('Error searching community contributions', error);
      throw error;
    }
  }

  /**
   * Get trending community content
   */
  async getTrendingCommunityContent(limit: number = 10): Promise<any[]> {
    try {
      const response = await axios.get(
        `${this.permagraphBaseUrl}/api/community/trending?limit=${limit}`,
        { timeout: this.requestTimeout }
      );

      return response.data.success ? response.data.trending : [];
    } catch (error) {
      logger.error('Error fetching trending content', error);
      return []; // Return empty array on error
    }
  }

  /**
   * Submit a community contribution
   */
  async submitCommunityContribution(contribution: {
    contributorId: string;
    contributionType: string;
    title: string;
    description: string;
    content: any;
    tags: string[];
    category?: string;
  }): Promise<any> {
    try {
      const response = await axios.post(
        `${this.permagraphBaseUrl}/api/community/contribute`,
        contribution,
        {
          timeout: this.requestTimeout,
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.data.success) {
        return response.data.contribution;
      } else {
        throw new Error(response.data.error || 'Failed to submit contribution');
      }
    } catch (error) {
      logger.error('Error submitting community contribution', error);
      throw error;
    }
  }

  /**
   * Vote on a community contribution
   */
  async voteOnContribution(
    contributionId: string,
    userId: string,
    isUpvote: boolean
  ): Promise<boolean> {
    try {
      const response = await axios.post(
        `${this.permagraphBaseUrl}/api/community/${contributionId}/vote`,
        {
          user_id: userId,
          is_upvote: isUpvote,
        },
        {
          timeout: this.requestTimeout,
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      return response.data.success || false;
    } catch (error) {
      logger.error('Error voting on contribution', error);
      return false;
    }
  }

  /**
   * Get knowledge base statistics
   */
  async getKnowledgeBaseStatistics(): Promise<any> {
    try {
      const response = await axios.get(
        `${this.permagraphBaseUrl}/api/knowledge-base/statistics`,
        { timeout: this.requestTimeout }
      );

      return response.data.success ? response.data.statistics : {};
    } catch (error) {
      logger.error('Error fetching knowledge base statistics', error);
      return {}; // Return empty object on error
    }
  }

  /**
   * Get architectural guidance
   */
  async getArchitecturalGuidance(
    query: string,
    context: Record<string, any> = {},
    maxRecommendations: number = 5
  ): Promise<any> {
    try {
      const knowledgeQuery: KnowledgeQuery = {
        queryType: 'architectural_guidance',
        queryText: query,
        context,
        maxResults: maxRecommendations,
      };

      const results = await this.queryKnowledgeBase(knowledgeQuery);

      if (results.length > 0) {
        return results[0].content;
      }

      return {
        recommended_patterns: [],
        recommended_practices: [],
        guidance_summary: 'No specific guidance found for this query.',
      };
    } catch (error) {
      logger.error('Error getting architectural guidance', error);
      throw error;
    }
  }

  /**
   * Apply an improvement suggestion
   */
  async applySuggestion(
    suggestionId: string,
    components: ArchitecturalComponent[]
  ): Promise<any> {
    try {
      const response = await axios.post(
        `${this.permagraphBaseUrl}/api/suggestions/${suggestionId}/apply`,
        { components },
        {
          timeout: this.requestTimeout,
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.data.success) {
        return response.data.result;
      } else {
        throw new Error(response.data.error || 'Failed to apply suggestion');
      }
    } catch (error) {
      logger.error('Error applying suggestion', error);
      throw error;
    }
  }

  /**
   * Health check for the knowledge base service
   */
  async healthCheck(): Promise<{
    status: 'healthy' | 'unhealthy';
    details?: string;
  }> {
    try {
      const response = await axios.get(`${this.permagraphBaseUrl}/health`, {
        timeout: 5000,
      });

      return {
        status: response.status === 200 ? 'healthy' : 'unhealthy',
        details: response.data?.message || 'Service is running',
      };
    } catch (error) {
      logger.error('Knowledge base health check failed', error);
      return {
        status: 'unhealthy',
        details: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Get cached query results (if available)
   */
  async getCachedResults(queryHash: string): Promise<KnowledgeResult[] | null> {
    try {
      const response = await axios.get(
        `${this.permagraphBaseUrl}/api/knowledge-base/cache/${queryHash}`,
        { timeout: 5000 }
      );

      return response.data.success ? response.data.results : null;
    } catch (error) {
      // Cache miss is not an error
      return null;
    }
  }

  /**
   * Clear query cache
   */
  async clearCache(): Promise<boolean> {
    try {
      const response = await axios.delete(
        `${this.permagraphBaseUrl}/api/knowledge-base/cache`,
        { timeout: 10000 }
      );

      return response.data.success || false;
    } catch (error) {
      logger.error('Error clearing knowledge base cache', error);
      return false;
    }
  }
}
