import fs from 'fs';
import path from 'path';

import type { GeneratedFile, FileDiff } from './diff/DiffService';
import DiffService from './diff/DiffService';

export class ProjectFS {
  constructor(private projectRoot: string) {}

  private resolveSafe(filePath: string): string {
    const normalized = path.normalize(filePath);
    if (normalized.split(path.sep).includes('..')) {
      const err: any = new Error('Access outside project root');
      err.status = 403;
      throw err;
    }
    const resolved = path.resolve(this.projectRoot, normalized);
    let realPath: string;
    try {
      realPath = fs.realpathSync(resolved);
    } catch {
      const dir = path.dirname(resolved);
      const realDir = fs.realpathSync(dir);
      realPath = path.join(realDir, path.basename(resolved));
    }
    const rel = path.relative(this.projectRoot, realPath);
    if (rel.startsWith('..') || path.isAbsolute(rel)) {
      const err: any = new Error('Access outside project root');
      err.status = 403;
      throw err;
    }
    return realPath;
  }

  async readFile(filePath: string): Promise<string> {
    const target = this.resolveSafe(filePath);
    return fs.promises.readFile(target, 'utf8');
  }

  async applyChanges(
    files: GeneratedFile[],
    dryRun: boolean
  ): Promise<FileDiff[]> {
    // validate paths first
    for (const f of files) {
      this.resolveSafe(f.path);
    }
    const diffService = new DiffService();
    const diffs = await diffService.generateDiffs(this.projectRoot, files);
    if (!dryRun) {
      await this.createCheckpoint(files);
      for (const file of files) {
        const target = this.resolveSafe(file.path);
        await fs.promises.mkdir(path.dirname(target), { recursive: true });
        await fs.promises.writeFile(target, file.content, 'utf8');
      }
    }
    return diffs;
  }

  private async createCheckpoint(files: GeneratedFile[]): Promise<void> {
    const checkpointDir = path.join(this.projectRoot, '.scg');
    await fs.promises.mkdir(checkpointDir, { recursive: true });
    const rollbackData: GeneratedFile[] = [];
    for (const f of files) {
      const target = this.resolveSafe(f.path);
      try {
        const content = await fs.promises.readFile(target, 'utf8');
        rollbackData.push({ path: f.path, content });
      } catch {
        rollbackData.push({ path: f.path, content: '' });
      }
    }
    await fs.promises.writeFile(
      path.join(checkpointDir, 'rollback.json'),
      JSON.stringify(rollbackData, null, 2),
      'utf8'
    );
  }

  async rollback(): Promise<void> {
    const file = path.join(this.projectRoot, '.scg', 'rollback.json');
    let data: GeneratedFile[];
    try {
      data = JSON.parse(await fs.promises.readFile(file, 'utf8'));
    } catch {
      const err: any = new Error('No rollback data');
      err.status = 404;
      throw err;
    }
    for (const f of data) {
      const target = this.resolveSafe(f.path);
      if (f.content) {
        await fs.promises.mkdir(path.dirname(target), { recursive: true });
        await fs.promises.writeFile(target, f.content, 'utf8');
      } else {
        await fs.promises.rm(target, { force: true });
      }
    }
    await fs.promises.rm(file, { force: true });
  }
}

export default ProjectFS;
