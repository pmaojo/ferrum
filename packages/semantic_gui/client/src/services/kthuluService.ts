import type {
  KthuluInitializeResponse,
  KthuluCommand,
  KthuluCommandResponse,
  KthuluValidationResponse,
  KthuluAnalysisResponse,
  GraphResponse,
} from '../../../shared/types/api-responses';
import {
  validateApiResponse,
  isKthuluCommand,
  isValidationResult,
  typedApiResponseFetch
} from '../../../shared/types/type-guards';

interface ErrorResponse {
  error?: string;
  message?: string;
}

async function handleError(
  response: Response,
  defaultMessage: string
): Promise<never> {
  let message = defaultMessage;
  try {
    const data = await response.json() as ErrorResponse;
    message = data.error || data.message || message;
  } catch {
    try {
      const text = await response.text();
      if (text) message = text;
    } catch {
      /* ignore */
    }
  }
  throw new Error(message);
}

export async function initialize(
  projectId: string,
  kthuluPath: string
): Promise<KthuluInitializeResponse> {
  const res = await fetch(`/api/v1/kthulu/projects/${projectId}/initialize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kthuluPath }),
  });
  if (!res.ok) await handleError(res, 'Failed to initialize Kthulu');
  return res.json() as Promise<KthuluInitializeResponse>;
}

export async function getCommands(projectId: string): Promise<KthuluCommand[]> {
  return typedApiResponseFetch(
    `/api/v1/kthulu/projects/${projectId}/commands`,
    (data): data is KthuluCommand[] => Array.isArray(data) && data.every(isKthuluCommand),
    undefined,
    'Failed to fetch commands'
  );
}

export async function executeCommand(
  projectId: string,
  command: string,
  args: string[] = []
): Promise<KthuluCommandResponse> {
  const res = await fetch(
    `/api/v1/kthulu/projects/${projectId}/commands/${command}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ args }),
    }
  );
  if (!res.ok) await handleError(res, 'Command execution failed');
  return res.json() as Promise<KthuluCommandResponse>;
}

export async function importGraph(projectId: string): Promise<GraphResponse> {
  const res = await fetch(`/api/v1/kthulu/projects/${projectId}/graph`, {
    method: 'POST',
  });
  if (!res.ok) await handleError(res, 'Failed to import graph');
  return res.json() as Promise<GraphResponse>;
}

export async function validate(projectId: string): Promise<KthuluValidationResponse> {
  const res = await fetch(`/api/v1/kthulu/projects/${projectId}/validate`, {
    method: 'POST',
  });
  if (!res.ok) await handleError(res, 'Validation failed');
  return res.json() as Promise<KthuluValidationResponse>;
}

export async function analyzeProject(
  projectId: string
): Promise<KthuluAnalysisResponse> {
  const res = await fetch(`/api/v1/kthulu/projects/${projectId}/analyze`, {
    method: 'POST',
  });
  if (!res.ok) await handleError(res, 'Project analysis failed');
  return res.json() as Promise<KthuluAnalysisResponse>;
}

interface ChangeRequest {
  type: string;
  target: string;
  action: string;
  data: Record<string, unknown>;
}

interface ApplyChangesResponse {
  success: boolean;
  appliedChanges: number;
  failedChanges: number;
  results: Array<{
    changeId: string;
    success: boolean;
    error?: string;
  }>;
}

export async function applyChanges(
  projectId: string,
  changes: ChangeRequest[]
): Promise<ApplyChangesResponse> {
  const res = await fetch(`/api/v1/kthulu/projects/${projectId}/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ changes }),
  });
  if (!res.ok) await handleError(res, 'Failed to apply changes');
  return res.json() as Promise<ApplyChangesResponse>;
}

export async function disconnect(projectId: string): Promise<void> {
  const res = await fetch(`/api/v1/kthulu/projects/${projectId}/disconnect`, {
    method: 'POST',
  });
  if (!res.ok) await handleError(res, 'Failed to disconnect');
}

interface ProjectStatus {
  projectId: string;
  status: 'active' | 'inactive' | 'error' | 'initializing';
  lastSync?: string;
  health: 'healthy' | 'degraded' | 'unhealthy';
  metrics: {
    uptime: number;
    lastActivity: string;
    errorCount: number;
  };
  configuration: {
    initialized: boolean;
    configPath?: string;
    version?: string;
  };
}

export async function getStatus(projectId: string): Promise<ProjectStatus> {
  const res = await fetch(`/api/v1/kthulu/projects/${projectId}/status`);
  if (!res.ok) await handleError(res, 'Failed to get status');
  return res.json() as Promise<ProjectStatus>;
}

export const kthuluService = {
  initialize,
  getCommands,
  executeCommand,
  importGraph,
  validate,
  analyzeProject,
  applyChanges,
  disconnect,
  getStatus,
};

export default kthuluService;
