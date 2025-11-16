import { useState, useCallback } from 'react';
import { exportProject } from '@/services/projectManagement';

export function useProjectExport() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const exportProjectFn = useCallback(async (projectId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      return await exportProject(projectId);
    } catch (e: any) {
      setError(e.message);
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { exportProject: exportProjectFn, isLoading, error };
}

export default useProjectExport;
