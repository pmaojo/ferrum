import path from 'path';

import type { TagSuggestion, SCGTag } from '../../types/universal-tag-system';

/**
 * AutoSuggester provides lightweight tag inference and injection helpers.
 *
 * The heuristics here are intentionally simple – they are designed to offer
 * best‑effort suggestions without relying on heavy language specific tooling.
 */
export class AutoSuggester {
  /**
   * Generate tag suggestions combining AST and file location heuristics.
   */
  async suggestTags(code: string, filePath: string): Promise<TagSuggestion[]> {
    const byLocation = this.inferComponentsByLocation(filePath);
    const byAst = this.inferComponentsByAST(code, filePath);
    return [...byLocation, ...byAst];
  }

  /**
   * Infer component type by analysing simple AST patterns such as class
   * declarations. This does not use a real parser but relies on common naming
   * conventions like `UserService` or `OrderController`.
   */
  inferComponentsByAST(code: string, filePath: string): TagSuggestion[] {
    const suggestions: TagSuggestion[] = [];
    const classRegex = /class\s+(\w+)/g;
    let match: RegExpExecArray | null;

    while ((match = classRegex.exec(code)) !== null) {
      const name = match[1];
      let type: SCGTag['type'] | undefined;
      if (name.endsWith('Controller')) type = 'controller';
      else if (name.endsWith('Service')) type = 'service';
      else if (name.endsWith('Repository')) type = 'repository';

      if (!type) continue;

      const lineNumber = code.slice(0, match.index).split(/\r?\n/).length;
      const line = code.split(/\r?\n/)[lineNumber - 1] || '';

      suggestions.push({
        suggestedTag: { type, layer: this.mapTypeToLayer(type), filePath },
        confidence: 0.6,
        reason: `Class name suggests ${type}`,
        filePath,
        lineNumber,
        codeContext: line.trim(),
        canAutoApply: true,
        template: '',
        source: 'ast',
        alternatives: [],
      });
    }

    return suggestions;
  }

  /**
   * Infer component type by file path. Looks for well known directory names
   * (controllers, services, repositories, adapters, ports).
   */
  inferComponentsByLocation(filePath: string): TagSuggestion[] {
    const suggestions: TagSuggestion[] = [];
    const normalized = filePath.replace(/\\/g, '/').toLowerCase();

    const locationMap: Record<
      string,
      { type: SCGTag['type']; layer: SCGTag['layer'] }
    > = {
      '/controllers/': { type: 'controller', layer: 'presentation' },
      '/services/': { type: 'service', layer: 'application' },
      '/repositories/': { type: 'repository', layer: 'infrastructure' },
      '/adapters/': { type: 'adapter', layer: 'infrastructure' },
      '/ports/': { type: 'port', layer: 'application' },
    };

    for (const [segment, info] of Object.entries(locationMap)) {
      if (normalized.includes(segment)) {
        suggestions.push({
          suggestedTag: { type: info.type, layer: info.layer, filePath },
          confidence: 0.7,
          reason: `File path implies ${info.type}`,
          filePath,
          codeContext: path.basename(filePath),
          canAutoApply: true,
          template: '',
          source: 'convention',
          alternatives: [],
        });
      }
    }

    return suggestions;
  }

  /**
   * Automatically inject SCG tags into the provided code based on suggestions.
   * A simple in-memory backup is used so failures rollback the changes.
   */
  async autoTag(
    code: string,
    filePath: string,
    suggestions: TagSuggestion[]
  ): Promise<string> {
    const backup = code;
    try {
      const tags: SCGTag[] = suggestions
        .filter(
          s => s.canAutoApply && s.suggestedTag.type && s.suggestedTag.layer
        )
        .map(s => ({
          type: s.suggestedTag.type as SCGTag['type'],
          layer: s.suggestedTag.layer as SCGTag['layer'],
          domain: s.suggestedTag.domain || 'unknown',
          framework: s.suggestedTag.framework || 'unknown',
          language: s.suggestedTag.language || 'unknown',
          filePath: s.filePath,
          lineNumber: s.lineNumber,
          dependencies: [],
          implements: [],
          uses: [],
          metadata: s.suggestedTag.metadata || {},
          originalTags: [],
        }));

      const updated = await this.injectSCGTags(code, tags);
      return updated;
    } catch (_err) {
      return backup; // rollback on failure
    }
  }

  /**
   * Inject SCG tags as comments above the target line numbers.
   * If an error occurs the original code is returned.
   */
  async injectSCGTags(code: string, tags: SCGTag[]): Promise<string> {
    const backup = code.split(/\r?\n/);
    try {
      const lines = [...backup];
      for (const tag of tags) {
        const index = tag.lineNumber ? Math.max(tag.lineNumber - 1, 0) : 0;
        const comment = `// @scg ${tag.type}:${tag.layer} ${tag.domain}`;
        lines.splice(index, 0, comment);
      }
      return lines.join('\n');
    } catch (_err) {
      return backup.join('\n');
    }
  }

  /**
   * Remove existing SCG tag comments from the code. Optionally restrict to
   * specific tag types.
   */
  async removeTags(code: string, tagTypes: string[] = []): Promise<string> {
    const backup = code;
    try {
      const lines = code.split(/\r?\n/).filter(line => {
        const trimmed = line.trim();
        if (!trimmed.startsWith('// @scg')) return true;
        if (tagTypes.length === 0) return false;
        const type = trimmed.split(/\s+/)[2]?.split(':')[0];
        return !tagTypes.includes(type || '');
      });
      return lines.join('\n');
    } catch (_err) {
      return backup;
    }
  }

  private mapTypeToLayer(type: string): SCGTag['layer'] {
    switch (type) {
      case 'controller':
        return 'presentation';
      case 'service':
      case 'port':
        return 'application';
      case 'repository':
      case 'adapter':
        return 'infrastructure';
      default:
        return 'domain';
    }
  }
}

export default AutoSuggester;
