import { useState } from 'react';
import { semanticService } from '@/services/semanticService';

export function useSemanticSearch() {
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = async (
    query: string,
    tenantId: string,
    options: { scope?: string; maxResults?: number } = {}
  ) => {
    setLoading(true);
    setError(null);
    try {
      const res = await semanticService.semanticSearch(
        query,
        tenantId,
        options
      );
      const list = res.results ?? res.data?.results ?? [];
      setResults(list);
      return list;
    } catch (e: any) {
      setError(e.message || 'Semantic search failed');
      throw e;
    } finally {
      setLoading(false);
    }
  };

  return { search, results, loading, error };
}

export default useSemanticSearch;
