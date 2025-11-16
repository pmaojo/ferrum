import { spawn } from 'child_process';
import { randomBytes } from 'crypto';
import { promises as fs } from 'fs';
import { tmpdir } from 'os';
import path from 'path';

export interface GeneratedFile {
  path: string;
  content: string;
}

export interface FileDiff {
  filePath: string;
  oldContent: string;
  newContent: string;
  diff: string;
  truncated: boolean;
}

export interface DiffOptions {
  maxFileSize?: number;
  maxHunks?: number;
}

export class DiffService {
  async generateDiffs(
    projectPath: string,
    files: GeneratedFile[],
    options: DiffOptions = {}
  ): Promise<FileDiff[]> {
    const { maxFileSize = Infinity, maxHunks = Infinity } = options;
    const diffs: FileDiff[] = [];

    for (const file of files) {
      const targetPath = path.join(projectPath, file.path);
      let oldContent = '';
      try {
        oldContent = await fs.readFile(targetPath, 'utf8');
      } catch {
        oldContent = '';
      }

      const oldSize = Buffer.byteLength(oldContent, 'utf8');
      const newSize = Buffer.byteLength(file.content, 'utf8');
      let truncated = false;
      let diff = '';

      if (oldSize <= maxFileSize && newSize <= maxFileSize) {
        const tmpFile = path.join(
          tmpdir(),
          `scaffold-${randomBytes(6).toString('hex')}`
        );
        await fs.mkdir(path.dirname(tmpFile), { recursive: true });
        await fs.writeFile(tmpFile, file.content, 'utf8');

        try {
          diff = await new Promise<string>(resolve => {
            const child = spawn('git', [
              'diff',
              '--no-index',
              '--unified=3',
              '--no-color',
              '--',
              targetPath,
              tmpFile,
            ]);
            let out = '';
            child.stdout.on('data', d => (out += d.toString()));
            child.on('close', () => resolve(out));
            child.on('error', () => resolve(''));
          });
        } finally {
          await fs.unlink(tmpFile).catch(() => {});
        }

        const normalizedPath = file.path.replace(/\\/g, '/');
        diff = diff
          .replace(
            /^diff --git a\/.* b\/.*$/m,
            `diff --git a/${normalizedPath} b/${normalizedPath}`
          )
          .replace(/^--- a\/.*$/m, `--- a/${normalizedPath}`)
          .replace(/^\+\+\+ b\/.*$/m, `+++ b/${normalizedPath}`);

        if (maxHunks !== Infinity) {
          const lines = diff.split('\n');
          const result: string[] = [];
          let hunkCount = 0;
          for (const line of lines) {
            if (line.startsWith('@@')) {
              hunkCount++;
              if (hunkCount > maxHunks) {
                truncated = true;
                break;
              }
            }
            result.push(line);
          }
          diff = result.join('\n');
        }
      } else {
        truncated = true;
      }

      diffs.push({
        filePath: file.path,
        oldContent,
        newContent: file.content,
        diff,
        truncated,
      });
    }

    return diffs;
  }
}

export default DiffService;
