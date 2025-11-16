import { useState } from 'react';
import {
  knowledgeBaseService,
  type KnowledgeBaseQuery,
  type PatternSearchParams,
  type PracticeSearchParams,
} from '../services/knowledgeBaseService';

export function useKnowledgeBase() {
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [patterns, setPatterns] = useState<any[]>([]);
  const [practices, setPractices] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = async (query: KnowledgeBaseQuery) => {
    setLoading(true);
    setError(null);
    try {
      const res = await knowledgeBaseService.search(query);
      const results = res.data?.results ?? res.results ?? [];
      setSearchResults(results);
      return results;
    } catch (e: any) {
      setError(e.message || 'Search failed');
      throw e;
    } finally {
      setLoading(false);
    }
  };

  const listPatterns = async (params: PatternSearchParams = {}) => {
    setLoading(true);
    setError(null);
    try {
      const res = await knowledgeBaseService.getPatterns(params);
      const list = res.data?.patterns ?? res.patterns ?? [];
      setPatterns(list);
      return list;
    } catch (e: any) {
      setError(e.message || 'Failed to fetch patterns');
      throw e;
    } finally {
      setLoading(false);
    }
  };

  const listPractices = async (params: PracticeSearchParams = {}) => {
    setLoading(true);
    setError(null);
    try {
      const res = await knowledgeBaseService.getPractices(params);
      const list = res.data?.practices ?? res.practices ?? [];
      setPractices(list);
      return list;
    } catch (e: any) {
      setError(e.message || 'Failed to fetch practices');
      throw e;
    } finally {
      setLoading(false);
    }
  };

  return {
    search,
    listPatterns,
    listPractices,
    searchResults,
    patterns,
    practices,
    loading,
    error,
  };
}

export default useKnowledgeBase;
