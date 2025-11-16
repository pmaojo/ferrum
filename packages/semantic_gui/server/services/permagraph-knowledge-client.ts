import axios, { AxiosError, AxiosInstance } from 'axios';

export interface KnowledgeQueryPayload {
  question: string;
  kg_id?: string;
  tenant_id?: string;
  user_id?: string;
  max_results?: number;
  query_opts?: {
    type?: string;
    filters?: Record<string, unknown>;
    context?: Record<string, unknown>;
  };
}

export interface KnowledgeQueryMetadata {
  [key: string]: unknown;
}

export interface KnowledgeQueryResult {
  queryId?: string;
  resultType?: string;
  title?: string;
  description?: string;
  content?: Record<string, unknown>;
  relevanceScore?: number;
  source?: string;
  metadata?: Record<string, unknown>;
}

export interface KnowledgeQueryResponse {
  results: KnowledgeQueryResult[];
  metadata?: KnowledgeQueryMetadata;
}

export interface KnowledgeServiceHealth {
  ok: boolean;
  status: string;
  details?: Record<string, unknown>;
}

export interface PermaGraphKnowledgeClient {
  queryKnowledge(payload: KnowledgeQueryPayload): Promise<KnowledgeQueryResponse>;
  getHealth(): Promise<KnowledgeServiceHealth>;
}

export class PermaGraphKnowledgeClientError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly details?: unknown,
    public readonly cause?: Error
  ) {
    super(message);
    this.name = 'PermaGraphKnowledgeClientError';
  }
}

export interface PermaGraphKnowledgeClientOptions {
  baseUrl?: string;
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 30_000;

function parseError(error: unknown): PermaGraphKnowledgeClientError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError;
    const status = axiosError.response?.status;
    const details = axiosError.response?.data ?? axiosError.toJSON?.();
    const message =
      (typeof axiosError.response?.data === 'object' &&
        axiosError.response?.data !== null &&
        'message' in axiosError.response?.data &&
        typeof (axiosError.response?.data as Record<string, unknown>).message === 'string'
        ? (axiosError.response?.data as Record<string, string>).message
        : axiosError.message) || 'PermaGraph knowledge request failed';

    return new PermaGraphKnowledgeClientError(message, status, details, error);
  }

  if (error instanceof Error) {
    return new PermaGraphKnowledgeClientError(error.message, undefined, undefined, error);
  }

  return new PermaGraphKnowledgeClientError('Unknown PermaGraph knowledge error');
}

export function createPermaGraphKnowledgeClient(
  options: PermaGraphKnowledgeClientOptions = {}
): PermaGraphKnowledgeClient {
  const baseUrl = (options.baseUrl || process.env.PERMAGRAPH_API_URL || 'http://localhost:8000').replace(/\/$/, '');
  const timeout = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  const httpClient: AxiosInstance = axios.create({
    baseURL: baseUrl,
    timeout,
  });

  return {
    async queryKnowledge(payload) {
      try {
        const response = await httpClient.post('/api/v1/query', payload, {
          headers: {
            'Content-Type': 'application/json',
          },
        });

        const results = Array.isArray(response.data?.results)
          ? (response.data.results as KnowledgeQueryResult[])
          : [];
        const metadata =
          response.data && typeof response.data === 'object' && 'metadata' in response.data
            ? (response.data.metadata as KnowledgeQueryMetadata)
            : undefined;

        if (metadata && typeof metadata === 'object' && 'error' in metadata) {
          throw new PermaGraphKnowledgeClientError(
            typeof metadata.error === 'string'
              ? metadata.error
              : 'PermaGraph knowledge query returned an error',
            undefined,
            metadata
          );
        }

        return { results, metadata } satisfies KnowledgeQueryResponse;
      } catch (error) {
        throw parseError(error);
      }
    },

    async getHealth() {
      try {
        const response = await httpClient.get('/health');
        const ok = response.status >= 200 && response.status < 300;
        return {
          ok,
          status: ok ? 'healthy' : 'unhealthy',
          details: response.data ?? undefined,
        } satisfies KnowledgeServiceHealth;
      } catch (error) {
        const parsed = parseError(error);
        return {
          ok: false,
          status: 'unhealthy',
          details: {
            message: parsed.message,
            statusCode: parsed.statusCode,
          },
        } satisfies KnowledgeServiceHealth;
      }
    },
  };
}

