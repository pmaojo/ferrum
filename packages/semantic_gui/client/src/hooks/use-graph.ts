import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import { createLogger } from '../utils/logger';
import type {
  GraphNode,
  GraphEdge,
  InsertGraphNode,
  InsertGraphEdge,
  Project,
  Template,
  ValidationResult,
} from '@shared/schema';

export function useProjects() {
  return useQuery<Project[]>({
    queryKey: ['/api/v1/projects'],
  });
}

export function useProject(projectId: string) {
  return useQuery<Project>({
    queryKey: ['/api/v1/projects', projectId],
    enabled: !!projectId,
  });
}

export function useGraphData(projectId: string) {
  return useQuery<{ nodes: GraphNode[]; edges: GraphEdge[] }>({
    queryKey: [`/api/v1/projects/${projectId}/graph`],
    enabled: !!projectId,
  });
}

export function useGraphRefresh() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      const response = await apiRequest(
        'POST',
        `/api/v1/projects/${projectId}/graph/refresh`
      );
      return response.json();
    },
    onSuccess: (_, projectId) => {
      queryClient.invalidateQueries({
        queryKey: [`/api/v1/projects/${projectId}/graph`],
      });
      queryClient.invalidateQueries({ queryKey: ['/api/v1/projects'] });
    },
  });
}

export function useTemplates() {
  return useQuery<Template[]>({
    queryKey: ['/api/v1/templates'],
  });
}

export function useValidationResults(projectId: string) {
  return useQuery<ValidationResult[]>({
    queryKey: ['/api/v1/projects', projectId, 'validation'],
    enabled: !!projectId,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: {
      name: string;
      description: string;
      templateId: string;
      projectPath: string;
      config?: Record<string, any>;
    }) => {
      const response = await apiRequest(
        'POST',
        '/api/v1/projects/create',
        data
      );
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/v1/projects'] });
    },
  });
}

export function useCreateNode() {
  const queryClient = useQueryClient();
  const logger = createLogger('useCreateNode');

  return useMutation({
    mutationFn: async (data: InsertGraphNode) => {
      logger.debug('Creating graph node', { 
        nodeType: data.type, 
        projectId: data.projectId,
        hasProperties: !!data.properties 
      });
      const response = await apiRequest('POST', '/api/v1/nodes', data);
      logger.debug('Node creation response received', { status: response.status });
      const result = await response.json();
      logger.info('Graph node created successfully', { nodeId: result.id, nodeType: data.type });
      return result;
    },
    onSuccess: (_, variables) => {
      // Force refetch the graph data immediately
      queryClient.refetchQueries({
        queryKey: [`/api/v1/projects/${variables.projectId}/graph`],
      });
      queryClient.invalidateQueries({
        queryKey: ['/api/v1/projects'],
      });
    },
  });
}

export function useUpdateNode() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: Partial<InsertGraphNode>;
    }) => {
      const response = await apiRequest('PUT', `/api/v1/nodes/${id}`, data);
      return response.json();
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({
        queryKey: ['/api/v1/projects', result.projectId, 'graph'],
      });
    },
  });
}

export function useDeleteNode() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await apiRequest('DELETE', `/api/v1/nodes/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/v1/projects'] });
    },
  });
}

export function useCreateEdge() {
  const queryClient = useQueryClient();
  const logger = createLogger('useCreateEdge');

  return useMutation({
    mutationFn: async (edge: Omit<GraphEdge, 'id' | 'createdAt'>) => {
      logger.debug('Creating graph edge', { 
        sourceId: edge.sourceId, 
        targetId: edge.targetId, 
        type: edge.type 
      });
      const response = await fetch('/api/v1/edges', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(edge),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to create edge: ${errorText}`);
      }

      return response.json();
    },
    onSuccess: (result, variables) => {
      // Force refetch the graph data immediately
      queryClient.refetchQueries({
        queryKey: [`/api/v1/projects/${variables.projectId}/graph`],
      });
      queryClient.invalidateQueries({
        queryKey: ['/api/v1/projects'],
      });
      queryClient.invalidateQueries({ queryKey: ['graph-data'] });
    },
  });
}

export function useUpdateEdge() {
  const queryClient = useQueryClient();
  const logger = createLogger('useUpdateEdge');

  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: Partial<GraphEdge>;
    }) => {
      logger.debug('Updating graph edge', { edgeId: id, updateData: Object.keys(data) });
      const response = await fetch(`/api/v1/edges/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to update edge: ${errorText}`);
      }

      const result = await response.json();
      return result;
    },
    onSuccess: (result) => {
      // Invalidate all graph-related queries to ensure fresh data
      queryClient.invalidateQueries({ queryKey: ['/api/v1/projects'] });
      queryClient.invalidateQueries({ queryKey: ['graph-data'] });

      // Also specifically invalidate the project graph query if we have project info
      if (result?.projectId) {
        queryClient.invalidateQueries({
          queryKey: [`/api/v1/projects/${result.projectId}/graph`],
        });
      }

      // Force refetch all queries to ensure immediate update
      queryClient.refetchQueries({
        predicate: (query) => {
          const key = query.queryKey[0] as string;
          return key?.includes('/api/v1/projects/') && key?.includes('/graph');
        },
      });
    },
  });
}

export function useDeleteEdge() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await apiRequest('DELETE', `/api/v1/edges/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/v1/projects'] });
    },
  });
}

export function useAnalyzeCode() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      files,
    }: {
      projectId: string;
      files: FileList;
    }) => {
      const formData = new FormData();
      Array.from(files).forEach((file) => {
        formData.append('files', file);
      });

      const response = await fetch(`/api/v1/projects/${projectId}/analyze`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to analyze code');
      }

      return response.json();
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['/api/v1/projects', variables.projectId, 'graph'],
      });
    },
  });
}

export function useValidateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      const response = await apiRequest(
        'POST',
        `/api/v1/projects/${projectId}/validate`
      );
      return response.json();
    },
    onSuccess: (_, projectId) => {
      queryClient.invalidateQueries({
        queryKey: ['/api/v1/projects', projectId, 'validation'],
      });
    },
  });
}

// @kthulu:extend - Add Kthulu-specific hooks
export function useKthuluInit() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      kthuluPath,
    }: {
      projectId: string;
      kthuluPath: string;
    }) => {
      const response = await apiRequest(
        'POST',
        `/api/v1/projects/${projectId}/kthulu/init`,
        { kthuluPath }
      );
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/v1/projects'] });
    },
  });
}

export function useKthuluCommand() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      command,
      args,
    }: {
      projectId: string;
      command: string;
      args?: string[];
    }) => {
      const response = await apiRequest(
        'POST',
        `/api/v1/projects/${projectId}/kthulu/command`,
        { command, args }
      );
      return response.json();
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [`/api/v1/projects/${variables.projectId}/graph`],
      });
    },
  });
}

export function useKthuluImportGraph() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      const response = await apiRequest(
        'POST',
        `/api/v1/projects/${projectId}/kthulu/import-graph`
      );
      return response.json();
    },
    onSuccess: (_, projectId) => {
      queryClient.invalidateQueries({
        queryKey: [`/api/v1/projects/${projectId}/graph`],
      });
    },
  });
}

export function useKthuluValidate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      const response = await apiRequest(
        'POST',
        `/api/v1/projects/${projectId}/kthulu/validate`
      );
      return response.json();
    },
    onSuccess: (_, projectId) => {
      queryClient.invalidateQueries({
        queryKey: ['/api/v1/projects', projectId, 'validation'],
      });
    },
  });
}

export function useKthuluAnalyze() {
  return useMutation({
    mutationFn: async (projectId: string) => {
      const response = await apiRequest(
        'GET',
        `/api/v1/projects/${projectId}/kthulu/analyze`
      );
      return response.json();
    },
  });
}

export function useKthuluStatus(projectId: string) {
  return useQuery({
    queryKey: [`/api/v1/projects/${projectId}/kthulu/status`],
    enabled: !!projectId,
  });
}

export function useKthuluExportTriples() {
  return useMutation({
    mutationFn: async ({
      projectId,
      format,
    }: {
      projectId: string;
      format: 'turtle' | 'jsonld' | 'json';
    }) => {
      const response = await fetch(
        `/api/v1/projects/${projectId}/kthulu/export-triples?format=${format}`
      );

      if (!response.ok) {
        throw new Error('Failed to export semantic triples');
      }

      // Get filename from Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition');
      const filename =
        contentDisposition?.match(/filename="([^"]+)"/)?.[1] ||
        `export.${format}`;

      const blob = await response.blob();

      // Trigger download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      return { filename, size: blob.size };
    },
  });
}

// @kthulu:extend - PermaGraph integration hooks
export function usePermaGraphInit() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      const response = await apiRequest('POST', '/api/v1/init', {
        projectId,
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/v1/projects'] });
    },
  });
}

export function usePermaGraphSync() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      kthuluPath,
    }: {
      projectId: string;
      kthuluPath?: string;
    }) => {
      const response = await apiRequest('POST', '/api/v1/sync', {
        projectId,
        kthuluPath,
      });
      return response.json();
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [`/api/v1/projects/${variables.projectId}/permagraph/metrics`],
      });
    },
  });
}

export function usePermaGraphAgents() {
  return useQuery({
    queryKey: ['/api/v1/agents', projectId],
    enabled: !!projectId,
  });
}

export function useStartAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ agentId }: { agentId: string }) => {
      const response = await apiRequest(
        'POST',
        `/api/v1/agents/${agentId}/start`,
        { projectId }
      );
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['/api/v1/agents', variables.projectId],
      });
    },
  });
}

export function useStopAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ agentId }: { agentId: string }) => {
      const response = await apiRequest(
        'POST',
        `/api/v1/agents/${agentId}/stop`,
        { projectId }
      );
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['/api/v1/agents', variables.projectId],
      });
    },
  });
}

export function usePermaGraphConfigureAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      agentId,
      config,
    }: {
      projectId: string;
      agentId: string;
      config: any;
    }) => {
      const response = await apiRequest(
        'PUT',
        `/api/v1/agents/${agentId}/config`,
        { projectId, config }
      );
      return response.json();
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['/api/v1/agents', variables.projectId],

      });
    },
  });
}

export function useExplainViolation() {
  return useMutation({
    mutationFn: async ({
      projectId,
      agentId,
      violation,
    }: {
      projectId: string;
      agentId: string;
      violation: any;
    }) => {
      const response = await apiRequest(
        'POST',
        `/api/v1/agents/${agentId}/explain`,
        { projectId, violation }
      );
      return response.json();
    },
  });
}

export function usePermaGraphValidate() {
  return useMutation({
    mutationFn: async (projectId: string) => {
      const response = await apiRequest('POST', '/api/v1/validate', {
        projectId,
      });
      return response.json();
    },
  });
}

export function usePermaGraphSPARQL() {
  return useMutation({
    mutationFn: async ({
      projectId,
      ...body
    }: {
      projectId: string;
      [key: string]: any;
    }) => {
      const response = await apiRequest(
        'POST',
        `/api/v1/projects/${projectId}/permagraph/sparql`,
        body
      );
      return response.json();
    },
  });
}

export function usePermaGraphQueries(projectId: string) {
  return useQuery<{ queries: { id: string; query: string }[] }>({
    queryKey: [`/api/v1/projects/${projectId}/permagraph/queries`],
    enabled: !!projectId,
  });
}

export function usePermaGraphExecuteQuery() {
  return useMutation({
    mutationFn: async ({
      projectId,
      queryId,
      ...body
    }: {
      projectId: string;
      queryId: string;
      [key: string]: any;
    }) => {
      const response = await apiRequest(
        'POST',
        `/api/v1/projects/${projectId}/permagraph/queries/${queryId}/execute`,
        body
      );
      return response.json();
    },
  });
}

export function useSemanticQueries(projectId: string) {
  return useQuery({
    queryKey: [`/api/v1/projects/${projectId}/semantic/queries`],
    enabled: !!projectId,
  });
}

export function useSemanticExecuteQuery() {
  return useMutation({
    mutationFn: async ({
      projectId,
      queryId,
      parameters,
    }: {
      projectId: string;
      queryId: string;
      parameters?: any;
    }) => {
      const response = await apiRequest(
        'POST',
        `/api/v1/projects/${projectId}/semantic/queries/${queryId}`,
        { parameters }
      );
      return response.json();
    },
  });
}

export function usePermaGraphStatus(projectId: string) {
  return useQuery({
    queryKey: ['/api/v1/status', projectId],
    enabled: !!projectId,
  });
}

export function usePermaGraphMetrics(projectId: string) {
  return useQuery({
    queryKey: [`/api/v1/projects/${projectId}/permagraph/metrics`],
    enabled: !!projectId,
  });
}
