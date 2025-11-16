import type {
  Template,
  NativeTag,
  SCGTag,
  TagTranslationResult,
  TagSuggestion,
} from '../../types/universal-tag-system';
import { TemplateService } from '../TemplateService';

/**
 * TagTranslator converts between native framework tags and
 * SCG (Semantic Code Graph) tags using template translation rules.
 */
export class TagTranslator {
  private templateService: TemplateService;

  constructor(templateService?: TemplateService) {
    this.templateService = templateService || new TemplateService();
  }

  /**
   * Translate framework specific tags into SCG tags using template rules
   */
  async translateToSCG(
    nativeTags: NativeTag[],
    templateId: string
  ): Promise<TagTranslationResult> {
    let template: Template;
    try {
      template = (await this.templateService.loadTemplate(templateId)) as any;
    } catch {
      return {
        originalTags: nativeTags,
        translatedTags: [],
        untranslatable: nativeTags,
        suggestions: [],
        confidence: 0,
        warnings: ['Template not found'],
      };
    }

    const rules =
      template.universalTagSystem?.translation?.toSCG ||
      ({} as Record<string, any>);
    const translatedTags: SCGTag[] = [];
    const untranslatable: NativeTag[] = [];

    for (const tag of nativeTags) {
      const rule = this.findRule(rules, tag.type);
      if (rule) {
        translatedTags.push(this.createSCGTag(tag, rule, template));
      } else {
        untranslatable.push(tag);
      }
    }

    const suggestions = this.generateSuggestions(
      untranslatable,
      rules,
      template
    );
    const confidence = nativeTags.length
      ? translatedTags.length / nativeTags.length
      : 1;

    return {
      originalTags: nativeTags,
      translatedTags,
      untranslatable,
      suggestions,
      confidence,
      warnings: [],
    };
  }

  /**
   * Translate SCG tags back into framework specific tags
   */
  async translateFromSCG(
    scgTags: SCGTag[],
    templateId: string
  ): Promise<NativeTag[]> {
    let template: Template;
    try {
      template = (await this.templateService.loadTemplate(templateId)) as any;
    } catch {
      return [];
    }

    const rules =
      template.universalTagSystem?.translation?.fromSCG ||
      ({} as Record<string, string>);
    const result: NativeTag[] = [];

    for (const tag of scgTags) {
      const nativeType = this.findReverseRule(rules, tag.type, tag.layer);
      result.push({
        framework: template.metadata?.framework || tag.framework,
        type: nativeType,
        value: tag.domain,
        filePath: tag.filePath,
        lineNumber: tag.lineNumber ?? 0,
        context: {},
        rawMatch: '',
        extractedData: {},
        confidence: 1,
        isValidated: false,
      } as any);
    }

    return result;
  }

  private findRule(rules: Record<string, any>, type: string) {
    if (rules[type]) return rules[type];
    const lower = type.toLowerCase();
    for (const [key, rule] of Object.entries(rules)) {
      if (key.toLowerCase() === lower) return rule;
    }
    return rules['*'];
  }

  private findReverseRule(
    rules: Record<string, string>,
    scgType: string,
    layer: string
  ): string {
    if (rules[`${scgType}:${layer}`]) return rules[`${scgType}:${layer}`];
    if (rules[scgType]) return rules[scgType];
    const wildcard = rules['*'];
    if (wildcard) return wildcard;
    // fallback to original scg type if nothing matches
    return scgType;
  }

  private createSCGTag(
    tag: NativeTag,
    rule: {
      scgType: SCGTag['type'];
      scgLayer: SCGTag['layer'];
      metadata?: Record<string, any>;
    },
    template: Template
  ): SCGTag {
    return {
      type: rule.scgType,
      layer: rule.scgLayer,
      domain: (tag.extractedData as any)?.domain || 'unknown',
      framework: template.metadata?.framework || tag.framework,
      language: template.metadata?.language || 'unknown',
      filePath: tag.filePath,
      lineNumber: tag.lineNumber,
      dependencies: [],
      implements: [],
      uses: [],
      metadata: { ...(rule.metadata || {}), ...(tag.extractedData || {}) },
      originalTags: [tag],
    };
  }

  /**
   * Generate suggestions for untranslatable tags using available rules
   */
  private generateSuggestions(
    untranslatable: NativeTag[],
    rules: Record<string, any>,
    template: Template
  ): TagSuggestion[] {
    const suggestions: TagSuggestion[] = [];
    for (const tag of untranslatable) {
      const fallback = rules['*'] || Object.values(rules)[0];
      if (!fallback) continue;
      suggestions.push({
        suggestedTag: {
          type: fallback.scgType,
          layer: fallback.scgLayer,
          domain: (tag.extractedData as any)?.domain || 'unknown',
          framework: template.metadata?.framework || tag.framework,
          language: template.metadata?.language || 'unknown',
          filePath: tag.filePath,
          dependencies: [],
          implements: [],
          uses: [],
          metadata: fallback.metadata || {},
          originalTags: [tag],
        },
        confidence: rules['*'] ? 0.4 : 0.1,
        reason: rules['*']
          ? `Fallback rule applied for tag type "${tag.type}"`
          : `No translation rule for "${tag.type}". Suggested using available rule`,
        filePath: tag.filePath,
        lineNumber: tag.lineNumber,
        codeContext: tag.value,
        canAutoApply: false,
        template: template.id,
        source: 'pattern',
        alternatives: [],
      });
    }
    return suggestions;
  }
}

export default TagTranslator;
