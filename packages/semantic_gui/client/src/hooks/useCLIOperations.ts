import { useQuery } from '@tanstack/react-query';

export interface CLIOperation {
  key: string;
  label: string;
  description?: string;
  argsSchema?: any;
  command?: string;
}

export function useCLIOperations(projectId: string, enabled = true) {
  const query = useQuery<{ operations: CLIOperation[] }>({
    queryKey: ['cli-operations', projectId],
    queryFn: async () => {
      const res = await fetch(`/api/projects/${projectId}/cli/operations`);
      if (!res.ok) throw new Error('Failed to fetch CLI operations');
      return res.json();
    },
    enabled: !!projectId && enabled,
    staleTime: 1000 * 60 * 5,
  });

  return {
    operations: query.data?.operations ?? [],
    ...query,
  };
}

export default useCLIOperations;
