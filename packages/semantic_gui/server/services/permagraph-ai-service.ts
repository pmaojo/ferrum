import axios, { type AxiosInstance, isAxiosError } from 'axios';

type SerializableRecord = Record<string, unknown>;

export interface NaturalLanguageQueryParams {
  query: string;
  sessionId?: string;
  context?: SerializableRecord;
  metadata?: SerializableRecord;
}

export interface QuerySuggestionParams {
  partialQuery: string;
  metadata?: SerializableRecord;
}

export interface CodeReviewParams {
  files: string[];
  context: SerializableRecord;
  metadata?: SerializableRecord;
}

export interface SemanticCompletionParams {
  context: SerializableRecord;
  partialInput: string;
  completionType: string;
  maxSuggestions: number;
  metadata?: SerializableRecord;
}

export interface ApplySuggestionParams {
  filePath: string;
  lineNumber?: number;
  suggestedFix: string;
  metadata?: SerializableRecord;
}

export interface PermaGraphAIAdapter {
  processNaturalLanguageQuery(
    params: NaturalLanguageQueryParams
  ): Promise<unknown>;
  getQuerySuggestions(params: QuerySuggestionParams): Promise<unknown>;
  performCodeReview(params: CodeReviewParams): Promise<unknown>;
  getSemanticCompletions(params: SemanticCompletionParams): Promise<unknown>;
  detectAntiPatterns(metadata?: SerializableRecord): Promise<unknown>;
  applySuggestion(params: ApplySuggestionParams): Promise<unknown>;
}

export interface PermaGraphAIServiceConfig {
  baseURL?: string;
  apiKey?: string;
  httpClient?: AxiosInstance;
}

export class PermaGraphAIServiceError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly data?: unknown
  ) {
    super(message);
    this.name = 'PermaGraphAIServiceError';
  }
}

export class PermaGraphAIService implements PermaGraphAIAdapter {
  private readonly httpClient: AxiosInstance;

  constructor(config: PermaGraphAIServiceConfig = {}) {
    this.httpClient =
      config.httpClient ??
      axios.create({
        baseURL:
          config.baseURL || process.env.PERMAGRAPH_API_URL || 'http://localhost:8000',
        headers: {
          'Content-Type': 'application/json',
          ...(config.apiKey ? { Authorization: `Bearer ${config.apiKey}` } : {}),
        },
      });
  }

  async processNaturalLanguageQuery({
    query,
    sessionId,
    context,
    metadata,
  }: NaturalLanguageQueryParams): Promise<unknown> {
    return this.sendRequest(() =>
      this.httpClient.post('/api/v1/nl/query', this.compactPayload({
        query,
        session_id: sessionId,
        context,
        metadata,
      }))
    );
  }

  async getQuerySuggestions({
    partialQuery,
    metadata,
  }: QuerySuggestionParams): Promise<unknown> {
    return this.sendRequest(() =>
      this.httpClient.post('/api/v1/nl/suggestions', this.compactPayload({
        partial_query: partialQuery,
        metadata,
      }))
    );
  }

  async performCodeReview({
    files,
    context,
    metadata,
  }: CodeReviewParams): Promise<unknown> {
    return this.sendRequest(() =>
      this.httpClient.post('/api/v1/nl/code-review', this.compactPayload({
        files,
        context,
        metadata,
      }))
    );
  }

  async getSemanticCompletions({
    context,
    partialInput,
    completionType,
    maxSuggestions,
    metadata,
  }: SemanticCompletionParams): Promise<unknown> {
    return this.sendRequest(() =>
      this.httpClient.post('/api/v1/nl/completions', this.compactPayload({
        context,
        partial_input: partialInput,
        completion_type: completionType,
        max_suggestions: maxSuggestions,
        metadata,
      }))
    );
  }

  async detectAntiPatterns(metadata?: SerializableRecord): Promise<unknown> {
    return this.sendRequest(() =>
      this.httpClient.post('/api/v1/nl/anti-patterns', this.compactPayload({
        metadata,
      }))
    );
  }

  async applySuggestion({
    filePath,
    lineNumber,
    suggestedFix,
    metadata,
  }: ApplySuggestionParams): Promise<unknown> {
    return this.sendRequest(() =>
      this.httpClient.post('/api/v1/nl/apply-suggestion', this.compactPayload({
        file_path: filePath,
        line_number: lineNumber,
        suggested_fix: suggestedFix,
        metadata,
      }))
    );
  }

  private async sendRequest<T>(executor: () => Promise<{ data: T }>): Promise<T> {
    try {
      const { data } = await executor();
      return data;
    } catch (error) {
      throw this.normalizeError(error);
    }
  }

  private normalizeError(error: unknown): PermaGraphAIServiceError {
    if (isAxiosError(error)) {
      const status = error.response?.status;
      const responseData = error.response?.data;
      const message =
        error.response?.data?.message ||
        error.message ||
        'PermaGraph AI request failed';
      return new PermaGraphAIServiceError(message, status, responseData);
    }

    if (error instanceof Error) {
      return new PermaGraphAIServiceError(error.message);
    }

    return new PermaGraphAIServiceError('An unknown error occurred while contacting PermaGraph');
  }

  private compactPayload(payload: SerializableRecord): SerializableRecord {
    return Object.fromEntries(
      Object.entries(payload).filter(([, value]) =>
        value !== undefined && value !== null
      )
    );
  }
}

export const createPermaGraphAIService = (
  config?: PermaGraphAIServiceConfig
): PermaGraphAIAdapter => new PermaGraphAIService(config);

