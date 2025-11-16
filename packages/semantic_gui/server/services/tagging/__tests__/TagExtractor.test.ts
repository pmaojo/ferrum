import type { Template } from '../../../types/universal-tag-system';
import { TagExtractor } from '../TagExtractor';

const loadTemplate = jest.fn();

jest.mock('../../TemplateService', () => {
  return {
    TemplateService: class {
      loadTemplate = loadTemplate;
    },
  };
});

describe('TagExtractor', () => {
  let extractor: TagExtractor;

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
        nativePatterns: {
          decorator: [
            {
              regex: '@(Controller|Service|Module)\\(([^)]*)\\)',
              extractors: { type: '$1', metadata: { args: '$2' } },
            },
          ],
        },
        conventions: {
          directoryMapping: {},
          fileNamePatterns: {},
          classNamePatterns: {},
        },
      },
      translation: { toSCG: {}, fromSCG: {} },
      autoTagging: { enabled: false, confidence: 'low', patterns: [] },
    },
  };

  beforeEach(() => {
    extractor = new TagExtractor();
    loadTemplate.mockReset();
  });

  test('extracts native tags using template patterns', async () => {
    loadTemplate.mockResolvedValue(baseTemplate);
    const code = "@Controller('users')\nexport class UserController {}";
    const tags = await extractor.extractNativeTags(
      code,
      'test-template',
      'src/user.controller.ts'
    );
    expect(tags).toHaveLength(1);
    expect(tags[0]).toMatchObject({
      type: 'Controller',
      value: "@Controller('users')",
      framework: 'test',
      filePath: 'src/user.controller.ts',
      lineNumber: 1,
    });
  });

  test('respects file pattern context', async () => {
    const templateWithContext: Template = JSON.parse(
      JSON.stringify(baseTemplate)
    );
    templateWithContext.universalTagSystem!.extraction.nativePatterns.decorator[0].context =
      {
        filePattern: '**/*.controller.ts',
      };
    loadTemplate.mockResolvedValue(templateWithContext);
    const tags = await extractor.extractNativeTags(
      "@Controller('users')\nexport class UserController {}",
      'test-template',
      'src/not-matching.service.ts'
    );
    expect(tags).toHaveLength(0);
  });

  test('extracts convention tags from directory mapping', async () => {
    const template: Template = JSON.parse(JSON.stringify(baseTemplate));
    template.universalTagSystem!.extraction.conventions.directoryMapping = {
      'src/controllers/**': { type: 'Controller', layer: 'presentation' },
    };
    loadTemplate.mockResolvedValue(template);
    const tags = await extractor.extractConventionTags(
      'export class User {}',
      'test-template',
      'src/controllers/user.ts'
    );
    expect(tags).toHaveLength(1);
    expect(tags[0]).toMatchObject({
      type: 'Controller',
      extractedData: { layer: 'presentation' },
    });
  });

  test('extracts convention tags from filename patterns', async () => {
    const template: Template = JSON.parse(JSON.stringify(baseTemplate));
    template.universalTagSystem!.extraction.conventions.fileNamePatterns = {
      '*.service.ts': { type: 'Service', layer: 'application' },
    };
    loadTemplate.mockResolvedValue(template);
    const tags = await extractor.extractConventionTags(
      'export class UserService {}',
      'test-template',
      'src/user.service.ts'
    );
    expect(tags).toHaveLength(1);
    expect(tags[0]).toMatchObject({
      type: 'Service',
      extractedData: { layer: 'application' },
    });
  });

  test('extracts convention tags from class name suffixes', async () => {
    const template: Template = JSON.parse(JSON.stringify(baseTemplate));
    template.universalTagSystem!.extraction.conventions.classNamePatterns = {
      Controller: { type: 'Controller', layer: 'presentation' },
    };
    loadTemplate.mockResolvedValue(template);
    const code = 'export class UserController {}';
    const tags = await extractor.extractConventionTags(
      code,
      'test-template',
      'src/user.controller.ts'
    );
    expect(tags).toHaveLength(1);
    expect(tags[0]).toMatchObject({
      type: 'Controller',
      context: { className: 'UserController' },
      extractedData: { layer: 'presentation' },
    });
  });

  test('extracts module tags using decorator pattern', async () => {
    loadTemplate.mockResolvedValue(baseTemplate);
    const code = '@Module({})\nexport class AppModule {}';
    const tags = await extractor.extractNativeTags(
      code,
      'test-template',
      'src/app.module.ts'
    );
    expect(tags).toHaveLength(1);
    expect(tags[0]).toMatchSnapshot();
  });
});
