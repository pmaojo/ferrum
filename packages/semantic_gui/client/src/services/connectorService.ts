import type { GraphResponse } from '../../../shared/types/api-responses';
import { validateApiResponse, isGraphNode, isGraphEdge } from '../../../shared/types/type-guards';

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

interface ConnectorInitResponse {
  success: boolean;
  projectId: string;
  templateId: string;
  configPath?: string;
  message?: string;
}

export async function init(
  projectId: string,
  projectPath: string,
  templateId: string
): Promise<ConnectorInitResponse> {
  const res = await fetch(`/api/v1/projects/${projectId}/connector/init`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ projectPath, templateId }),
  });
  if (!res.ok) await handleError(res, 'Failed to initialize connector');
  return res.json() as Promise<ConnectorInitResponse>;
}

interface CommandExecutionResponse {
  success: boolean;
  output: string;
  exitCode: number;
  duration: number;
  command: string;
  args: string[];
  error?: string;
}

export async function execute(
  projectId: string,
  command: string,
  args: string[] = []
): Promise<CommandExecutionResponse> {
  const res = await fetch(`/api/v1/projects/${projectId}/connector/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command, args }),
  });
  if (!res.ok) await handleError(res, 'Failed to execute command');
  return res.json() as Promise<CommandExecutionResponse>;
}

function isGraphData(data: unknown): data is GraphResponse['data'] {
  if (typeof data !== 'object' || data === null) return false;
  const graphData = data as Record<string, unknown>;
  
  return (
    Array.isArray(graphData.nodes) &&
    graphData.nodes.every(isGraphNode) &&
    Array.isArray(graphData.edges) &&
    graphData.edges.every(isGraphEdge)
  );
}

export async function graph(projectId: string): Promise<GraphResponse> {
  const res = await fetch(`/api/v1/projects/${projectId}/connector/graph`);
  if (!res.ok) await handleError(res, 'Failed to generate graph');
  
  const rawData = await res.json();
  const validatedData = validateApiResponse(rawData, isGraphData, 'Invalid graph response data');
  
  return {
    success: true,
    data: validatedData
  };
}

interface ValidationResponse {
  success: boolean;
  isValid: boolean;
  violations: Array<{
    rule: string;
    severity: 'error' | 'warning' | 'info';
    message: string;
    file?: string;
    line?: number;
    column?: number;
  }>;
  summary: {
    totalFiles: number;
    validFiles: number;
    errors: number;
    warnings: number;
  };
}

export async function validate(projectId: string): Promise<ValidationResponse> {
  const res = await fetch(`/api/v1/projects/${projectId}/connector/validate`, {
    method: 'POST',
  });
  if (!res.ok) await handleError(res, 'Failed to validate architecture');
  return res.json() as Promise<ValidationResponse>;
}

export const connectorService = {
  init,
  execute,
  graph,
  validate,
};

export default connectorService;
