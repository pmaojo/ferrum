/** @jest-environment node */
import { promises as fs } from 'fs';
import { tmpdir } from 'os';
import path from 'path';

import type { GeneratedFile } from '../DiffService';
import DiffService from '../DiffService';

describe('DiffService', () => {
  const service = new DiffService();

  async function createTempProject() {
    return fs.mkdtemp(path.join(tmpdir(), 'diff-service-'));
  }

  it('generates deterministic git-style diffs', async () => {
    const project = await createTempProject();
    const filePath = 'file.txt';
    await fs.mkdir(path.join(project, path.dirname(filePath)), {
      recursive: true,
    });
    await fs.writeFile(
      path.join(project, filePath),
      'line1\nline2\nline3\n',
      'utf8'
    );

    const files: GeneratedFile[] = [
      {
        path: filePath,
        content: 'line1\nlineX\nline3\n',
      },
    ];

    const first = await service.generateDiffs(project, files);
    const second = await service.generateDiffs(project, files);

    expect(first[0].diff).toBe(second[0].diff);
    expect(first[0].truncated).toBe(false);
    expect(first[0].diff).toContain('@@');
  });

  it('marks diffs as truncated when file size limit is exceeded', async () => {
    const project = await createTempProject();
    const filePath = 'big.txt';
    await fs.writeFile(path.join(project, filePath), '', 'utf8');

    const files: GeneratedFile[] = [
      { path: filePath, content: 'a'.repeat(20) },
    ];

    const [result] = await service.generateDiffs(project, files, {
      maxFileSize: 10,
    });

    expect(result.truncated).toBe(true);
    expect(result.diff).toBe('');
  });

  it('truncates diff when hunk limit is exceeded', async () => {
    const project = await createTempProject();
    const filePath = 'multi.txt';
    await fs.writeFile(
      path.join(project, filePath),
      `${['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8', 'a9', 'a10'].join(
        '\n'
      )}\n`,
      'utf8'
    );

    const newContent = `${[
      'b1',
      'a2',
      'a3',
      'a4',
      'a5',
      'a6',
      'a7',
      'a8',
      'a9',
      'b10',
    ].join('\n')}\n`;
    const files: GeneratedFile[] = [{ path: filePath, content: newContent }];

    const [result] = await service.generateDiffs(project, files, {
      maxHunks: 1,
    });

    expect(result.truncated).toBe(true);
    const hunkCount = result.diff
      .split('\n')
      .filter(l => l.startsWith('@@')).length;
    expect(hunkCount).toBe(1);
  });
});
