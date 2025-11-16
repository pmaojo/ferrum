import fs from 'fs';
import os from 'os';
import path from 'path';

import express from 'express';
import request from 'supertest';

import { registerRoutes } from '../routes';

process.env.GROQ_API_KEY = 'test';

const mockStorage = {
  listProjects: jest.fn(),
  createProject: jest.fn(),
  getProject: jest.fn(),
};

describe('project routes', () => {
  let app: express.Express;

  beforeEach(() => {
    app = express();
    app.use(express.json());
    registerRoutes(app, mockStorage as any);
  });

  it('GET /api/projects', async () => {
    mockStorage.listProjects.mockResolvedValueOnce([{ id: '1', name: 'proj' }]);
    const res = await request(app).get('/api/v1/projects');
    expect(res.status).toBe(200);
    expect(res.body).toEqual([{ id: '1', name: 'proj' }]);
  });

  it('POST /api/projects/create', async () => {
    mockStorage.createProject.mockResolvedValueOnce({
      id: '2',
      name: 'p',
      description: 'd',
      templateId: 't',
      projectPath: '/tmp/project',
      metadata: {},
    });
    const res = await request(app)
      .post('/api/v1/projects/create')
      .send({
        name: 'p',
        description: 'd',
        templateId: 't',
        projectPath: '/tmp/project',
      });
    expect(res.status).toBe(200);
    expect(mockStorage.createProject).toHaveBeenCalled();
    expect(res.body.id).toBe('2');
  });

  it('GET /api/projects/:id/files/*', async () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'proj-'));
    fs.writeFileSync(path.join(tmp, 'file.txt'), 'hello');
    mockStorage.getProject.mockResolvedValueOnce({
      id: '1',
      projectPath: tmp,
    });
    const res = await request(app).get('/api/v1/projects/1/files/file.txt');
    expect(res.status).toBe(200);
    expect(res.text).toBe('hello');
  });
});
