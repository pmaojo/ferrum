import type { Request, Response } from 'express';
import express from 'express';
import { z, ZodError } from 'zod';

import { authMiddleware } from '../middleware/auth';
import { requireRole } from '../middleware/requireRole';
import {
  createPermaGraphAIService,
  PermaGraphAIServiceError,
  type PermaGraphAIAdapter,
} from '../services/permagraph-ai-service';

const naturalLanguageQuerySchema = z.object({
  query: z.string().min(1),
  session_id: z.string().optional(),
  context: z
    .object({
      timestamp: z.string().optional(),
      source: z.string().optional(),
    })
    .optional(),
});

const querySuggestionSchema = z.object({
  partial_query: z.string().min(1),
});

const codeReviewSchema = z.object({
  files: z.array(z.string()),
  context: z.object({
    project_type: z.string(),
    architecture_style: z.string(),
    review_focus: z.array(z.string()),
  }),
});

const semanticCompletionSchema = z.object({
  context: z.object({
    file_path: z.string(),
    cursor_line: z.number(),
    cursor_column: z.number(),
    current_line: z.string(),
    preceding_lines: z.array(z.string()),
    following_lines: z.array(z.string()),
    project_type: z.string(),
    language: z.string(),
    module_name: z.string().optional(),
    component_type: z.string().optional(),
  }),
  partial_input: z.string(),
  completion_type: z.string(),
  max_suggestions: z.number().default(10),
});

const applySuggestionSchema = z.object({
  file_path: z.string(),
  line_number: z.number().optional(),
  suggested_fix: z.string(),
});

type SerializableRecord = Record<string, unknown>;

const createSessionMetadata = (
  req: Request,
  explicitSessionId?: string
): SerializableRecord | undefined => {
  const metadata: SerializableRecord = {
    sessionId: explicitSessionId ?? (req as unknown as { sessionID?: string }).sessionID,
    requestId: req.get('x-request-id'),
    traceId: (req as unknown as { traceId?: string }).traceId ?? req.get('x-trace-id'),
    userAgent: req.get('user-agent'),
    ip: req.ip,
  };

  const filtered = Object.fromEntries(
    Object.entries(metadata).filter(([, value]) =>
      value !== undefined && value !== null && value !== ''
    )
  );

  return Object.keys(filtered).length > 0 ? filtered : undefined;
};

const handleRouteError = (
  res: Response,
  error: unknown,
  fallbackMessage: string
): void => {
  if (error instanceof ZodError) {
    res.status(400).json({
      error: 'Validation error',
      details: error.flatten(),
    });
    return;
  }

  if (error instanceof PermaGraphAIServiceError) {
    res.status(error.status ?? 502).json({
      error: fallbackMessage,
      details: error.message,
      cause: error.data,
    });
    return;
  }

  const message = error instanceof Error ? error.message : 'Unknown error';
  res.status(500).json({ error: fallbackMessage, details: message });
};

export const createAIRouter = (
  aiService: PermaGraphAIAdapter = createPermaGraphAIService()
) => {
  const router = express.Router();

  router.post('/natural-language-query', async (req: Request, res: Response) => {
    try {
      const { query, session_id, context } = naturalLanguageQuerySchema.parse(
        req.body
      );

      const metadata = createSessionMetadata(req, session_id);
      const response = await aiService.processNaturalLanguageQuery({
        query,
        sessionId: session_id,
        context,
        metadata,
      });

      res.json(response);
    } catch (error) {
      console.error('Natural language query error:', error);
      handleRouteError(res, error, 'Failed to process natural language query');
    }
  });

  router.post('/query-suggestions', async (req: Request, res: Response) => {
    try {
      const { partial_query } = querySuggestionSchema.parse(req.body);
      const metadata = createSessionMetadata(req);
      const response = await aiService.getQuerySuggestions({
        partialQuery: partial_query,
        metadata,
      });

      res.json(response);
    } catch (error) {
      console.error('Query suggestions error:', error);
      handleRouteError(res, error, 'Failed to get query suggestions');
    }
  });

  router.post('/code-review', async (req: Request, res: Response) => {
    try {
      const { files, context } = codeReviewSchema.parse(req.body);
      const metadata = createSessionMetadata(req);
      const response = await aiService.performCodeReview({
        files,
        context,
        metadata,
      });

      res.json(response);
    } catch (error) {
      console.error('Code review error:', error);
      handleRouteError(res, error, 'Failed to perform code review');
    }
  });

  router.post('/semantic-completion', async (req: Request, res: Response) => {
    try {
      const { context, partial_input, completion_type, max_suggestions } =
        semanticCompletionSchema.parse(req.body);
      const metadata = createSessionMetadata(req);
      const response = await aiService.getSemanticCompletions({
        context,
        partialInput: partial_input,
        completionType: completion_type,
        maxSuggestions: max_suggestions,
        metadata,
      });

      res.json(response);
    } catch (error) {
      console.error('Semantic completion error:', error);
      handleRouteError(res, error, 'Failed to get semantic completions');
    }
  });

  router.post('/anti-pattern-detection', async (req: Request, res: Response) => {
    try {
      const metadata = createSessionMetadata(req);
      const response = await aiService.detectAntiPatterns(metadata);
      res.json(response);
    } catch (error) {
      console.error('Anti-pattern detection error:', error);
      handleRouteError(res, error, 'Failed to detect anti-patterns');
    }
  });

  router.post(
    '/apply-suggestion',
    authMiddleware,
    requireRole('owner', 'reader'),
    async (req: Request, res: Response) => {
      try {
        const { file_path, line_number, suggested_fix } =
          applySuggestionSchema.parse(req.body);
        const metadata = createSessionMetadata(req);
        const response = await aiService.applySuggestion({
          filePath: file_path,
          lineNumber: line_number,
          suggestedFix: suggested_fix,
          metadata,
        });

        res.json(response);
      } catch (error) {
        console.error('Apply suggestion error:', error);
        handleRouteError(res, error, 'Failed to apply suggestion');
      }
    }
  );

  return router;
};

const router = createAIRouter();

export default router;
