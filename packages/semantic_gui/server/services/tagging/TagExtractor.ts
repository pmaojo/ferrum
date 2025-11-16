import path from 'path';

import type { Template, NativeTag } from '../../types/universal-tag-system';
import { TemplateService } from '../TemplateService';

import { PatternMatchingUtils } from './PatternMatchingUtils';

interface NativePattern {
  regex: string;
  extractors?: Record<string, any>;
  multiline?: boolean;
  flags?: string;
  context?: {
    filePattern?: string;
    directoryPattern?: string;
    nearbyPatterns?: string[];
  };
}

interface MatchInfo {
  match: RegExpExecArray;
  lineNumber: number;
  columnNumber: number;
}

/**
 * TagExtractor loads template native pattern definitions and
 * extracts framework-specific tags from source code.
 */
export class TagExtractor {
  private templateService: TemplateService;

  constructor(templateService?: TemplateService) {
    this.templateService = templateService || new TemplateService();
  }

  /**
   * Extract native framework tags from code using template patterns
   */
  async extractNativeTags(
    code: string,
    templateId: string,
    filePath: string
  ): Promise<NativeTag[]> {
    let template: Template;
    try {
      template = (await this.templateService.loadTemplate(templateId)) as any;
    } catch {
      return [];
    }

    const patterns = template.universalTagSystem?.extraction?.nativePatterns;
    if (!patterns) {
      return [];
    }

    const framework = template.metadata?.framework || 'unknown';
    const tags: NativeTag[] = [];

    for (const [tagType, patternList] of Object.entries(patterns)) {
      for (const pattern of patternList as NativePattern[]) {
        const matches = this.findMatches(code, pattern, filePath);
        for (const m of matches) {
          tags.push(
            this.createNativeTag(
              tagType,
              m,
              framework,
              filePath,
              pattern.extractors
            )
          );
        }
      }
    }

    return tags;
  }

  /**
   * Extract tags based on framework naming conventions
   */
  async extractConventionTags(
    code: string,
    templateId: string,
    filePath: string
  ): Promise<NativeTag[]> {
    let template: Template;
    try {
      template = (await this.templateService.loadTemplate(templateId)) as any;
    } catch {
      return [];
    }

    const conventions = template.universalTagSystem?.extraction?.conventions;
    if (!conventions) {
      return [];
    }

    const framework = template.metadata?.framework || 'unknown';
    const tags: NativeTag[] = [];

    // Directory mappings
    const normalizedPath = filePath.replace(/\\/g, '/');
    for (const [pattern, info] of Object.entries(
      conventions.directoryMapping || {}
    )) {
      if (
        PatternMatchingUtils.matchesPattern(normalizedPath, pattern).matches
      ) {
        tags.push(
          this.createConventionTag(
            info.type,
            info.layer,
            framework,
            filePath,
            path.dirname(filePath)
          )
        );
      }
    }

    // File name patterns
    const fileName = path.basename(filePath);
    for (const [pattern, info] of Object.entries(
      conventions.fileNamePatterns || {}
    )) {
      if (PatternMatchingUtils.matchesPattern(fileName, pattern).matches) {
        tags.push(
          this.createConventionTag(
            info.type,
            info.layer,
            framework,
            filePath,
            fileName
          )
        );
      }
    }

    // Class name suffix patterns
    const classRegex = /class\s+(\w+)/g;
    let match: RegExpExecArray | null;
    while ((match = classRegex.exec(code)) !== null) {
      const className = match[1];
      const { line, column } = this.getLineAndColumn(code, match.index);
      for (const [suffix, info] of Object.entries(
        conventions.classNamePatterns || {}
      )) {
        if (className.endsWith(suffix)) {
          tags.push(
            this.createConventionTag(
              info.type,
              info.layer,
              framework,
              filePath,
              className,
              line,
              column,
              { className }
            )
          );
        }
      }
    }

    return tags;
  }

  /**
   * Find all matches for a given pattern in code, honouring context rules
   */
  private findMatches(
    code: string,
    pattern: NativePattern,
    filePath: string
  ): MatchInfo[] {
    if (pattern.context?.filePattern) {
      const fileMatch = PatternMatchingUtils.matchesPattern(
        filePath,
        pattern.context.filePattern
      );
      if (!fileMatch.matches) {
        return [];
      }
    }

    if (pattern.context?.directoryPattern) {
      const dir = path.dirname(filePath);
      const dirMatch = PatternMatchingUtils.matchesPattern(
        dir,
        pattern.context.directoryPattern
      );
      if (!dirMatch.matches) {
        return [];
      }
    }

    const flags = this.buildFlags(pattern);
    const regex = new RegExp(pattern.regex, flags);
    const matches: MatchInfo[] = [];
    let exec: RegExpExecArray | null;
    while ((exec = regex.exec(code)) !== null) {
      const { line, column } = this.getLineAndColumn(code, exec.index);
      matches.push({ match: exec, lineNumber: line, columnNumber: column });
      if (!regex.global) break;
    }
    return matches;
  }

  /**
   * Create a NativeTag object from a regex match and extractor rules
   */
  private createNativeTag(
    tagType: string,
    match: MatchInfo,
    framework: string,
    filePath: string,
    extractors: Record<string, any> = {}
  ): NativeTag {
    const extracted = this.applyExtractors(extractors, match.match);
    const type = extracted.type || tagType;
    if (Object.prototype.hasOwnProperty.call(extracted, 'type')) {
      delete extracted.type;
    }

    return {
      type,
      value: match.match[0],
      framework,
      filePath,
      lineNumber: match.lineNumber,
      columnNumber: match.columnNumber,
      context: {},
      rawMatch: match.match[0],
      extractedData: extracted,
      confidence: 1,
      isValidated: false,
    };
  }

  /** Create a NativeTag from convention match */
  private createConventionTag(
    type: string,
    layer: string,
    framework: string,
    filePath: string,
    value: string,
    lineNumber = 1,
    columnNumber = 1,
    context: Record<string, any> = {}
  ): NativeTag {
    return {
      type,
      value,
      framework,
      filePath,
      lineNumber,
      columnNumber,
      context,
      rawMatch: value,
      extractedData: { layer },
      confidence: 1,
      isValidated: false,
    };
  }

  /** Apply extractor mappings to regex match groups */
  private applyExtractors(
    extractors: Record<string, any>,
    match: RegExpExecArray
  ): Record<string, any> {
    const result: Record<string, any> = {};
    for (const [key, value] of Object.entries(extractors)) {
      if (typeof value === 'string') {
        result[key] = value.replace(
          /\$(\d+)/g,
          (_m, g) => match[parseInt(g, 10)] || ''
        );
      } else if (value && typeof value === 'object') {
        result[key] = this.applyExtractors(value, match);
      } else {
        result[key] = value;
      }
    }
    return result;
  }

  private buildFlags(pattern: NativePattern): string {
    const base = pattern.flags || '';
    const includesGlobal = base.includes('g');
    const includesMultiline = base.includes('m');
    const flags =
      base +
      (includesGlobal ? '' : 'g') +
      (pattern.multiline || includesMultiline ? 'm' : '');
    return Array.from(new Set(flags.split(''))).join('');
  }

  private getLineAndColumn(
    text: string,
    index: number
  ): {
    line: number;
    column: number;
  } {
    const lines = text.slice(0, index).split(/\r?\n/);
    return { line: lines.length, column: lines[lines.length - 1].length + 1 };
  }
}

export default TagExtractor;
