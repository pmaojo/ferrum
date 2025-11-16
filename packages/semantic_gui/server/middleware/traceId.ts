import type { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4, validate as uuidValidate } from 'uuid';

declare global {
  namespace Express {
    interface Request {
      traceId?: string;
    }
  }
}

export function traceIdMiddleware(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  let traceId = req.header('x-trace-id');
  if (!traceId || !uuidValidate(traceId)) {
    traceId = uuidv4();
  }
  req.traceId = traceId;
  res.setHeader('x-trace-id', traceId);
  next();
}

export default traceIdMiddleware;
