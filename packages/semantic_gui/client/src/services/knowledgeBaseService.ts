/**
 * Service functions for interacting with the semantic knowledge base API.
 * Provides wrappers around search, pattern listing and practice retrieval endpoints.
 */

import type { KnowledgeResult, PatternMatch, ImprovementSuggestion } from '../../../shared/types/api-responses';
import { typedApiResponseFetch, isObject, isArray } from '../../../shared/types/type-guards';

export interface KnowledgeBaseQuery {
  queryType:
    | 'pattern_search'
    | 'practice_search'
    | 'violation_analysis'
    | 'improvement_suggestions'
    | 'community_content'
    | 'architectural_guidance';
  queryText: string;
  context?: Record<string, unknown>;
  filters?: Record<string, unknown>;
  maxResults?: number;
}

export interface PatternSearchParams {
  category?: string;
  complexity?: string;
  tags?: string[];
  framework?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface PracticeSearchParams {
  practiceType?: string;
  context?: string;
  severity?: string;
  tags?: string[];
  framework?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

interface ErrorResponse {
  error?: string;
  message?: string;
}

function isKnowledgeResult(value: unknown): value is KnowledgeResult {
  if (!isObject(value)) return false;
  const result = value as Record<string, unknown>;
  
  return (
    typeof result.queryId === 'string' &&
    typeof result.resultType === 'string' &&
    typeof result.title === 'string' &&
    typeof result.description === 'string' &&
    isObject(result.content) &&
    typeof result.relevanceScore === 'number' &&
    (result.source === 'library' || result.source === 'community' || result.source === 'generated') &&
    isObject(result.metadata)
  );
}

function isPatternMatch(value: unknown): value is PatternMatch {
  if (!isObject(value)) return false;
  const pattern = value as Record<string, unknown>;
  
  return (
    typeof pattern.patternId === 'string' &&
    typeof pattern.patternName === 'string' &&
    typeof pattern.confidence === 'number' &&
    isArray(pattern.matchedComponents, (item): item is string => typeof item === 'string') &&
    isArray(pattern.missingComponents, (item): item is string => typeof item === 'string') &&
    isArray(pattern.violations, (item): item is string => typeof item === 'string') &&
    isObject(pattern.evidence) &&
    isObject(pattern.context)
  );
}

function isImprovementSuggestion(value: unknown): value is ImprovementSuggestion {
  if (!isObject(value)) return false;
  const suggestion = value as Record<string, unknown>;
  
  return (
    typeof suggestion.id === 'string' &&
    typeof suggestion.suggestionType === 'string' &&
    (suggestion.priority === 'low' || suggestion.priority === 'medium' || 
     suggestion.priority === 'high' || suggestion.priority === 'critical') &&
    typeof suggestion.title === 'string' &&
    typeof suggestion.description === 'string' &&
    typeof suggestion.rationale === 'string' &&
    isArray(suggestion.affectedComponents, (item): item is string => typeof item === 'string') &&
    isArray(suggestion.implementationSteps, (item): item is string => typeof item === 'string') &&
    typeof suggestion.confidence === 'number' &&
    typeof suggestion.createdAt === 'string'
  );
}

async function handleResponse<T>(res: Response, defaultMessage: string): Promise<T> {
  if (!res.ok) {
    let message = defaultMessage;
    try {
      const data = await res.json() as ErrorResponse;
      message = data.error || data.message || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

interface KnowledgeSearchResponse {
  results: KnowledgeResult[];
  totalResults: number;
  queryId: string;
  executionTime: number;
}

export async function searchKnowledgeBase(
  query: KnowledgeBaseQuery
): Promise<KnowledgeSearchResponse> {
  return typedApiResponseFetch(
    '/api/v1/knowledge-base/search',
    (data): data is KnowledgeSearchResponse => {
      if (!isObject(data)) return false;
      const response = data as Record<string, unknown>;
      
      return (
        isArray(response.results, isKnowledgeResult) &&
        typeof response.totalResults === 'number' &&
        typeof response.queryId === 'string' &&
        typeof response.executionTime === 'number'
      );
    },
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(query),
    },
    'Failed to search knowledge base'
  );
}

interface PatternsResponse {
  patterns: PatternMatch[];
  totalCount: number;
  pagination: {
    limit: number;
    offset: number;
    hasMore: boolean;
  };
}

export async function getPatterns(
  params: PatternSearchParams = {}
): Promise<PatternsResponse> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      if (typeof value === 'object') {
        query.append(key, JSON.stringify(value));
      } else {
        query.append(key, String(value));
      }
    }
  });

  return typedApiResponseFetch(
    `/api/v1/knowledge-base/patterns?${query.toString()}`,
    (data): data is PatternsResponse => {
      if (!isObject(data)) return false;
      const response = data as Record<string, unknown>;
      
      return (
        isArray(response.patterns, isPatternMatch) &&
        typeof response.totalCount === 'number' &&
        isObject(response.pagination)
      );
    },
    undefined,
    'Failed to fetch patterns'
  );
}

interface PracticesResponse {
  practices: ImprovementSuggestion[];
  totalCount: number;
  pagination: {
    limit: number;
    offset: number;
    hasMore: boolean;
  };
}

export async function getPractices(
  params: PracticeSearchParams = {}
): Promise<PracticesResponse> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      if (typeof value === 'object') {
        query.append(key, JSON.stringify(value));
      } else {
        query.append(key, String(value));
      }
    }
  });

  return typedApiResponseFetch(
    `/api/v1/knowledge-base/practices?${query.toString()}`,
    (data): data is PracticesResponse => {
      if (!isObject(data)) return false;
      const response = data as Record<string, unknown>;
      
      return (
        isArray(response.practices, isImprovementSuggestion) &&
        typeof response.totalCount === 'number' &&
        isObject(response.pagination)
      );
    },
    undefined,
    'Failed to fetch practices'
  );
}

export const knowledgeBaseService = {
  search: searchKnowledgeBase,
  getPatterns,
  getPractices,
};

export default knowledgeBaseService;
