import type { Response } from 'express';

import { logger } from './logger';

export function errorResponse(
  res: Response,
  status: number,
  message: string,
  code?: string | number,
  details?: unknown
) {
  const traceId = res.getHeader('x-trace-id');
  logger.error(message, { status, code: code ?? status, traceId, details });
  return res.status(status).json({
    code: code ?? status,
    message,
    details,
    traceId,
  });
}
