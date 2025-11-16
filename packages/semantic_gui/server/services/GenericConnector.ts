import { exec } from 'child_process';
import { EventEmitter } from 'events';
import { readFile, writeFile } from 'fs/promises';
import { join } from 'path';
import { promisify } from 'util';

import type { GraphNode, GraphEdge } from '@shared/schema';

import type { SCGTag } from '../types/universal-tag-system';
import { logger } from '../utils/logger';

import { fileWatcher } from './file-watcher';
import { FrameworkDetector } from './tagging/FrameworkDetector';
import { TagExtractor } from './tagging/TagExtractor';
import { TagTranslator } from './tagging/TagTranslator';

const execAsync = promisify(exec);

export interface ConnectorConfig {
  type: string;
  parser?: string;
  fileWatcher?: {
    patterns: string[];
    excludes?: string[];
    events: string[];
  };
  analysis?: {
    graphCommand?: string;
    outputPath?: string;
    structureCommand?: string;
    validationCommand?: string;
  };
  paths?: {
    projectRoot: string;
    backendPath?: string;
    cliPath?: string;
    tempDir?: string;
  };
  scgMapping?: {
    nodePositioning?: Record<string, { baseX: number; baseY: number }>;
    componentTypes?: Record<string, string>;
  };
}

export interface ProjectStructure {
  path: string;
  name: string;
  elements: ArchitecturalElement[];
  dependencies: ProjectDependency[];
}

export interface ArchitecturalElement {
  id: string;
  name: string;
  type: string;
  filePath: string;
  packagePath?: string;
  dependencies: string[];
  implements: string[];
  metadata: Record<string, any>;
}

export interface ProjectDependency {
  source: string;
  target: string;
  type: 'depends' | 'calls' | 'implements' | 'uses';
}

export class GenericConnector extends EventEmitter {
  private projectPath: string;
  private projectId: string;
  private config: ConnectorConfig;
  private templateId: string;
  private tagExtractor = new TagExtractor();
  private tagTranslator = new TagTranslator();
  private frameworkDetector = new FrameworkDetector();

  constructor(
    config: ConnectorConfig,
    projectPath: string,
    templateId: string,
    projectId?: string
  ) {
    super();
    this.config = config;
    this.projectPath = projectPath;
    this.templateId = templateId;
    this.projectId = projectId || 'default';
  }

  /**
   * Execute CLI commands based on template configuration
   */
  async executeCommand(command: string, args: string[] = []): Promise<string> {
    try {
      const cliPath = this.config.paths?.cliPath
        ? join(this.projectPath, this.config.paths.cliPath)
        : this.projectPath;

      const fullCommand = this.config.paths?.cliPath?.includes('go')
        ? `cd ${cliPath} && go run main.go ${command} ${args.join(' ')}`
        : `${command} ${args.join(' ')}`;

      const { stdout, stderr } = await execAsync(fullCommand, {
        cwd: this.projectPath,
      });

      if (stderr && !stderr.includes('warning')) {
        throw new Error(`CLI error: ${stderr}`);
      }

      return stdout;
    } catch (error) {
      logger.error('Failed to execute command', {
        operation: command,
        error: (error as Error).message,
      });
      throw new Error(`Failed to execute command: ${(error as Error).message}`);
    }
  }

  /**
   * Auto-detect framework and extract SCG tags for a given file
   */
  async extractSCGTags(filePath: string): Promise<SCGTag[]> {
    try {
      const absPath = join(this.projectPath, filePath);
      const code = await readFile(absPath, 'utf-8');

      // Detect framework using available templates
      const detection = await this.frameworkDetector.detectFramework(
        code,
        absPath,
        this.projectPath
      );

      const templateId =
        detection.templateId && detection.templateId !== 'unknown'
          ? detection.templateId
          : this.templateId;

      // Extract native and convention tags then translate to SCG
      const native = await this.tagExtractor.extractNativeTags(
        code,
        templateId,
        absPath
      );
      const convention = await this.tagExtractor.extractConventionTags(
        code,
        templateId,
        absPath
      );
      const translation = await this.tagTranslator.translateToSCG(
        [...native, ...convention],
        templateId
      );

      return translation.translatedTags;
    } catch (error) {
      logger.error('Failed to extract SCG tags', {
        operation: 'extractSCGTags',
        error: (error as Error).message,
      });
      return [];
    }
  }

  /**
   * Generate architecture graph using template-defined command
   */
  async generateArchitectureGraph(): Promise<any> {
    if (!this.config.analysis?.graphCommand) {
      throw new Error('Graph command not defined in template');
    }

    try {
      const [command, ...args] = this.config.analysis.graphCommand.split(' ');
      await this.executeCommand(command, args);

      if (this.config.analysis.outputPath) {
        const graphData = await readFile(
          this.config.analysis.outputPath,
          'utf-8'
        );
        return JSON.parse(graphData);
      }

      return { nodes: [], edges: [] };
    } catch (error) {
      logger.error('Failed to generate architecture graph', {
        operation: 'generateArchitectureGraph',
        error: (error as Error).message,
      });
      throw new Error(
        `Failed to generate architecture graph: ${(error as Error).message}`
      );
    }
  }

  /**
   * Validate architecture using template-defined command
   */
  async validateArchitecture(): Promise<any> {
    if (!this.config.analysis?.validationCommand) {
      return { valid: true, message: 'No validation command defined' };
    }

    try {
      const [command, ...args] =
        this.config.analysis.validationCommand.split(' ');
      const output = await this.executeCommand(command, args);
      return { valid: true, output };
    } catch (error) {
      logger.error('Failed to validate architecture', {
        operation: 'validateArchitecture',
        error: (error as Error).message,
      });
      return { valid: false, error: (error as Error).message };
    }
  }

  /**
   * Analyze project structure using template configuration
   */
  async analyzeCodeStructure(): Promise<ProjectStructure> {
    try {
      // This would use the parser specified in template config
      // For now, we'll return a basic structure
      const elements: ArchitecturalElement[] = [];
      const dependencies: ProjectDependency[] = [];

      // If structure command is defined, use it
      if (this.config.analysis?.structureCommand) {
        const [command, ...args] =
          this.config.analysis.structureCommand.split(' ');
        const output = await this.executeCommand(command, args);

        // Parse the output based on template configuration
        // This would be extended based on the parser type
        try {
          const parsed = JSON.parse(output);
          // Transform parsed data to our format
          if (parsed.elements) {
            elements.push(...parsed.elements);
          }
          if (parsed.dependencies) {
            dependencies.push(...parsed.dependencies);
          }
        } catch {
          // If not JSON, handle as text output
          logger.warn('Structure command output is not JSON, using fallback');
        }
      }

      return {
        path: this.projectPath,
        name: 'Generic Project',
        elements,
        dependencies,
      };
    } catch (error) {
      logger.error('Failed to analyze code structure', {
        operation: 'analyzeCodeStructure',
        error: (error as Error).message,
      });
      throw new Error(
        `Failed to analyze code structure: ${(error as Error).message}`
      );
    }
  }

  /**
   * Convert project structure to SCG graph format using template mapping
   */
  async convertToSCGGraph(
    projectId: string
  ): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
    try {
      const structure = await this.analyzeCodeStructure();
      const nodes: GraphNode[] = [];
      const edges: GraphEdge[] = [];

      // Convert elements to SCG nodes using template configuration
      for (const [index, element] of structure.elements.entries()) {
        const position = this.calculateNodePosition(element, index);
        const componentType = this.getComponentType(element.type);
        const tags = await this.extractSCGTags(element.filePath);
        const framework = tags[0]?.framework;

        const node: GraphNode = {
          id: element.id,
          name: element.name,
          type: element.type,
          filePath: element.filePath,
          description: `${element.type}: ${element.name}`,
          position,
          metadata: {
            packagePath: element.packagePath,
            componentType,
            framework,
            scgTags: tags,
            ...element.metadata,
          },
          templateId: this.templateId,
          projectId,
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        nodes.push(node);
      }

      // Create edges based on dependencies
      structure.dependencies.forEach((dep, depIndex) => {
        const edge: GraphEdge = {
          id: `dep-${dep.source}-${dep.target}-${depIndex}`,
          sourceNodeId: dep.source,
          targetNodeId: dep.target,
          type: dep.type,
          metadata: {
            dependencyType: dep.type,
          },
          projectId,
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        edges.push(edge);
      });

      return { nodes, edges };
    } catch (error) {
      logger.error('Failed to convert to SCG graph', {
        operation: 'convertToSCGGraph',
        error: (error as Error).message,
      });
      throw new Error(
        `Failed to convert to SCG graph: ${(error as Error).message}`
      );
    }
  }

  /**
   * Start file system watcher based on template configuration
   */
  async startFileWatcher(): Promise<void> {
    if (!this.config.fileWatcher) {
      logger.info('No file watcher configuration found in template');
      return;
    }

    const watchPath = this.config.paths?.backendPath
      ? join(this.projectPath, this.config.paths.backendPath)
      : this.projectPath;

    try {
      // Set up file watcher event listeners based on template events
      this.config.fileWatcher.events.forEach(eventName => {
        fileWatcher.on(eventName, event => {
          if (event.projectId === this.projectId) {
            this.emit(eventName, event);
          }
        });
      });

      // Start watching the directory
      fileWatcher.watchDirectory(watchPath, this.projectId);

      logger.info('Started file watcher for project', {
        operation: 'startFileWatcher',
        projectPath: this.projectPath,
        patterns: this.config.fileWatcher.patterns,
      });
    } catch (error) {
      logger.error('File watcher error', {
        operation: 'startFileWatcher',
        error: (error as Error).message,
      });
      throw error;
    }
  }

  /**
   * Stop file watcher
   */
  stopFileWatcher(): void {
    const watchPath = this.config.paths?.backendPath
      ? join(this.projectPath, this.config.paths.backendPath)
      : this.projectPath;

    fileWatcher.unwatchDirectory(watchPath);
    fileWatcher.removeAllListeners();
  }

  /**
   * Apply code changes suggested by agents
   */
  async applyCodeChanges(
    changes: Array<{
      file: string;
      content: string;
      type: 'create' | 'update' | 'delete';
    }>
  ): Promise<void> {
    for (const change of changes) {
      const filePath = join(this.projectPath, change.file);

      try {
        switch (change.type) {
          case 'create':
          case 'update':
            await writeFile(filePath, change.content, 'utf-8');
            break;
          case 'delete':
            // Implementation for file deletion would go here
            break;
        }

        this.emit('codeApplied', { file: change.file, type: change.type });
      } catch (error) {
        this.emit('codeError', {
          file: change.file,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    }
  }

  // Private helper methods using template configuration
  private calculateNodePosition(
    element: ArchitecturalElement,
    index: number
  ): { x: number; y: number } {
    const positioning = this.config.scgMapping?.nodePositioning;

    if (positioning?.[element.type]) {
      const { baseX, baseY } = positioning[element.type];
      return {
        x: baseX + (index % 5) * 250,
        y: baseY + Math.floor(index / 5) * 150,
      };
    }

    // Default positioning
    const baseX = (index % 5) * 250;
    const baseY = Math.floor(index / 5) * 150;
    return { x: baseX, y: baseY };
  }

  private getComponentType(elementType: string): string {
    const componentTypes = this.config.scgMapping?.componentTypes;

    if (componentTypes?.[elementType]) {
      return componentTypes[elementType];
    }

    // Default mapping
    switch (elementType) {
      case 'usecase':
      case 'entity':
      case 'port':
        return 'domain';
      case 'adapter':
      case 'handler':
        return 'infrastructure';
      case 'service':
        return 'application';
      default:
        return 'unknown';
    }
  }
}
