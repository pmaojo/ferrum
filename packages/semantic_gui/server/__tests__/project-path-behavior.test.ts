import fs from 'fs';
import os from 'os';
import path from 'path';

import express from 'express';
import request from 'supertest';

import type { Project } from '@shared/schema';
import { attachProjectRoutes } from '../routes/projectsRoutes';
import cliRoutes from '../routes/cliRoutes';
import { MockStorage } from '../../test/mock-storage';
import { TemplateService } from '../services/TemplateService';

jest.mock('../middleware/auth', () => ({
  authMiddleware: (_req: express.Request, _res: express.Response, next: express.NextFunction) =>
    next(),
}));
jest.mock('../middleware/requireRole', () => ({
  requireRole: () =>
    (_req: express.Request, _res: express.Response, next: express.NextFunction) => next(),
}));

describe('project path persistence', () => {
  let tmpDir: string;
  let storage: MockStorage;
  let project: Project;
  let app: express.Express;

  beforeEach(async () => {
    tmpDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'project-path-'));
    storage = new MockStorage();
    project = await storage.createProject({
      name: 'Project',
      templateId: 'tmpl1',
      projectPath: tmpDir,
      metadata: {},
    } as any);

    app = express();
    app.use(express.json());
    app.set('storage', storage as any);
    app.set('permagraphControllers', new Map());
    app.set('wsManager', {
      broadcast: jest.fn(),
      unsubscribeProject: jest.fn(),
    });

    attachProjectRoutes(app, storage as any);
  });

  afterEach(async () => {
    jest.restoreAllMocks();
    await fs.promises.rm(tmpDir, { recursive: true, force: true });
  });

  it('reads project files from the stored root directory', async () => {
    const samplePath = path.join(tmpDir, 'README.md');
    await fs.promises.mkdir(path.dirname(samplePath), { recursive: true });
    await fs.promises.writeFile(samplePath, 'hello world');

    const res = await request(app).get(`/projects/${project.id}/files/README.md`);
    expect(res.status).toBe(200);
    expect(res.text).toBe('hello world');
  });

  it('writes files within the stored root when applying changes', async () => {
    const mockFetch = jest
      .spyOn(global, 'fetch')
      .mockResolvedValue({ ok: true, json: async () => ({}) } as any);

    const res = await request(app)
      .post(`/projects/${project.id}/apply`)
      .send({ files: [{ path: 'src/index.ts', content: 'export const value = 1;' }] });

    expect(res.status).toBe(200);
    const written = await fs.promises.readFile(path.join(tmpDir, 'src/index.ts'), 'utf8');
    expect(written).toContain('export const value = 1;');
    expect(mockFetch).toHaveBeenCalled();
  });

  it('passes the persisted project path to CLI executions', async () => {
    const mockExecutor = {
      execute: jest.fn().mockResolvedValue({ exitCode: 0, stdout: '', stderr: '' }),
    };
    app.set('cliExecutor', mockExecutor);

    const templateSpy = jest
      .spyOn(TemplateService.prototype, 'getTemplate')
      .mockResolvedValue({
        id: project.templateId,
        cli: {
          operations: {
            planGraph: {
              command: 'echo planGraph',
            },
          },
        },
      } as any);

    app.use(cliRoutes);

    const res = await request(app)
      .post(`/projects/${project.id}/cli/execute`)
      .set('x-trace-id', 'trace')
      .send({ operation: 'planGraph', args: {} });

    expect(res.status).toBe(200);
    expect(templateSpy).toHaveBeenCalled();
    expect(mockExecutor.execute).toHaveBeenCalledWith(
      project.id,
      'echo planGraph',
      'trace',
      tmpDir
    );
  });
});
