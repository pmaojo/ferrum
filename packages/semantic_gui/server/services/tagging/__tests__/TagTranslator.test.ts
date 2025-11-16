import type {
  Template,
  NativeTag,
  SCGTag,
} from '../../../types/universal-tag-system';
import { TagTranslator } from '../TagTranslator';

const loadTemplate = jest.fn();

jest.mock('../../TemplateService', () => {
  return {
    TemplateService: class {
      loadTemplate = loadTemplate;
    },
  };
});

describe('TagTranslator', () => {
  let translator: TagTranslator;
  const baseTemplate: Template = {
    id: 'test-template',
    name: 'Test Template',
    description: 'Template for testing',
    version: '1.0.0',
    metadata: {
      framework: 'test',
      language: 'ts',
      architecture: 'test',
    },
    universalTagSystem: {
      detection: { filePatterns: [], codePatterns: [], directoryPatterns: [] },
      extraction: {
        nativePatterns: {},
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
          'controller:presentation': 'Controller',
          '*': 'Generic',
        },
      },
      autoTagging: { enabled: false, confidence: 'low', patterns: [] },
    },
  };

  beforeEach(() => {
    translator = new TagTranslator();
    loadTemplate.mockReset();
  });

  test('translates native tags to SCG tags using case-insensitive matching', async () => {
    loadTemplate.mockResolvedValue(baseTemplate);
    const nativeTags: NativeTag[] = [
      {
        framework: 'test',
        type: 'Controller',
        value: '@Controller()',
        filePath: 'src/app.controller.ts',
        lineNumber: 1,
        columnNumber: 1,
        context: {},
        rawMatch: '@Controller()',
        extractedData: {},
        confidence: 1,
        isValidated: false,
      } as any,
    ];
    const result = await translator.translateToSCG(nativeTags, 'test-template');
    expect(result.translatedTags).toHaveLength(1);
    expect(result.untranslatable).toHaveLength(0);
    expect(result.confidence).toBe(1);
    expect(result.translatedTags[0]).toMatchObject({
      type: 'controller',
      layer: 'presentation',
    });
  });

  test('handles untranslatable tags and generates suggestions', async () => {
    loadTemplate.mockResolvedValue(baseTemplate);
    const nativeTags: NativeTag[] = [
      {
        framework: 'test',
        type: 'Service',
        value: '@Service()',
        filePath: 'src/app.service.ts',
        lineNumber: 1,
        columnNumber: 1,
        context: {},
        rawMatch: '@Service()',
        extractedData: {},
        confidence: 1,
        isValidated: false,
      } as any,
    ];
    const result = await translator.translateToSCG(nativeTags, 'test-template');
    expect(result.translatedTags).toHaveLength(0);
    expect(result.untranslatable).toHaveLength(1);
    expect(result.confidence).toBe(0);
    expect(result.suggestions.length).toBeGreaterThan(0);
  });

  test('translates SCG tags back to native tags using layer-specific rules', async () => {
    loadTemplate.mockResolvedValue(baseTemplate);
    const scg: SCGTag[] = [
      {
        type: 'controller',
        layer: 'presentation',
        domain: 'app',
        framework: 'test',
        language: 'ts',
        filePath: 'src/app.ts',
        lineNumber: 1,
        dependencies: [],
        implements: [],
        uses: [],
        metadata: {},
        originalTags: [],
      },
    ];
    const native = await translator.translateFromSCG(scg, 'test-template');
    expect(native).toHaveLength(1);
    expect(native[0].type).toBe('Controller');
  });

  test('applies wildcard rule when no direct translation exists', async () => {
    const wildcardTemplate: Template = {
      ...baseTemplate,
      universalTagSystem: {
        ...(baseTemplate.universalTagSystem as any),
        translation: {
          toSCG: {
            '*': { scgType: 'module', scgLayer: 'application' },
          },
          fromSCG: {},
        },
      },
    };
    loadTemplate.mockResolvedValue(wildcardTemplate);
    const nativeTags: NativeTag[] = [
      {
        framework: 'test',
        type: 'Unknown',
        value: '',
        filePath: 'src/file.ts',
        lineNumber: 1,
        columnNumber: 0,
        context: {},
        rawMatch: '',
        extractedData: {},
        confidence: 1,
        isValidated: false,
      } as any,
    ];
    const result = await translator.translateToSCG(nativeTags, 'wildcard');
    expect(result.translatedTags).toHaveLength(1);
    expect(result.translatedTags[0]).toMatchObject({
      type: 'module',
      layer: 'application',
    });
  });

  test('returns warning when template not found', async () => {
    loadTemplate.mockRejectedValue(new Error('not found'));
    const result = await translator.translateToSCG([], 'missing');
    expect(result.warnings).toContain('Template not found');
  });
});
