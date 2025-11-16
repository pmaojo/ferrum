import type {
  SCGTag,
  TagValidationResult,
  TagValidationError,
  TagValidationWarning,
} from './TagSystem';

export interface ValidationRule {
  rule: string;
  type: 'required' | 'prohibited';
  description?: string;
  pattern: string; // e.g., "service->domain" or "port<-adapter"
}

export interface TagValidatorConfig {
  universalRules?: ValidationRule[];
  frameworkRules?: Record<string, ValidationRule[]>;
  typeLayerMap?: Record<SCGTag['type'], SCGTag['layer']>;
}

/**
 * TagValidator validates SCG tags using universal and framework-specific rules.
 * Rules are configuration driven and support simple semantic consistency checks
 * such as layer/type mapping and relationship requirements.
 */
export class TagValidator {
  private universalRules: ValidationRule[];
  private frameworkRules: Record<string, ValidationRule[]>;
  private typeLayerMap: Record<SCGTag['type'], SCGTag['layer']>;

  constructor(config: TagValidatorConfig = {}) {
    this.universalRules = config.universalRules ?? [];
    this.frameworkRules = config.frameworkRules ?? {};
    this.typeLayerMap =
      config.typeLayerMap ??
      ({
        controller: 'presentation',
        service: 'application',
        usecase: 'application',
        port: 'application',
        adapter: 'infrastructure',
        repository: 'infrastructure',
        entity: 'domain',
        valueobject: 'domain',
        dto: 'application',
        module: 'application',
      } as Record<SCGTag['type'], SCGTag['layer']>);
  }

  /**
   * Validate a list of SCG tags against universal and framework rules.
   */
  async validateTags(tags: SCGTag[]): Promise<TagValidationResult> {
    const errors: TagValidationError[] = [];
    const warnings: TagValidationWarning[] = [];

    // Basic semantic checks
    for (const tag of tags) {
      if (!tag.type || !tag.layer) {
        errors.push({
          tag,
          message: 'Tag missing required type or layer',
          severity: 'error',
        });
        continue;
      }
      const expectedLayer = this.typeLayerMap[tag.type];
      if (expectedLayer && tag.layer !== expectedLayer) {
        errors.push({
          tag,
          message: `${tag.type} should be in layer ${expectedLayer} but is in ${tag.layer}`,
          severity: 'warning',
        });
      }
    }

    // Group tags by framework
    const tagsByFramework: Record<string, SCGTag[]> = {};
    for (const tag of tags) {
      const fw = tag.framework || 'unknown';
      if (!tagsByFramework[fw]) tagsByFramework[fw] = [];
      tagsByFramework[fw].push(tag);
    }

    for (const [framework, fwTags] of Object.entries(tagsByFramework)) {
      const frameworkRules = this.frameworkRules[framework] || [];
      const rules = [...this.universalRules, ...frameworkRules];
      for (const rule of rules) {
        this.applyRule(rule, fwTags, errors, warnings);
      }
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
    };
  }

  private applyRule(
    rule: ValidationRule,
    tags: SCGTag[],
    errors: TagValidationError[],
    warnings: TagValidationWarning[]
  ): void {
    const match = rule.pattern.match(/^([a-z]+)\s*(<-|->)\s*([a-z]+)$/i);
    if (!match) {
      if (tags[0]) {
        warnings.push({
          tag: tags[0],
          message: `Invalid rule pattern "${rule.pattern}"`,
        });
      }
      return;
    }

    const [, leftRaw, operator, rightRaw] = match;
    const left = leftRaw.toLowerCase();
    const right = rightRaw.toLowerCase();

    if (operator === '->') {
      const matches: { src: SCGTag; tgt: SCGTag }[] = [];
      for (const src of tags.filter(t => t.type === left)) {
        for (const tgt of tags.filter(t => t.type === right)) {
          const dep =
            src.dependencies?.includes(right) || src.uses?.includes(right);
          if (dep) {
            matches.push({ src, tgt });
          }
        }
      }

      if (rule.type === 'prohibited' && matches.length > 0) {
        for (const m of matches) {
          errors.push({
            tag: m.src,
            message: `${rule.rule}: ${left} should not depend on ${right}`,
            severity: 'error',
          });
        }
      }

      if (rule.type === 'required' && matches.length === 0) {
        const src = tags.find(t => t.type === left);
        if (src) {
          errors.push({
            tag: src,
            message: `${rule.rule}: ${left} must depend on ${right}`,
            severity: 'error',
          });
        }
      }
    } else if (operator === '<-') {
      const sources = tags.filter(t => t.type === left);
      for (const src of sources) {
        const implemented = tags.some(
          t => t.type === right && t.implements?.includes(left)
        );
        if (rule.type === 'required' && !implemented) {
          errors.push({
            tag: src,
            message: `${rule.rule}: ${right} must implement ${left}`,
            severity: 'error',
          });
        }
        if (rule.type === 'prohibited' && implemented) {
          const implementor = tags.find(
            t => t.type === right && t.implements?.includes(left)
          );
          errors.push({
            tag: implementor || src,
            message: `${rule.rule}: ${right} should not implement ${left}`,
            severity: 'error',
          });
        }
      }
    }
  }
}
