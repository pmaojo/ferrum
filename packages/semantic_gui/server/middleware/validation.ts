import type { Request, Response, NextFunction } from 'express';

export function validateRequest(_schema?: any) {
  return (_req: Request, _res: Response, next: NextFunction) => {
    next();
  };
}
