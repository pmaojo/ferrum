import type { TagSuggestion } from '../../../types/universal-tag-system';
import { AutoSuggester } from '../AutoSuggester';

describe('AutoSuggester', () => {
  let suggester: AutoSuggester;

  beforeEach(() => {
    suggester = new AutoSuggester();
  });

  test('infers components from AST patterns', () => {
    const code = `class UserController {}\nclass PaymentService {}\nclass UserRepository {}`;
    const suggestions = suggester.inferComponentsByAST(code, 'src/app.ts');
    const types = suggestions.map(s => s.suggestedTag.type);
    expect(types).toEqual(
      expect.arrayContaining(['controller', 'service', 'repository'])
    );
  });

  test('infers components from file location', () => {
    const suggestions = suggester.inferComponentsByLocation(
      '/project/src/controllers/user.ts'
    );
    expect(suggestions).toHaveLength(1);
    expect(suggestions[0].suggestedTag.type).toBe('controller');
  });

  test('autoTag injects and removeTags strips comments', async () => {
    const code = 'class Foo {}';
    const suggestion: TagSuggestion = {
      suggestedTag: {
        type: 'service',
        layer: 'application',
        filePath: 'src/foo.ts',
      },
      confidence: 1,
      reason: 'Class name suggests service',
      filePath: 'src/foo.ts',
      lineNumber: 1,
      codeContext: 'class Foo {}',
      canAutoApply: true,
      template: '',
      source: 'ast',
      alternatives: [],
    };

    const tagged = await suggester.autoTag(code, 'src/foo.ts', [suggestion]);
    expect(tagged).toContain('// @scg service:application');

    const cleaned = await suggester.removeTags(tagged, ['service']);
    expect(cleaned).toBe(code);
  });
});
