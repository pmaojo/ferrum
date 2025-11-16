import { useState } from 'react';
import { semanticService } from '@/services/semanticService';

export function useSemanticRecommendations() {
  const [recommendations, setRecommendations] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRecommendations = async (
    componentIri: string,
    tenantId: string,
    contextId?: string
  ) => {
    setLoading(true);
    setError(null);
    try {
      const res = await semanticService.getSemanticRecommendations(
        componentIri,
        tenantId,
        contextId
      );
      const list = res.recommendations ?? res;
      setRecommendations(list);
      return list;
    } catch (e: any) {
      setError(e.message || 'Failed to load recommendations');
      throw e;
    } finally {
      setLoading(false);
    }
  };

  return { fetchRecommendations, recommendations, loading, error };
}

export default useSemanticRecommendations;
