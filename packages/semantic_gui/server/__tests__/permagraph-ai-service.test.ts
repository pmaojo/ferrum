/** @jest-environment node */

import { describe, expect, it, beforeEach, jest } from '@jest/globals';
import type { AxiosInstance } from 'axios';

import {
  PermaGraphAIService,
  PermaGraphAIServiceError,
} from '../services/permagraph-ai-service';

describe('PermaGraphAIService', () => {
  let httpClient: Pick<AxiosInstance, 'post'> & { get?: unknown };
  let service: PermaGraphAIService;

  beforeEach(() => {
    httpClient = {
      post: jest.fn(),
    };

    service = new PermaGraphAIService({ httpClient: httpClient as AxiosInstance });
  });

  it('forwards natural language queries to the PermaGraph API', async () => {
    const mockResponse = { data: { answer: 'Hello world' } };
    (httpClient.post as jest.Mock).mockResolvedValue(mockResponse);

    const result = await service.processNaturalLanguageQuery({
      query: 'test query',
      sessionId: 'session-1',
      context: { project: 'demo' },
      metadata: { requestId: 'req-1' },
    });

    expect(httpClient.post).toHaveBeenCalledWith(
      '/api/v1/nl/query',
      {
        query: 'test query',
        session_id: 'session-1',
        context: { project: 'demo' },
        metadata: { requestId: 'req-1' },
      }
    );
    expect(result).toEqual({ answer: 'Hello world' });
  });

  it('propagates structured errors from the PermaGraph API', async () => {
    const error = Object.assign(new Error('Bad Request'), {
      isAxiosError: true,
      response: { status: 400, data: { message: 'Invalid query' } },
    });

    (httpClient.post as jest.Mock).mockRejectedValue(error);

    await expect(
      service.processNaturalLanguageQuery({ query: 'oops' })
    ).rejects.toEqual(
      new PermaGraphAIServiceError('Invalid query', 400, {
        message: 'Invalid query',
      })
    );
  });

  it('handles network failures gracefully', async () => {
    (httpClient.post as jest.Mock).mockRejectedValue(new Error('Network down'));

    await expect(
      service.performCodeReview({
        files: ['a.ts'],
        context: { project_type: 'ts', architecture_style: 'hex', review_focus: [] },
      })
    ).rejects.toEqual(new PermaGraphAIServiceError('Network down'));
  });

  it('sends semantic completion requests with metadata', async () => {
    const mockResponse = { data: { completions: [] } };
    (httpClient.post as jest.Mock).mockResolvedValue(mockResponse);

    await service.getSemanticCompletions({
      context: { file_path: 'index.ts' },
      partialInput: 'function',
      completionType: 'auto',
      maxSuggestions: 5,
      metadata: { ip: '127.0.0.1' },
    });

    expect(httpClient.post).toHaveBeenCalledWith(
      '/api/v1/nl/completions',
      {
        context: { file_path: 'index.ts' },
        partial_input: 'function',
        completion_type: 'auto',
        max_suggestions: 5,
        metadata: { ip: '127.0.0.1' },
      }
    );
  });
});
