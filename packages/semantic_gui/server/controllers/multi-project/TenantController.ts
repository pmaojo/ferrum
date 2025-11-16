import type { Request, Response } from 'express';

import { logger } from '../../utils/logger';
import type { MultiProjectClient } from '../../services/permaGraphMultiProjectClient';
import { PermaGraphClientError } from '../../services/permaGraphMultiProjectClient';

function handleError(res: Response, error: unknown, message: string): Response {
  if (error instanceof PermaGraphClientError) {
    logger.error('PermaGraph tenant API error', error);
    return res.status(error.statusCode).json({
      success: false,
      error: error.message,
      details: error.details,
    });
  }

  logger.error(message, error);
  return res.status(500).json({
    success: false,
    error: message,
  });
}

export class TenantController {
  constructor(private readonly client: MultiProjectClient) {}

  listTenantProjects = async (req: Request, res: Response) => {
    try {
      const { tenantId } = req.params;
      const { status } = req.query;

      logger.info(`🏢 Getting projects for tenant: ${tenantId}`);

      const projects = await this.client.listTenantProjects(tenantId, {
        status: status as string | undefined,
      });

      res.json({
        success: true,
        tenant_id: tenantId,
        projects,
        total: projects.length,
      });
    } catch (error) {
      handleError(res, error, 'Failed to fetch tenant projects');
    }
  };
}
