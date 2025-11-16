import { promises as fs } from 'fs';
import path from 'path';

export class ProjectFS {
  constructor(private projectRoot: string) {}

  private async resolveSafe(p: string): Promise<string> {
    const normalized = path.normalize(p);
    if (normalized.split(path.sep).includes('..')) {
      const err: any = new Error('Path outside project root');
      err.status = 403;
      throw err;
    }
    const resolved = path.resolve(this.projectRoot, normalized);
    let real: string;
    try {
      real = await fs.realpath(resolved);
    } catch {
      const dir = path.dirname(resolved);
      const realDir = await fs.realpath(dir);
      real = path.join(realDir, path.basename(resolved));
    }
    const rel = path.relative(this.projectRoot, real);
    if (rel.startsWith('..') || path.isAbsolute(rel)) {
      const err: any = new Error('Path outside project root');
      err.status = 403;
      throw err;
    }
    return real;
  }

  async readFile(
    p: string,
    encoding: BufferEncoding = 'utf8'
  ): Promise<string> {
    const filePath = await this.resolveSafe(p);
    return fs.readFile(filePath, encoding);
  }

  async writeFile(
    p: string,
    data: string | NodeJS.ArrayBufferView
  ): Promise<void> {
    const filePath = await this.resolveSafe(p);
    await fs.mkdir(path.dirname(filePath), { recursive: true });
    await fs.writeFile(filePath, data);
  }
}
