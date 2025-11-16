/**
 * Pattern Matching Utilities for Universal Tag System
 *
 * This module provides reusable pattern matching utilities for file paths,
 * code patterns, and directory structures used throughout the Universal Tag System.
 */

import { spawnSync } from 'child_process';

export interface PatternMatchOptions {
  caseSensitive?: boolean;
  multiline?: boolean;
  global?: boolean;
  dotAll?: boolean;
  unicode?: boolean;
  maxMatches?: number;
  timeout?: number; // Timeout in milliseconds
}

export interface PatternMatchResult {
  matches: boolean;
  matchedText?: string;
  matchGroups?: string[];
  matchCount?: number;
  executionTime?: number;
}

export interface DirectoryMatchOptions {
  recursive?: boolean;
  includeHidden?: boolean;
  maxDepth?: number;
  excludePatterns?: string[];
}

/**
 * Utility class for pattern matching operations
 */
export class PatternMatchingUtils {
  private static regexCache: Map<string, RegExp> = new Map();
  private static readonly CACHE_SIZE_LIMIT = 1000;

  /**
   * Matches a file path against a glob-style pattern
   * @param filePath - The file path to check
   * @param pattern - The glob pattern (supports *, **, ?, [abc], {a,b,c})
   * @param options - Matching options
   * @returns PatternMatchResult with match information
   */
  static matchesPattern(
    filePath: string,
    pattern: string,
    options: PatternMatchOptions = {}
  ): PatternMatchResult {
    const startTime = Date.now();

    try {
      const regex = this.getOrCreateGlobRegex(pattern, options);
      const matches = regex.test(filePath);

      return {
        matches,
        matchedText: matches ? filePath : undefined,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      console.warn(`Pattern matching error for pattern "${pattern}":`, error);
      return {
        matches: false,
        executionTime: Date.now() - startTime,
      };
    }
  }

  /**
   * Matches code content against a regex pattern
   * @param code - The code content to search
   * @param regexPattern - The regex pattern to match
   * @param options - Matching options
   * @returns PatternMatchResult with match information
   */
  static matchesRegex(
    code: string,
    regexPattern: string,
    options: PatternMatchOptions = {}
  ): PatternMatchResult {
    const startTime = Date.now();

    try {
      // When a timeout is specified, run the regex in a child process that can be terminated
      if (options.timeout) {
        const flags = this.buildRegexFlags(options);
        const script =
          `const pattern = new RegExp(${JSON.stringify(regexPattern)}, '${flags}');\n` +
          `const text = ${JSON.stringify(code)};\n` +
          `const matches = pattern.exec(text);\n` +
          `const globalPattern = new RegExp(pattern.source, pattern.flags.includes('g') ? pattern.flags : pattern.flags + 'g');\n` +
          `const matchCount = text.match(globalPattern)?.length || 0;\n` +
          `console.log(JSON.stringify({matches: matches !== null, matchedText: matches ? matches[0] : undefined, matchGroups: matches ? Array.from(matches).slice(1) : undefined, matchCount}));`;

        const result = spawnSync(process.execPath, ['-e', script], {
          timeout: options.timeout,
          encoding: 'utf8',
        });

        if ((result.error as any)?.code === 'ETIMEDOUT') {
          return {
            matches: false,
            executionTime: Date.now() - startTime,
          };
        }

        const output = result.stdout ? JSON.parse(result.stdout) : {};
        return {
          matches: output.matches || false,
          matchedText: output.matchedText,
          matchGroups: output.matchGroups,
          matchCount: output.matchCount,
          executionTime: Date.now() - startTime,
        };
      }

      const regex = this.getOrCreateRegex(regexPattern, options);
      const matches = regex.exec(code);

      return {
        matches: matches !== null,
        matchedText: matches?.[0],
        matchGroups: matches ? Array.from(matches).slice(1) : undefined,
        matchCount: this.countMatches(code, regex),
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      console.warn(
        `Regex matching error for pattern "${regexPattern}":`,
        error
      );
      return {
        matches: false,
        executionTime: Date.now() - startTime,
      };
    }
  }

  /**
   * Checks if directory structure matches a pattern
   * @param directories - Array of directory paths
   * @param pattern - The directory pattern to match
   * @param options - Directory matching options
   * @returns PatternMatchResult with match information
   */
  static matchesDirectoryStructure(
    directories: string[],
    pattern: string,
    options: DirectoryMatchOptions = {}
  ): PatternMatchResult {
    const startTime = Date.now();

    try {
      const normalize = (p: string) => p.replace(/\\/g, '/').replace(/\/$/, '');
      let filteredDirs = directories.map(d => normalize(d));

      if (!options.includeHidden) {
        filteredDirs = filteredDirs.filter(dir => !this.isHiddenPath(dir));
      }

      if (options.excludePatterns) {
        filteredDirs = filteredDirs.filter(
          dir =>
            !options.excludePatterns!.some(
              excludePattern => this.matchesPattern(dir, excludePattern).matches
            )
        );
      }

      if (options.maxDepth !== undefined) {
        filteredDirs = filteredDirs.filter(
          dir => this.getPathDepth(dir) <= options.maxDepth!
        );
      }

      if (options.recursive === false) {
        filteredDirs = filteredDirs.filter(dir => !dir.includes('/'));
      }

      const normalizedPattern = normalize(pattern);
      const matchingDirs = filteredDirs.filter(
        dir => this.matchesPattern(dir, normalizedPattern).matches
      );

      return {
        matches: matchingDirs.length > 0,
        matchedText: matchingDirs[0],
        matchCount: matchingDirs.length,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      console.warn(
        `Directory structure matching error for pattern "${pattern}":`,
        error
      );
      return {
        matches: false,
        executionTime: Date.now() - startTime,
      };
    }
  }

  /**
   * Finds all matches of a pattern in code
   * @param code - The code content to search
   * @param regexPattern - The regex pattern to match
   * @param options - Matching options
   * @returns Array of match results
   */
  static findAllMatches(
    code: string,
    regexPattern: string,
    options: PatternMatchOptions = {}
  ): Array<{
    match: string;
    groups: string[];
    index: number;
    line: number;
    column: number;
  }> {
    try {
      const regex = this.getOrCreateRegex(regexPattern, {
        ...options,
        global: true,
      });
      const matches: Array<{
        match: string;
        groups: string[];
        index: number;
        line: number;
        column: number;
      }> = [];

      let match;
      let matchCount = 0;
      const maxMatches = options.maxMatches || 1000;

      while ((match = regex.exec(code)) !== null && matchCount < maxMatches) {
        const position = this.getLineAndColumn(code, match.index);

        matches.push({
          match: match[0],
          groups: Array.from(match).slice(1),
          index: match.index,
          line: position.line,
          column: position.column,
        });

        matchCount++;

        // Prevent infinite loop on zero-length matches
        if (match.index === regex.lastIndex) {
          regex.lastIndex++;
        }
      }

      return matches;
    } catch (error) {
      console.warn(
        `Find all matches error for pattern "${regexPattern}":`,
        error
      );
      return [];
    }
  }

  /**
   * Validates if a pattern is syntactically correct
   * @param pattern - The pattern to validate
   * @param type - Type of pattern ('glob' or 'regex')
   * @returns Object with validation result and error message if invalid
   */
  static validatePattern(
    pattern: string,
    type: 'glob' | 'regex'
  ): { valid: boolean; error?: string } {
    try {
      if (type === 'regex') {
        new RegExp(pattern);
      } else {
        // For glob patterns, try to convert to regex
        this.globToRegex(pattern);
      }
      return { valid: true };
    } catch (error) {
      return {
        valid: false,
        error:
          error instanceof Error ? error.message : 'Unknown validation error',
      };
    }
  }

  /**
   * Escapes special regex characters in a string
   * @param str - String to escape
   * @returns Escaped string safe for use in regex
   */
  static escapeRegex(str: string): string {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  /**
   * Converts a glob pattern to a regular expression
   * @param pattern - Glob pattern to convert
   * @param options - Pattern options
   * @returns RegExp object
   */
  private static globToRegex(
    pattern: string,
    options: PatternMatchOptions = {}
  ): RegExp {
    let regexPattern = pattern
      .replace(/\./g, '\\.') // Escape dots
      .replace(/\*\*/g, '§DSTAR§') // Temporarily replace ** to avoid conflicts
      .replace(/\*/g, '[^/]*') // * matches any filename chars (not path separators)
      .replace(/§DSTAR§/g, '.*') // ** matches any path including separators
      .replace(/\?/g, '.') // ? matches single char
      .replace(/\{([^}]+)\}/g, '($1)') // {a,b,c} becomes (a|b|c)
      .replace(/,/g, '|') // Convert commas to alternation
      .replace(/\[([^\]]+)\]/g, '[$1]'); // Character classes remain the same

    // Handle patterns that start with **/ or end with /** differently
    const startsWithDoubleStar = pattern.startsWith('**/');
    const endsWithDoubleStar = pattern.endsWith('/**');

    // Ensure pattern matches appropriately
    if (!startsWithDoubleStar && !regexPattern.startsWith('^')) {
      regexPattern = `^${regexPattern}`;
    }
    if (!endsWithDoubleStar && !regexPattern.endsWith('$')) {
      regexPattern = `${regexPattern}$`;
    }

    const flags = this.buildRegexFlags(options);
    return new RegExp(regexPattern, flags);
  }

  /**
   * Gets or creates a cached regex for glob patterns
   */
  private static getOrCreateGlobRegex(
    pattern: string,
    options: PatternMatchOptions
  ): RegExp {
    const cacheKey = `glob:${pattern}:${JSON.stringify(options)}`;

    let regex = this.regexCache.get(cacheKey);
    if (!regex) {
      regex = this.globToRegex(pattern, options);
      this.setCachedRegex(cacheKey, regex);
    }

    return regex;
  }

  /**
   * Gets or creates a cached regex
   */
  private static getOrCreateRegex(
    pattern: string,
    options: PatternMatchOptions
  ): RegExp {
    const cacheKey = `regex:${pattern}:${JSON.stringify(options)}`;

    let regex = this.regexCache.get(cacheKey);
    if (!regex) {
      const flags = this.buildRegexFlags(options);
      regex = new RegExp(pattern, flags);
      this.setCachedRegex(cacheKey, regex);
    }

    return regex;
  }

  /**
   * Sets a regex in cache with size limit management
   */
  private static setCachedRegex(key: string, regex: RegExp): void {
    if (this.regexCache.size >= this.CACHE_SIZE_LIMIT) {
      // Remove oldest entries (simple FIFO)
      const firstKey = this.regexCache.keys().next().value;
      if (firstKey) {
        this.regexCache.delete(firstKey);
      }
    }
    this.regexCache.set(key, regex);
  }

  /**
   * Builds regex flags from options
   */
  private static buildRegexFlags(options: PatternMatchOptions): string {
    let flags = '';
    if (!options.caseSensitive) flags += 'i';
    if (options.global) flags += 'g';
    if (options.multiline) flags += 'm';
    if (options.dotAll) flags += 's';
    if (options.unicode) flags += 'u';
    return flags;
  }

  /**
   * Counts the number of matches for a regex in text
   */
  private static countMatches(text: string, regex: RegExp): number {
    const globalRegex = new RegExp(
      regex.source,
      regex.flags.includes('g') ? regex.flags : `${regex.flags}g`
    );
    const matches = text.match(globalRegex);
    return matches ? matches.length : 0;
  }

  /**
   * Gets line and column number for a character index in text
   */
  private static getLineAndColumn(
    text: string,
    index: number
  ): { line: number; column: number } {
    const lines = text.substring(0, index).split('\n');
    return {
      line: lines.length,
      column: lines[lines.length - 1].length + 1,
    };
  }

  /**
   * Checks if a path is hidden (starts with dot)
   */
  private static isHiddenPath(path: string): boolean {
    return path.split('/').some(segment => segment.startsWith('.'));
  }

  /**
   * Gets the depth of a path (number of directory separators)
   */
  private static getPathDepth(path: string): number {
    return path.split('/').length - 1;
  }

  /**
   * Clears the regex cache
   */
  static clearCache(): void {
    this.regexCache.clear();
  }

  /**
   * Gets cache statistics
   */
  static getCacheStats(): { size: number; limit: number; hitRate?: number } {
    return {
      size: this.regexCache.size,
      limit: this.CACHE_SIZE_LIMIT,
    };
  }
}

export default PatternMatchingUtils;
