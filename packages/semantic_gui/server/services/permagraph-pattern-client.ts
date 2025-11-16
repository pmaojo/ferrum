import axios, { AxiosError, AxiosInstance } from 'axios';

import {
  AuthPattern,
  RequirementChain,
  ServicePattern,
} from './pattern-models';

export interface PatternExportRequest {
  strategy: string;
  metadata: Record<string, unknown>;
  pageToken?: string;
  pageSize?: number;
}

export interface RateLimitInfo {
  limit?: number;
  remaining?: number;
  reset?: Date;
  retryAfterMs?: number;
}

export interface PatternExportResponse {
  patterns: (AuthPattern | ServicePattern | RequirementChain)[];
  nextPageToken?: string;
  rateLimit?: RateLimitInfo;
}

export interface PermaGraphPatternClient {
  exportPatterns(request: PatternExportRequest): Promise<PatternExportResponse>;
}

export class PermaGraphRateLimitError extends Error {
  constructor(
    message: string,
    public readonly retryAfterMs: number | undefined,
    public readonly cause?: Error
  ) {
    super(message);
    this.name = 'PermaGraphRateLimitError';
  }
}

export interface PermaGraphPatternClientOptions {
  baseUrl?: string;
  timeoutMs?: number;
  pageSize?: number;
}

const DEFAULT_TIMEOUT_MS = 30_000;

function parseRetryAfter(retryAfter?: string): number | undefined {
  if (!retryAfter) {
    return undefined;
  }

  const numeric = Number(retryAfter);
  if (!Number.isNaN(numeric)) {
    return Math.max(0, numeric * 1000);
  }

  const parsedDate = Date.parse(retryAfter);
  if (!Number.isNaN(parsedDate)) {
    return Math.max(0, parsedDate - Date.now());
  }

  return undefined;
}

function extractRateLimitInfo(headers: Record<string, unknown>): RateLimitInfo | undefined {
  const limitHeader = headers['x-ratelimit-limit'];
  const remainingHeader = headers['x-ratelimit-remaining'];
  const resetHeader = headers['x-ratelimit-reset'];
  const retryAfterHeader = headers['retry-after'];

  if (
    limitHeader === undefined &&
    remainingHeader === undefined &&
    resetHeader === undefined &&
    retryAfterHeader === undefined
  ) {
    return undefined;
  }

  const limit = typeof limitHeader === 'string' ? Number(limitHeader) : undefined;
  const remaining =
    typeof remainingHeader === 'string' ? Number(remainingHeader) : undefined;
  const resetDate =
    typeof resetHeader === 'string' && !Number.isNaN(Date.parse(resetHeader))
      ? new Date(resetHeader)
      : undefined;
  const retryAfterMs =
    typeof retryAfterHeader === 'string'
      ? parseRetryAfter(retryAfterHeader)
      : undefined;

  return {
    limit: Number.isFinite(limit) ? limit : undefined,
    remaining: Number.isFinite(remaining) ? remaining : undefined,
    reset: resetDate,
    retryAfterMs,
  };
}

export function createPermaGraphPatternClient(
  options: PermaGraphPatternClientOptions = {}
): PermaGraphPatternClient {
  const baseUrl = (
    options.baseUrl || process.env.PERMAGRAPH_API_URL || 'http://localhost:8000'
  ).replace(/\/$/, '');
  const timeout = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  const httpClient: AxiosInstance = axios.create({
    baseURL: baseUrl,
    timeout,
  });

  return {
    async exportPatterns({ strategy, metadata, pageToken, pageSize }: PatternExportRequest) {
      try {
        const response = await httpClient.post(
          `/api/patterns/export/${encodeURIComponent(strategy)}`,
          {
            strategy,
            metadata,
          },
          {
            params: {
              page_token: pageToken,
              page_size: pageSize,
            },
          }
        );

        const rateLimit = extractRateLimitInfo(response.headers ?? {});
        const data = response.data ?? {};

        return {
          patterns: Array.isArray(data.patterns) ? data.patterns : [],
          nextPageToken:
            typeof data.nextPageToken === 'string'
              ? data.nextPageToken
              : typeof data.next_page_token === 'string'
                ? data.next_page_token
                : undefined,
          rateLimit,
        } satisfies PatternExportResponse;
      } catch (error) {
        if (axios.isAxiosError(error)) {
          const axiosError = error as AxiosError;
          if (axiosError.response?.status === 429) {
            const retryAfterHeader = axiosError.response.headers?.['retry-after'];
            const retryAfterMs =
              typeof retryAfterHeader === 'string'
                ? parseRetryAfter(retryAfterHeader)
                : undefined;
            throw new PermaGraphRateLimitError(
              'PermaGraph rate limit exceeded',
              retryAfterMs,
              error
            );
          }
        }

        throw error;
      }
    },
  };
}

