import path from 'path';

import { featureFlagService } from '../FeatureFlagService';
import { TemplateService } from '../TemplateService';

describe('TemplateService.listTemplates', () => {
  it('includes laravel-hexagonal template when laravelBeta flag enabled', async () => {
    (featureFlagService as any).flags.laravelBeta = true;
    const templatesDir = path.join(
      __dirname,
      '..',
      '..',
      '..',
      '..',
      'templates',
      'semantic_gui'
    );
    const service = new TemplateService(templatesDir);
    const templates = await service.listTemplates();
    const ids = templates.map(t => t.id);
    expect(ids).toContain('laravel-hexagonal');
  });
});
