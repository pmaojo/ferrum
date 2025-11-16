import type { Request, Response } from 'express';

import { logger } from '../../utils/logger';
import type {
  CreateTemplatePayload,
  MultiProjectClient,
} from '../../services/permaGraphMultiProjectClient';
import { PermaGraphClientError } from '../../services/permaGraphMultiProjectClient';

function handleError(res: Response, error: unknown, message: string): Response {
  if (error instanceof PermaGraphClientError) {
    logger.error('PermaGraph template API error', error);
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

export class TemplateController {
  constructor(private readonly client: MultiProjectClient) {}

  listTemplates = async (_req: Request, res: Response) => {
    try {
      logger.info('📦 Listing project templates');
      const templates = await this.client.listTemplates();
      res.json({
        success: true,
        templates,
        total: templates.length,
      });
    } catch (error) {
      handleError(res, error, 'Failed to list templates');
    }
  };

  createTemplate = async (req: Request, res: Response) => {
    try {
      const payload = req.body as CreateTemplatePayload;

      if (!payload.name?.trim()) {
        return res.status(400).json({
          success: false,
          error: 'Template name is required',
        });
      }

      logger.info(`🧩 Creating new template: ${payload.name}`);

      const template = await this.client.createTemplate({
        ...payload,
        name: payload.name.trim(),
        description: payload.description?.trim(),
      });

      res.status(201).json({
        success: true,
        template,
        message: `Template "${payload.name}" created successfully`,
      });
    } catch (error) {
      handleError(res, error, 'Failed to create template');
    }
  };
}
