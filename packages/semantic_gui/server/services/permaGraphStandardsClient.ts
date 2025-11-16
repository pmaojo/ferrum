import { basename } from 'node:path';
import { readFile } from 'node:fs/promises';

export interface ExportOntologyRequest {
  projectId: string;
  format: string;
  options?: Record<string, unknown>;
}

export interface ImportOntologyFromFileRequest {
  projectId: string;
  format: string;
  filePath: string;
  options?: Record<string, unknown>;
}

export interface ImportOntologyFromUrlRequest {
  projectId: string;
  format: string;
  url: string;
  options?: Record<string, unknown>;
}

export interface ExportShapesRequest {
  projectId: string;
}

export type ImportResult = Record<string, unknown>;

export class PermaGraphStandardsClientError extends Error {
  public readonly statusCode: number;
  public readonly details?: unknown;

  constructor(message: string, statusCode: number, details?: unknown) {
    super(message);
    this.name = 'PermaGraphStandardsClientError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

export interface PermaGraphStandardsClient {
  exportOntology(request: ExportOntologyRequest): Promise<Response>;
  importOntologyFromFile(request: ImportOntologyFromFileRequest): Promise<ImportResult>;
  importOntologyFromUrl(request: ImportOntologyFromUrlRequest): Promise<ImportResult>;
  exportShapes(request: ExportShapesRequest): Promise<Response>;
}

interface ClientConfig {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
}

function resolveBaseUrl(baseUrl?: string): string {
  const url =
    baseUrl || process.env.PERMAGRAPH_API_URL || 'http://localhost:8000';
  return url.replace(/\/?$/, '');
}

async function parseErrorResponse(response: Response): Promise<{
  message: string;
  details?: unknown;
}> {
  let details: unknown;
  let message = response.statusText || 'PermaGraph request failed';

  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    try {
      details = await response.json();
      if (
        details &&
        typeof details === 'object' &&
        'error' in details &&
        typeof (details as Record<string, unknown>).error === 'string'
      ) {
        message = (details as Record<string, string>).error;
      } else if (
        details &&
        typeof details === 'object' &&
        'message' in details &&
        typeof (details as Record<string, unknown>).message === 'string'
      ) {
        message = (details as Record<string, string>).message;
      }
    } catch {
      /* ignore JSON parse errors */
    }
  } else {
    try {
      const text = await response.text();
      if (text) {
        details = text;
        message = text;
      }
    } catch {
      /* ignore */
    }
  }

  return { message, details };
}

export function createPermaGraphStandardsClient(
  config: ClientConfig = {},
): PermaGraphStandardsClient {
  const baseUrl = resolveBaseUrl(config.baseUrl);
  const fetchImpl = config.fetchImpl ?? fetch;

  async function ensureOk(response: Response): Promise<Response> {
    if (!response.ok) {
      const { message, details } = await parseErrorResponse(response);
      throw new PermaGraphStandardsClientError(
        message,
        response.status,
        details,
      );
    }

    return response;
  }

  async function ensureJson<T>(response: Response): Promise<T> {
    const okResponse = await ensureOk(response);
    const contentType = okResponse.headers.get('content-type') || '';

    if (!contentType.includes('application/json')) {
      throw new PermaGraphStandardsClientError(
        'Unexpected response content type from PermaGraph',
        okResponse.status,
      );
    }

    return (await okResponse.json()) as T;
  }

  return {
    async exportOntology({ projectId, format, options }): Promise<Response> {
      const response = await fetchImpl(
        `${baseUrl}/api/v1/projects/${encodeURIComponent(
          projectId,
        )}/standards/export`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: projectId,
            export_format: format,
            options: options ?? {},
          }),
        },
      );

      return ensureOk(response);
    },

    async importOntologyFromFile({
      projectId,
      format,
      filePath,
      options,
    }): Promise<ImportResult> {
      const fileBuffer = await readFile(filePath);
      const file = new File([fileBuffer], basename(filePath));
      const formData = new FormData();

      formData.append('project_id', projectId);
      formData.append('import_format', format);
      formData.append('file', file);
      if (options && Object.keys(options).length > 0) {
        formData.append('options', JSON.stringify(options));
      }

      const response = await fetchImpl(
        `${baseUrl}/api/v1/projects/${encodeURIComponent(
          projectId,
        )}/standards/import/file`,
        {
          method: 'POST',
          body: formData,
        },
      );

      return ensureJson<ImportResult>(response);
    },

    async importOntologyFromUrl({
      projectId,
      format,
      url,
      options,
    }): Promise<ImportResult> {
      const response = await fetchImpl(
        `${baseUrl}/api/v1/projects/${encodeURIComponent(
          projectId,
        )}/standards/import/url`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: projectId,
            import_format: format,
            source_url: url,
            options: options ?? {},
          }),
        },
      );

      return ensureJson<ImportResult>(response);
    },

    async exportShapes({ projectId }): Promise<Response> {
      const response = await fetchImpl(
        `${baseUrl}/api/v1/projects/${encodeURIComponent(
          projectId,
        )}/standards/shapes/export`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_id: projectId }),
        },
      );

      return ensureOk(response);
    },
  };
}

export default createPermaGraphStandardsClient;
