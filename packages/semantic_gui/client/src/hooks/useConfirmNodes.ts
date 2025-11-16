import { useState, useCallback } from 'react';
import { confirmNodes as confirmNodesService } from '@/services/projectManagement';

export function useConfirmNodes() {
  const [result, setResult] = useState<{
    message: string;
    confirmedNodes: number;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confirmNodes = useCallback(
    async (projectId: string, files: string[]) => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await confirmNodesService(projectId, files);
        setResult(res);
        return res;
      } catch (e: any) {
        setError(e.message);
        throw e;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  return { confirmNodes, result, isLoading, error };
}

export default useConfirmNodes;
