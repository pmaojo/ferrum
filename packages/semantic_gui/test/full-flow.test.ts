/** @jest-environment node */
import { spawn } from 'child_process';
import fs from 'fs/promises';
import { createServer } from 'http';
import { tmpdir } from 'os';
import path from 'path';

import express from 'express';
import request from 'supertest';
import { WebSocket, RawData } from 'ws';

import { attachPermaGraphRoutes } from '../server/routes/permagraphRoutes';
import { attachProjectRoutes } from '../server/routes/projectsRoutes';
import { WebSocketManager } from '../server/services/websocket-manager';

import { MockStorage } from './mock-storage';

function waitForWs<T>(
  ws: WebSocket,
  predicate: (data: any) => boolean
): Promise<T> {
  return new Promise<T>(resolve => {
    const handler = (raw: RawData) => {
      const msg = JSON.parse(raw.toString());
      if (predicate(msg)) {
        ws.off('message', handler);
        resolve(msg);
      }
    };
    ws.on('message', handler);
  });
}

describe('full workflow integration', () => {
  let server: any;
  let baseUrl: string;
  let storage: MockStorage;

  beforeAll(async () => {
    storage = new MockStorage();
    storage.templates['test-template'] = {
      id: 'test-template',
      name: 'Test Template',
      description: '',
      nodeTypes: [],
      validationRules: [],
      metadata: {},
      cli: {
        operations: {
          'make:module': {
            command: `node -e "console.log(JSON.stringify([{path:'src/TestModule.ts',content:'export const test = 1;\\n'}]))"`,
            description: 'Generate module',
          },
          planGraph: {
            command: `node -e "console.log(JSON.stringify({nodes:[{name:'TestModule',type:'module',templateId:'test-template',position:{x:0,y:0}}],edges:[]}))"`,
            description: 'Plan graph',
          },
        },
      },
    } as any;

    const app = express();
    app.use(express.json());
    attachPermaGraphRoutes(app, storage);
    attachProjectRoutes(app, storage);
    app.post('/api/v1/projects/:id/cli/execute', async (req, res) => {
      const { id } = req.params as any;
      const { operation } = req.body as any;
      const project = await storage.getProject(id);
      const template = await storage.getTemplate(project!.templateId);
      const cmd = template!.cli.operations[operation].command;
      const child = spawn(cmd, { cwd: project!.projectPath, shell: true });
      let stdout = '';
      child.stdout.on('data', d => (stdout += d.toString()));
      await new Promise(r => child.on('close', r));
      res.json({ stdout, exitCode: 0 });
    });
    server = createServer(app);
    const wsManager = new WebSocketManager(server);
    app.set('wsManager', wsManager);
    await new Promise<void>(resolve => server.listen(0, resolve));
    const address = server.address();
    baseUrl = `http://127.0.0.1:${(address as any).port}`;
  });

  afterAll(async () => {
    await new Promise<void>(resolve => server.close(() => resolve()));
  });

  it('creates project, scaffolds module and runs validation', async () => {
    const tmp = await fs.mkdtemp(path.join(tmpdir(), 'proj-'));

    const createRes = await request(baseUrl)
      .post('/api/v1/projects/create')
      .send({
        name: 'Proj',
        templateId: 'test-template',
        projectPath: tmp,
      });
    expect(createRes.status).toBe(200);
    const projectId = createRes.body.id;
    storage.projects[projectId].projectPath = tmp;

    const ws = new WebSocket(baseUrl.replace('http', 'ws'));
    await new Promise(resolve => ws.on('open', resolve));
    ws.send(JSON.stringify({ type: 'subscribe', projectId }));

    const diffRes = await request(baseUrl)
      .post(`/api/v1/projects/${projectId}/scaffold/module`)
      .send({ name: 'TestModule' });
    expect(diffRes.status).toBe(200);
    const diff = diffRes.body.diffs[0];
    expect(diff.filePath).toBe('src/TestModule.ts');

    const graphEvt = waitForWs(ws, m => m.type === 'graph.updated');

    const applyRes = await request(baseUrl)
      .post(`/api/v1/projects/${projectId}/apply`)
      .send({ files: [{ path: diff.filePath, content: diff.newContent }] });
    expect(applyRes.status).toBe(200);
    expect(applyRes.body.applied).toBe(1);

    await graphEvt;

    const validateRes = await request(baseUrl)
      .post(`/api/v1/projects/${projectId}/validate`)
      .send();
    expect(validateRes.status).toBe(200);
    expect(Array.isArray(validateRes.body.validationResults)).toBe(true);

    ws.close();
    await fs.rm(tmp, { recursive: true, force: true });
  });
});
