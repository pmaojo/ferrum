import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';

interface GithubAnalysisParams {
  repoUrl: string;
  accessToken?: string;
}

/**
 * Hook to trigger GitHub repository analysis for a project.
 * Keeps graph data fresh by invalidating related queries after completion.
 */
export function useGithubAnalysis(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ repoUrl, accessToken }: GithubAnalysisParams) => {
      const body: Record<string, string> = { repoUrl };
      if (accessToken) body.accessToken = accessToken;
      const res = await apiRequest(
        'POST',
        `/api/v1/projects/${projectId}/analyze-github`,
        body
      );
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [`/api/v1/projects/${projectId}/graph`],
      });
    },
  });
}
