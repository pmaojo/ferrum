/**
 * Service functions for semantic navigation features.
 */

interface ErrorResponse {
  error?: string;
  message?: string;
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

interface SemanticRecommendation {
  componentIri: string;
  componentName: string;
  relationshipType: string;
  confidence: number;
  reasoning: string;
  suggestedActions: string[];
  metadata: Record<string, unknown>;
}

interface SemanticRecommendationsResponse {
  recommendations: SemanticRecommendation[];
  contextId: string;
  totalResults: number;
}

export async function getSemanticRecommendations(
  currentComponentIri: string,
  tenantId: string,
  contextId = 'default'
): Promise<SemanticRecommendationsResponse> {
  const res = await fetch('/api/v1/semantic/recommendations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_component_iri: currentComponentIri,
      tenant_id: tenantId,
      context_id: contextId,
    }),
  });
  return handleResponse<SemanticRecommendationsResponse>(res, 'Failed to fetch semantic recommendations');
}

interface SemanticSearchResult {
  iri: string;
  name: string;
  type: string;
  description: string;
  relevanceScore: number;
  context: Record<string, unknown>;
  relationships: Array<{
    targetIri: string;
    relationshipType: string;
    direction: 'incoming' | 'outgoing';
  }>;
}

interface SemanticSearchResponse {
  results: SemanticSearchResult[];
  query: string;
  totalResults: number;
  executionTime: number;
  scope: string;
}

export async function semanticSearch(
  query: string,
  tenantId: string,
  options: { scope?: string; maxResults?: number } = {}
): Promise<SemanticSearchResponse> {
  const res = await fetch('/api/v1/semantic/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      tenant_id: tenantId,
      scope: options.scope ?? 'all',
      max_results: options.maxResults ?? 50,
    }),
  });
  return handleResponse<SemanticSearchResponse>(res, 'Semantic search failed');
}

export const semanticService = {
  getSemanticRecommendations,
  semanticSearch,
};

export default semanticService;
