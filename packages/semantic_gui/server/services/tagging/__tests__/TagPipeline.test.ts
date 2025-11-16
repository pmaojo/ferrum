import type { Template } from '../../../types/universal-tag-system';
import { TagExtractor } from '../TagExtractor';
import { TagTranslator } from '../TagTranslator';
import { TagValidator } from '../TagValidator';

const loadTemplate = jest.fn();

jest.mock('../../TemplateService', () => {
  return {
    TemplateService: class {
      loadTemplate = loadTemplate;
    },
  };
});

describe('Tagging service integration', () => {
  const template: Template = {
    id: 'tmpl',
    name: 'tmpl',
    description: '',
    version: '1',
    metadata: { framework: 'test', language: 'ts', architecture: 'test' },
    universalTagSystem: {
      detection: { filePatterns: [], codePatterns: [], directoryPatterns: [] },
      extraction: {
        nativePatterns: {
          controller: [
            { regex: '@Controller\\(\\)', extractors: { type: 'controller' } },
          ],
        },
        conventions: {
          directoryMapping: {},
          fileNamePatterns: {},
          classNamePatterns: {},
        },
      },
      translation: {
        toSCG: {
          controller: { scgType: 'controller', scgLayer: 'presentation' },
        },
        fromSCG: {
          controller: 'Controller',
        },
      },
      autoTagging: { enabled: false, confidence: 'low', patterns: [] },
    },
  };

  beforeEach(() => {
    loadTemplate.mockResolvedValue(template);
  });

  it('extracts, translates and validates tags end-to-end', async () => {
    const extractor = new TagExtractor();
    const translator = new TagTranslator();
    const validator = new TagValidator();

    const code = '@Controller()\nclass AppController {}';
    const native = await extractor.extractNativeTags(
      code,
      'tmpl',
      'src/app.controller.ts'
    );
    const translation = await translator.translateToSCG(native, 'tmpl');
    const validation = await validator.validateTags(
      translation.translatedTags as any
    );

    expect(native).toHaveLength(1);
    expect(translation.translatedTags).toHaveLength(1);
    expect(validation.valid).toBe(true);
  });
});
