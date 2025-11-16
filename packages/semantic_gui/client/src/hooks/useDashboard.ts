import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query';
import { useToast } from '@/hooks/use-toast';

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'stopped';
  url: string;
  port: number;
  framework?: string;
  description: string;
  lastCheck: string;
  responseTime?: number;
  version?: string;
  dependencies?: string[];
}

interface Framework {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'error';
  description: string;
  services: string[];
  composeFile: string;
  features: {
    name: string;
    status: 'working' | 'partial' | 'planned' | 'broken';
    description: string;
  }[];
}

interface Project {
  id: string;
  name: string;
  framework: string;
  status: 'active' | 'inactive' | 'archived';
  lastModified: string;
  description: string;
  path: string;
  gitBranch?: string;
  nodeCount?: number;
  edgeCount?: number;
}

interface DashboardOverview {
  frameworks: Framework[];
  services: ServiceStatus[];
  activeFramework: string | null;
  timestamp: string;
}

export function useDashboardOverview(): UseQueryResult<DashboardOverview> {
  return useQuery<DashboardOverview>({
    queryKey: ['dashboard', 'overview'],
    queryFn: async () => {
      const response = await fetch('/api/v1/dashboard/overview');
      if (!response.ok) {
        throw new Error('Failed to fetch dashboard overview');
      }
      const data = await response.json();
      return data.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

export function useServices(): UseQueryResult<ServiceStatus[]> {
  return useQuery<ServiceStatus[]>({
    queryKey: ['dashboard', 'services'],
    queryFn: async () => {
      const response = await fetch('/api/v1/dashboard/services');
      if (!response.ok) {
        throw new Error('Failed to fetch services');
      }
      const data = await response.json();
      return data.data;
    },
    refetchInterval: 15000, // Refresh every 15 seconds
  });
}

export function useFrameworks(): UseQueryResult<Framework[]> {
  return useQuery<Framework[]>({
    queryKey: ['dashboard', 'frameworks'],
    queryFn: async () => {
      const response = await fetch('/api/v1/dashboard/frameworks');
      if (!response.ok) {
        throw new Error('Failed to fetch frameworks');
      }
      const data = await response.json();
      return data.data;
    },
  });
}

export function useDashboardProjects(framework?: string): UseQueryResult<Project[]> {
  return useQuery<Project[]>({
    queryKey: ['dashboard', 'projects', framework],
    queryFn: async () => {
      const url = framework 
        ? `/api/v1/dashboard/projects?framework=${framework}`
        : '/api/v1/dashboard/projects';
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Failed to fetch projects');
      }
      const data = await response.json();
      return data.data;
    },
  });
}

export function useFrameworkSwitch(): UseMutationResult<any, Error, string> {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (frameworkId: string) => {
      const response = await fetch('/api/v1/dashboard/frameworks/switch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ frameworkId }),
      });

      if (!response.ok) {
        throw new Error('Failed to switch framework');
      }

      return response.json();
    },
    onSuccess: (data) => {
      // Invalidate and refetch dashboard data
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      
      toast({
        title: 'Framework Switched',
        description: `Switched to ${data.data.framework.name} development environment`,
      });
    },
    onError: (error) => {
      toast({
        title: 'Error',
        description: 'Failed to switch framework',
        variant: 'destructive',
      });
    },
  });
}

export function useServiceAction(): UseMutationResult<any, Error, { serviceName: string; action: 'start' | 'stop' | 'restart' }> {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ serviceName, action }: { serviceName: string; action: 'start' | 'stop' | 'restart' }) => {
      const response = await fetch(`/api/v1/dashboard/services/${serviceName}/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action }),
      });

      if (!response.ok) {
        throw new Error(`Failed to ${action} service`);
      }

      return response.json();
    },
    onSuccess: (data, variables) => {
      // Invalidate and refetch services data
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'services'] });
      
      toast({
        title: 'Service Action Complete',
        description: `${variables.serviceName} ${variables.action}ed successfully`,
      });
    },
    onError: (error, variables) => {
      toast({
        title: 'Error',
        description: `Failed to ${variables.action} ${variables.serviceName}`,
        variant: 'destructive',
      });
    },
  });
}

export function useCreateProject(): UseMutationResult<any, Error, { name: string; framework: string; description?: string }> {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ name, framework, description }: { name: string; framework: string; description?: string }) => {
      const response = await fetch('/api/v1/dashboard/projects', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, framework, description }),
      });

      if (!response.ok) {
        throw new Error('Failed to create project');
      }

      return response.json();
    },
    onSuccess: (data) => {
      // Invalidate and refetch projects data
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'projects'] });
      
      toast({
        title: 'Project Created',
        description: `Created new project: ${data.data.name}`,
      });
    },
    onError: (error) => {
      toast({
        title: 'Error',
        description: 'Failed to create project',
        variant: 'destructive',
      });
    },
  });
}

export function useServiceHealth(serviceName: string): UseQueryResult<any> {
  return useQuery({
    queryKey: ['dashboard', 'service-health', serviceName],
    queryFn: async () => {
      const response = await fetch(`/api/v1/dashboard/services/${serviceName}/health`);
      if (!response.ok) {
        throw new Error('Failed to check service health');
      }
      const data = await response.json();
      return data.data;
    },
    refetchInterval: 10000, // Check health every 10 seconds
  });
}