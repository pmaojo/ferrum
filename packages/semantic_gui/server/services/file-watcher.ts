import { EventEmitter } from 'events';
import { relative, extname } from 'path';

import type { FSWatcher } from 'chokidar';
import { watch } from 'chokidar';

export interface FileChangeEvent {
  type: 'add' | 'change' | 'unlink';
  path: string;
  relativePath: string;
  isGoFile: boolean;
  timestamp: Date;
}

export class FileWatcher extends EventEmitter {
  private watchers: Map<string, FSWatcher> = new Map();
  private watchedPaths: Set<string> = new Set();

  /**
   * Start watching a directory for Go file changes
   */
  watchDirectory(path: string, projectId: string): void {
    if (this.watchedPaths.has(path)) {
      console.log(`Already watching ${path}`);
      return;
    }

    const watcher = watch(path, {
      ignored: [
        '**/node_modules/**',
        '**/.git/**',
        '**/vendor/**',
        '**/*.log',
        '**/*.tmp',
        '**/.*',
      ],
      persistent: true,
      ignoreInitial: true,
      followSymlinks: false,
      depth: 10,
    });

    watcher
      .on('add', filePath =>
        this.handleFileEvent('add', filePath, path, projectId)
      )
      .on('change', filePath =>
        this.handleFileEvent('change', filePath, path, projectId)
      )
      .on('unlink', filePath =>
        this.handleFileEvent('unlink', filePath, path, projectId)
      )
      .on('error', error => {
        console.error(`File watcher error for ${path}:`, error);
        this.emit('error', { path, error, projectId });
      });

    this.watchers.set(path, watcher);
    this.watchedPaths.add(path);

    console.log(`Started watching ${path} for project ${projectId}`);
  }

  /**
   * Stop watching a specific directory
   */
  unwatchDirectory(path: string): void {
    const watcher = this.watchers.get(path);
    if (watcher) {
      watcher.close();
      this.watchers.delete(path);
      this.watchedPaths.delete(path);
      console.log(`Stopped watching ${path}`);
    }
  }

  /**
   * Stop all watchers
   */
  unwatchAll(): void {
    this.watchers.forEach((watcher, path) => {
      watcher.close();
      console.log(`Stopped watching ${path}`);
    });
    this.watchers.clear();
    this.watchedPaths.clear();
  }

  /**
   * Get list of watched paths
   */
  getWatchedPaths(): string[] {
    return Array.from(this.watchedPaths);
  }

  /**
   * Check if a path is being watched
   */
  isWatching(path: string): boolean {
    return this.watchedPaths.has(path);
  }

  private handleFileEvent(
    type: 'add' | 'change' | 'unlink',
    filePath: string,
    basePath: string,
    projectId: string
  ): void {
    const relativePath = relative(basePath, filePath);
    const isGoFile = extname(filePath) === '.go';

    // Only emit events for Go files or important config files
    if (!isGoFile && !this.isImportantFile(filePath)) {
      return;
    }

    const event: FileChangeEvent = {
      type,
      path: filePath,
      relativePath,
      isGoFile,
      timestamp: new Date(),
    };

    console.log(`File ${type}: ${relativePath} (Go: ${isGoFile})`);

    this.emit('fileChange', {
      ...event,
      projectId,
    });

    // Emit specific events for different file types
    if (isGoFile) {
      this.emit('goFileChange', {
        ...event,
        projectId,
      });

      // Emit module-specific events
      if (this.isModuleFile(relativePath)) {
        this.emit('moduleFileChange', {
          ...event,
          projectId,
          moduleName: this.extractModuleName(relativePath),
        });
      }
    }
  }

  private isImportantFile(filePath: string): boolean {
    const importantFiles = [
      'go.mod',
      'go.sum',
      'Makefile',
      'docker-compose.yml',
      'Dockerfile',
    ];

    const fileName = filePath.split('/').pop() || '';
    return importantFiles.includes(fileName);
  }

  private isModuleFile(relativePath: string): boolean {
    return (
      relativePath.includes('internal/modules/') && relativePath.endsWith('.go')
    );
  }

  private extractModuleName(relativePath: string): string {
    const parts = relativePath.split('/');
    const moduleIndex = parts.indexOf('modules');

    if (moduleIndex !== -1 && moduleIndex + 1 < parts.length) {
      const moduleFile = parts[moduleIndex + 1];
      return moduleFile.replace('.go', '');
    }

    return 'unknown';
  }
}

// Singleton instance for global use
export const fileWatcher = new FileWatcher();
