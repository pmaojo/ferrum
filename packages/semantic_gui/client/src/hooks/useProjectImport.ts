import { useState, useCallback } from 'react';
import { importProject } from '@/services/projectManagement';

export function useProjectImport() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const importProjectFn = useCallback(async (file: File) => {
    setIsLoading(true);
    setError(null);
    try {
      return await importProject(file);
    } catch (e: any) {
      setError(e.message);
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { importProject: importProjectFn, isLoading, error };
}

export default useProjectImport;
