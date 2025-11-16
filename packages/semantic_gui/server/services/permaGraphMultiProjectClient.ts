import { URLSearchParams } from 'node:url';

export interface ListProjectsParams {
  tenant_id?: string;
  status?: string;
  owner?: string;
  tags?: string[];
}

export interface CreateProjectPayload {
  name: string;
  description?: string;
  template_id?: string;
  owner?: string;
  tenant_id?: string;
  tags?: string[];
}

export interface CloneProjectPayload {
  source_project_id: string;
  name: string;
  description?: string;
  owner?: string;
  tenant_id?: string;
}

export interface UpdateProjectPayload {
  name?: string;
  description?: string;
  tags?: string[];
  status?: string;
}

export interface BulkOperationPayload {
  operation: string;
  project_ids: string[];
  options?: Record<string, unknown>;
}

export interface ProjectActivityParams {
  limit?: number;
  offset?: number;
}

export interface ProjectActivityResponse {
  project_id?: string;
  activity: any[];
  total: number;
}

export interface CreateTemplatePayload {
  name: string;
  description?: string;
  category?: string;
  ontology_content?: string;
  metadata?: Record<string, unknown>;
}

export class PermaGraphClientError extends Error {
  public readonly statusCode: number;
  public readonly details?: unknown;

  constructor(message: string, statusCode: number, details?: unknown) {
    super(message);
    this.name = 'PermaGraphClientError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

export interface MultiProjectClient {
  listProjects(params: ListProjectsParams): Promise<any[]>;
  getProject(projectId: string): Promise<any>;
  getProjectStatistics(projectId: string): Promise<any>;
  createProject(payload: CreateProjectPayload): Promise<any>;
  cloneProject(payload: CloneProjectPayload): Promise<any>;
  updateProject(projectId: string, payload: UpdateProjectPayload): Promise<any>;
  archiveProject(projectId: string): Promise<void>;
  deleteProject(projectId: string, force?: boolean): Promise<void>;
  compareProjects(projectA: string, projectB: string): Promise<any>;
  bulkOperation(payload: BulkOperationPayload): Promise<any>;
  listTemplates(): Promise<any[]>;
  createTemplate(payload: CreateTemplatePayload): Promise<any>;
  listTenantProjects(
    tenantId: string,
    params?: { status?: string }
  ): Promise<any[]>;
  getProjectActivity(
    projectId: string,
    params?: ProjectActivityParams
  ): Promise<ProjectActivityResponse>;
}

export function createPermaGraphMultiProjectClient(
  baseUrl: string = process.env.PERMAGRAPH_API_URL || 'http://localhost:8000'
): MultiProjectClient {
  const normalizedBaseUrl = baseUrl.replace(/\/?$/, '');

  async function parseResponse<T>(response: Response): Promise<T> {
    const text = await response.text();
    let data: unknown;

    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = text;
      }
    }

    if (!response.ok) {
      const errorMessage =
        (data && typeof data === 'object' && 'error' in data &&
        typeof (data as Record<string, unknown>).error === 'string'
          ? (data as Record<string, string>).error
          : data && typeof data === 'object' && 'message' in data &&
              typeof (data as Record<string, unknown>).message === 'string'
            ? (data as Record<string, string>).message
            : response.statusText) || 'PermaGraph request failed';

      throw new PermaGraphClientError(errorMessage, response.status, data);
    }

    return data as T;
  }

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${normalizedBaseUrl}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers as Record<string, string> | undefined),
      },
    });

    return parseResponse<T>(response);
  }

  return {
    async listProjects(params) {
      const search = new URLSearchParams();
      if (params.tenant_id) search.set('tenant_id', params.tenant_id);
      if (params.status) search.set('status', params.status);
      if (params.owner) search.set('owner', params.owner);
      if (params.tags?.length) search.set('tags', params.tags.join(','));

      const query = search.toString();
      const path = `/api/v1/projects${query ? `?${query}` : ''}`;
      return request<any[]>(path, { method: 'GET' });
    },

    async getProject(projectId) {
      return request<any>(`/api/v1/projects/${encodeURIComponent(projectId)}`, {
        method: 'GET',
      });
    },

    async getProjectStatistics(projectId) {
      return request<any>(
        `/api/v1/projects/${encodeURIComponent(projectId)}/statistics`,
        { method: 'GET' }
      );
    },

    async createProject(payload) {
      return request<any>(`/api/v1/projects`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    async cloneProject({ source_project_id, ...rest }) {
      return request<any>(
        `/api/v1/projects/${encodeURIComponent(source_project_id)}/clone`,
        {
          method: 'POST',
          body: JSON.stringify(rest),
        }
      );
    },

    async updateProject(projectId, payload) {
      return request<any>(`/api/v1/projects/${encodeURIComponent(projectId)}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });
    },

    async archiveProject(projectId) {
      await request(`/api/v1/projects/${encodeURIComponent(projectId)}/archive`, {
        method: 'POST',
      });
    },

    async deleteProject(projectId, force) {
      const params = new URLSearchParams();
      if (force) params.set('force', 'true');
      const query = params.toString();
      await request(
        `/api/v1/projects/${encodeURIComponent(projectId)}${
          query ? `?${query}` : ''
        }`,
        { method: 'DELETE' }
      );
    },

    async compareProjects(projectA, projectB) {
      return request<any>(`/api/v1/projects/compare`, {
        method: 'POST',
        body: JSON.stringify({ project_a: projectA, project_b: projectB }),
      });
    },

    async bulkOperation(payload) {
      return request<any>(`/api/v1/projects/bulk`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    async getProjectActivity(projectId, params = {}) {
      const search = new URLSearchParams();
      if (typeof params.limit === 'number' && !Number.isNaN(params.limit)) {
        search.set('limit', params.limit.toString());
      }
      if (typeof params.offset === 'number' && !Number.isNaN(params.offset)) {
        search.set('offset', params.offset.toString());
      }

      const query = search.toString();
      const path = `/api/v1/projects/${encodeURIComponent(projectId)}/activity${
        query ? `?${query}` : ''
      }`;

      return request<ProjectActivityResponse>(path, { method: 'GET' });
    },

    async listTemplates() {
      return request<any[]>(`/api/v1/projects/templates`, { method: 'GET' });
    },

    async createTemplate(payload) {
      return request<any>(`/api/v1/projects/templates`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    async listTenantProjects(tenantId, params = {}) {
      const search = new URLSearchParams();
      if (params.status) search.set('status', params.status);
      const query = search.toString();
      const path = `/api/v1/tenants/${encodeURIComponent(tenantId)}/projects${
        query ? `?${query}` : ''
      }`;
      return request<any[]>(path, {
        method: 'GET',
      });
    },
  };
}
