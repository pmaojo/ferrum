export interface ExportOptions {
  includeMetadata?: boolean;
  includeValidation?: boolean;
  includeProvenance?: boolean;
  compressOutput?: boolean;
  [key: string]: unknown;
}

export interface ImportOptionParams {
  mergeStrategy?: string;
  validateBefore?: boolean;
  validateAfter?: boolean;
  createBackup?: boolean;
  resolveConflicts?: boolean;
  dryRun?: boolean;
  [key: string]: unknown;
}

export interface ImportOptions {
  file?: File;
  url?: string;
  options?: ImportOptionParams;
}

export interface ExportResponse {
  success?: boolean;
  download_url?: string;
  content?: string;
  mimeType?: string;
  size_bytes?: number;
  metadata?: Record<string, unknown>;
  error?: string;
  [key: string]: unknown;
}

export interface ImportResponse {
  success?: boolean;
  triples_imported?: number;
  triples_updated?: number;
  triples_removed?: number;
  validation_passed?: boolean;
  validation_warnings?: string[];
  errors?: string[];
  [key: string]: unknown;
}

async function handleError(
  response: Response,
  defaultMessage: string,
): Promise<never> {
  let message = defaultMessage;
  try {
    const data = await response.json();
    message = (data as any).error || (data as any).message || message;
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

export async function exportStandards(
  projectId: string,
  format: string,
  options: ExportOptions = {},
): Promise<ExportResponse> {
  const res = await fetch('/api/v1/standards/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ projectId, format, options }),
  });
  if (!res.ok) await handleError(res, 'Failed to export standards data');
  return res.json();
}

export async function importStandards(
  projectId: string,
  format: string,
  data: ImportOptions,
): Promise<ImportResponse> {
  const formData = new FormData();
  formData.append('projectId', projectId);
  formData.append('format', format);
  if (data.options) formData.append('options', JSON.stringify(data.options));
  if (data.file) formData.append('file', data.file);
  if (data.url) formData.append('url', data.url);

  const res = await fetch('/api/v1/standards/import', {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) await handleError(res, 'Failed to import standards data');
  return res.json();
}

export const standardsService = {
  exportStandards,
  importStandards,
};

export default standardsService;

