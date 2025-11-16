/**
 * Framework Detection Engine (Template-Driven)
 *
 * This class implements template-driven framework detection that reads detection
 * configurations from templates and uses weighted scoring to determine the most
 * likely framework for a given codebase.
 */

import { promises as fs } from 'fs';
import path from 'path';

import type { Template } from '../../shared/schema';
import type {
  FrameworkDetectionResult,
  UniversalTagSystemConfig,
} from '../../types/universal-tag-system';
import { TemplateService } from '../TemplateService';

import { PatternMatchingUtils } from './PatternMatchingUtils';

export interface DetectionPattern {
  pattern: string;
  weight: number;
  type: 'file' | 'code' | 'directory';
}

export interface DetectionContext {
  filePath: string;
  fileContent: string;
  projectPath: string;
  allFiles?: string[];
  directories?: string[];
}

export class FrameworkDetector {
  private templateService: TemplateService;

  constructor(templateService?: TemplateService) {
    this.templateService = templateService || new TemplateService();
  }

  /**
   * Detects the framework for a given code file using template-based detection
   * @param code - The source code content
   * @param filePath - Path to the file being analyzed
   * @param projectPath - Root path of the project (optional)
   * @returns Promise<FrameworkDetectionResult>
   */
  async detectFramework(
    code: string,
    filePath: string,
    projectPath?: string
  ): Promise<FrameworkDetectionResult> {
    const context: DetectionContext = {
      filePath,
      fileContent: code,
      projectPath: projectPath || path.dirname(filePath),
    };

    // Load project structure if projectPath is provided
    if (projectPath) {
      try {
        context.allFiles = await this.getAllFiles(projectPath);
        context.directories = await this.getAllDirectories(projectPath);
      } catch (error) {
        console.warn('Could not load project structure:', error);
      }
    }

    const templates = await this.templateService.listTemplates();
    const detectionResults: Array<{
      template: Template;
      confidence: number;
      detectedPatterns: string[];
    }> = [];

    // Analyze each template's detection configuration
    for (const template of templates) {
      if (!template.universalTagSystem?.detection) {
        continue;
      }

      const result = await this.calculateConfidence(
        context,
        template.universalTagSystem.detection,
        template.id
      );

      if (result.confidence > 0) {
        detectionResults.push({
          template,
          confidence: result.confidence,
          detectedPatterns: result.detectedPatterns,
        });
      }
    }

    // Sort by confidence and return the best match
    detectionResults.sort((a, b) => b.confidence - a.confidence);

    if (detectionResults.length === 0) {
      return {
        templateId: 'unknown',
        framework: 'unknown',
        confidence: 0,
        detectedPatterns: [],
        metadata: {},
      };
    }

    const bestMatch = detectionResults[0];
    return {
      templateId: bestMatch.template.id,
      framework: bestMatch.template.metadata?.framework || 'unknown',
      confidence: bestMatch.confidence,
      detectedPatterns: bestMatch.detectedPatterns,
      metadata: {
        version: this.extractVersion(context, bestMatch.template),
        variant: bestMatch.template.metadata?.architecture,
        dependencies: this.extractDependencies(context),
        configFiles: this.findConfigFiles(context),
      },
    };
  }

  /**
   * Calculates confidence score for a specific template's detection configuration
   * @param context - Detection context with file and project information
   * @param detection - Detection configuration from template
   * @param templateId - ID of the template being evaluated
   * @returns Object with confidence score and detected patterns
   */
  async calculateConfidence(
    context: DetectionContext,
    detection: UniversalTagSystemConfig['detection'],
    _templateId: string
  ): Promise<{ confidence: number; detectedPatterns: string[] }> {
    let totalScore = 0;
    let maxPossibleScore = 0;
    const detectedPatterns: string[] = [];

    // Check file patterns
    if (detection.filePatterns) {
      for (const filePattern of detection.filePatterns) {
        maxPossibleScore += filePattern.weight;

        if (this.matchesPattern(context.filePath, filePattern.pattern)) {
          totalScore += filePattern.weight;
          detectedPatterns.push(`file:${filePattern.pattern}`);
        }

        // Also check against all project files if available
        if (context.allFiles) {
          const matchingFiles = context.allFiles.filter(file =>
            this.matchesPattern(file, filePattern.pattern)
          );
          if (matchingFiles.length > 0) {
            // Boost score based on number of matching files (diminishing returns)
            const boost = Math.min(
              matchingFiles.length * 0.1,
              filePattern.weight * 0.5
            );
            totalScore += boost;
            detectedPatterns.push(
              `files:${filePattern.pattern}(${matchingFiles.length})`
            );
          }
        }
      }
    }

    // Check code patterns
    if (detection.codePatterns) {
      for (const codePattern of detection.codePatterns) {
        maxPossibleScore += codePattern.weight;

        if (this.matchesRegex(context.fileContent, codePattern.regex)) {
          totalScore += codePattern.weight;
          detectedPatterns.push(`code:${codePattern.regex}`);
        }
      }
    }

    // Check directory patterns
    if (detection.directoryPatterns && context.directories) {
      for (const dirPattern of detection.directoryPatterns) {
        maxPossibleScore += dirPattern.weight;

        if (
          this.matchesDirectoryStructure(
            context.directories,
            dirPattern.pattern
          )
        ) {
          totalScore += dirPattern.weight;
          detectedPatterns.push(`dir:${dirPattern.pattern}`);
        }
      }
    }

    // Calculate normalized confidence (0-1)
    const confidence = maxPossibleScore > 0 ? totalScore / maxPossibleScore : 0;

    return {
      confidence: Math.min(confidence, 1.0), // Cap at 1.0
      detectedPatterns,
    };
  }

  /**
   * Checks if a file path matches a given pattern (glob-style)
   * @param filePath - The file path to check
   * @param pattern - The pattern to match against (supports * and ** wildcards)
   * @returns boolean indicating if the pattern matches
   */
  matchesPattern(filePath: string, pattern: string): boolean {
    return PatternMatchingUtils.matchesPattern(filePath, pattern, {
      caseSensitive: false,
    }).matches;
  }

  /**
   * Checks if code content matches a regex pattern
   * @param code - The code content to search
   * @param regexPattern - The regex pattern to match
   * @returns boolean indicating if the pattern matches
   */
  matchesRegex(code: string, regexPattern: string): boolean {
    return PatternMatchingUtils.matchesRegex(code, regexPattern, {
      global: true,
      multiline: true,
    }).matches;
  }

  /**
   * Checks if directory structure matches a pattern
   * @param directories - Array of directory paths in the project
   * @param pattern - The directory pattern to match
   * @returns boolean indicating if the pattern matches
   */
  matchesDirectoryStructure(directories: string[], pattern: string): boolean {
    return PatternMatchingUtils.matchesDirectoryStructure(
      directories,
      pattern,
      {
        includeHidden: false,
        excludePatterns: ['node_modules', 'vendor', 'target', 'dist', 'build'],
      }
    ).matches;
  }

  /**
   * Gets all files in a project directory recursively
   * @param projectPath - Root path of the project
   * @returns Promise<string[]> array of file paths
   */
  private async getAllFiles(projectPath: string): Promise<string[]> {
    const files: string[] = [];

    const scanDirectory = async (dirPath: string): Promise<void> => {
      try {
        const entries = await fs.readdir(dirPath, { withFileTypes: true });

        for (const entry of entries) {
          const fullPath = path.join(dirPath, entry.name);
          const relativePath = path.relative(projectPath, fullPath);

          // Skip hidden directories and common ignore patterns
          if (
            entry.name.startsWith('.') ||
            entry.name === 'node_modules' ||
            entry.name === 'vendor' ||
            entry.name === 'target' ||
            entry.name === 'dist' ||
            entry.name === 'build'
          ) {
            continue;
          }

          if (entry.isDirectory()) {
            await scanDirectory(fullPath);
          } else {
            files.push(relativePath);
          }
        }
      } catch (error) {
        // Ignore permission errors and continue
        console.debug(`Could not scan directory ${dirPath}:`, error);
      }
    };

    await scanDirectory(projectPath);
    return files;
  }

  /**
   * Gets all directories in a project recursively
   * @param projectPath - Root path of the project
   * @returns Promise<string[]> array of directory paths
   */
  private async getAllDirectories(projectPath: string): Promise<string[]> {
    const directories: string[] = [];

    const scanDirectory = async (dirPath: string): Promise<void> => {
      try {
        const entries = await fs.readdir(dirPath, { withFileTypes: true });

        for (const entry of entries) {
          if (entry.isDirectory()) {
            const fullPath = path.join(dirPath, entry.name);
            const relativePath = path.relative(projectPath, fullPath);

            // Skip hidden directories and common ignore patterns
            if (
              entry.name.startsWith('.') ||
              entry.name === 'node_modules' ||
              entry.name === 'vendor' ||
              entry.name === 'target' ||
              entry.name === 'dist' ||
              entry.name === 'build'
            ) {
              continue;
            }

            directories.push(relativePath);
            await scanDirectory(fullPath);
          }
        }
      } catch (error) {
        // Ignore permission errors and continue
        console.debug(`Could not scan directory ${dirPath}:`, error);
      }
    };

    await scanDirectory(projectPath);
    return directories;
  }

  /**
   * Extracts version information from the project context
   * @param context - Detection context
   * @param template - The matched template
   * @returns string version or undefined
   */
  private extractVersion(
    context: DetectionContext,
    template: Template
  ): string | undefined {
    const versionRegex = template.metadata?.versionRegex;
    if (!versionRegex) {
      return undefined;
    }

    try {
      const match = context.fileContent.match(new RegExp(versionRegex, 'i'));
      if (match) {
        return match[1] || match[0];
      }
    } catch (error) {
      console.warn('Invalid version regex:', versionRegex, error);
    }

    return undefined;
  }

  /**
   * Extracts key dependencies from the project context
   * @param context - Detection context
   * @returns string[] array of dependency names
   */
  private extractDependencies(context: DetectionContext): string[] {
    const dependencies: string[] = [];

    // Extract from various package managers
    if (context.filePath.includes('package.json')) {
      const depMatches = context.fileContent.match(/"([^"]+)":\s*"[^"]+"/g);
      if (depMatches) {
        dependencies.push(...depMatches.map(match => match.split('"')[1]));
      }
    }

    if (context.filePath.includes('go.mod')) {
      const depMatches = context.fileContent.match(/^\s*([^\s]+)\s+v/gm);
      if (depMatches) {
        dependencies.push(
          ...depMatches.map(match => match.trim().split(' ')[0])
        );
      }
    }

    if (context.filePath.includes('composer.json')) {
      const depMatches = context.fileContent.match(
        /"([^"]+\/[^"]+)":\s*"[^"]+"/g
      );
      if (depMatches) {
        dependencies.push(...depMatches.map(match => match.split('"')[1]));
      }
    }

    return dependencies.slice(0, 10); // Limit to first 10 dependencies
  }

  /**
   * Finds configuration files in the project context
   * @param context - Detection context
   * @returns string[] array of config file names
   */
  private findConfigFiles(context: DetectionContext): string[] {
    const configFiles: string[] = [];

    if (context.allFiles) {
      const configPatterns = [
        'package.json',
        'composer.json',
        'go.mod',
        'pom.xml',
        'build.gradle',
        '.env',
        'config.json',
        'config.yml',
        'config.yaml',
        'docker-compose.yml',
        'Dockerfile',
        'Makefile',
      ];

      for (const file of context.allFiles) {
        const fileName = path.basename(file);
        if (configPatterns.includes(fileName)) {
          configFiles.push(fileName);
        }
      }
    }

    return configFiles;
  }

  /**
   * Clears the internal pattern cache
   */
  clearCache(): void {
    PatternMatchingUtils.clearCache();
  }
}
