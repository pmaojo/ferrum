import { useState, useCallback } from 'react';
import { getProjectScore } from '@/services/projectManagement';

export interface ProjectScoreResult {
  score: number;
  compliance: number;
  penalties: number;
  rewards: number;
  totalNodes: number;
  totalEdges: number;
}

export function useProjectScore() {
  const [score, setScore] = useState<ProjectScoreResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchScore = useCallback(async (projectId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getProjectScore(projectId);
      setScore(res);
      return res;
    } catch (e: any) {
      setError(e.message);
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { fetchScore, score, isLoading, error };
}

export default useProjectScore;
