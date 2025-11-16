// Project management service functions for confirm nodes, scoring, export, and import operations

import type { Project } from '../../../shared/types/api-responses';

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

export async function confirmNodes(
  projectId: string,
  confirmedFiles: string[]
): Promise<{ message: string; confirmedNodes: number }> {
  const res = await fetch(`/api/v1/projects/${projectId}/confirm-nodes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirmedFiles }),
  });
  if (!res.ok) await handleError(res, 'Failed to confirm nodes');
  return res.json();
}

export async function getProjectScore(projectId: string): Promise<{
  score: number;
  compliance: number;
  penalties: number;
  rewards: number;
  totalNodes: number;
  totalEdges: number;
}> {
  const res = await fetch(`/api/v1/projects/${projectId}/score`);
  if (!res.ok) await handleError(res, 'Failed to get project score');
  return res.json();
}

export async function exportProject(
  projectId: string
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(`/api/v1/projects/${projectId}/export`);
  if (!res.ok) await handleError(res, 'Failed to export project');
  const blob = await res.blob();
  const disposition = res.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^";]+)"?/);
  const filename = match ? match[1] : `project-${projectId}.json`;
  return { blob, filename };
}

interface ImportProjectResponse {
  success: boolean;
  project: Project;
  message?: string;
  warnings?: string[];
}

export async function importProject(file: File): Promise<ImportProjectResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch('/api/v1/projects/import', {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) await handleError(res, 'Failed to import project');
  return res.json() as Promise<ImportProjectResponse>;
}

export const projectManagementService = {
  confirmNodes,
  getProjectScore,
  exportProject,
  importProject,
};

export default projectManagementService;
