import type { Template } from '../shared/schema';
import type { IStorage } from '../storage';
import { logger } from '../utils/logger';

import TemplateService from './TemplateService';

/**
 * Lookup a template by id using storage first, then falling back to
 * filesystem templates.
 */
export async function lookupTemplate(
  id: string,
  storage: IStorage,
  templateService: TemplateService = new TemplateService()
): Promise<Template | undefined> {
  // First try storage implementation
  const fromStorage = await storage.getTemplate(id);
  if (fromStorage) {
    return fromStorage;
  }

  // Fallback to filesystem templates
  try {
    return await templateService.getTemplate(id);
  } catch (error) {
    logger.error('Failed to load template', {
      operation: 'lookupTemplate',
      templateId: id,
      error: (error as Error).message,
    });
    return undefined;
  }
}
