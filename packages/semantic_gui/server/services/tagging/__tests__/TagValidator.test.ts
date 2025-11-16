import type { SCGTag } from '../TagSystem';
import { TagValidator, type ValidationRule } from '../TagValidator';

function createTag(overrides: Partial<SCGTag>): SCGTag {
  return {
    type: 'service',
    layer: 'application',
    domain: 'Test',
    framework: 'test',
    language: 'ts',
    filePath: 'file.ts',
    dependencies: [],
    implements: [],
    uses: [],
    metadata: {},
    originalTags: [],
    ...overrides,
  } as SCGTag;
}

describe('TagValidator', () => {
  test('detects prohibited dependencies', async () => {
    const rules: ValidationRule[] = [
      {
        rule: 'NO_ENTITY_ADAPTER',
        type: 'prohibited',
        pattern: 'entity->adapter',
      },
    ];
    const validator = new TagValidator({ frameworkRules: { test: rules } });
    const tags: SCGTag[] = [
      createTag({ type: 'entity', layer: 'domain', dependencies: ['adapter'] }),
      createTag({ type: 'adapter', layer: 'infrastructure' }),
    ];
    const result = await validator.validateTags(tags);
    expect(result.valid).toBe(false);
    expect(result.errors[0].message).toMatch(
      'entity should not depend on adapter'
    );
  });

  test('reports missing required implementation', async () => {
    const validator = new TagValidator({
      frameworkRules: {
        test: [
          {
            rule: 'PORT_IMPLEMENTATION',
            type: 'required',
            pattern: 'port<-adapter',
          },
        ],
      },
    });
    const tags: SCGTag[] = [
      createTag({ type: 'port', layer: 'application' }),
      createTag({ type: 'adapter', layer: 'infrastructure' }),
    ];
    const result = await validator.validateTags(tags);
    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.tag.type === 'port')).toBe(true);
  });

  test('applies universal rules and layer consistency', async () => {
    const validator = new TagValidator({
      universalRules: [
        {
          rule: 'SERVICE_ENTITY',
          type: 'required',
          pattern: 'service->entity',
        },
      ],
      frameworkRules: {
        test: [
          {
            rule: 'PORT_IMPLEMENTATION',
            type: 'required',
            pattern: 'port<-adapter',
          },
        ],
      },
    });
    const tags: SCGTag[] = [
      createTag({ type: 'service', layer: 'application' }),
      createTag({ type: 'entity', layer: 'domain' }),
      createTag({ type: 'port', layer: 'application' }),
      createTag({ type: 'controller', layer: 'domain' }), // layer mismatch
    ];
    const result = await validator.validateTags(tags);
    expect(result.valid).toBe(false);
    expect(
      result.errors.some(
        e =>
          e.message.includes('SERVICE_ENTITY') ||
          e.message.includes('must depend on entity')
      )
    ).toBe(true);
    expect(result.errors.some(e => e.tag.type === 'port')).toBe(true);
    expect(
      result.errors.some(e =>
        e.message.includes('controller should be in layer')
      )
    ).toBe(true);
  });

  test('warns on invalid rule patterns', async () => {
    const validator = new TagValidator({
      frameworkRules: {
        test: [{ rule: 'BAD_RULE', type: 'required', pattern: 'invalid' }],
      },
    });
    const tags: SCGTag[] = [createTag({})];
    const result = await validator.validateTags(tags);
    expect(result.warnings).toHaveLength(1);
    expect(result.warnings[0].message).toMatch('Invalid rule pattern');
  });
});
