import express from 'express';
import request from 'supertest';

import { registerRoutes } from '../server/routes';

import { MockStorage } from './mock-storage';

process.env.GROQ_API_KEY = 'test';

describe('routes integration', () => {
  test('POST /api/v1/nodes validates and creates node', async () => {
    const app = express();
    app.use(express.json());
    await registerRoutes(app, new MockStorage());

    const payload = {
      name: 'MyService',
      type: 'service',
      position: { x: 0, y: 0 },
      templateId: 'tmpl1',
      projectId: 'proj1',
      metadata: { decorators: ['Injectable'] },
    };

    const res = await request(app).post('/api/v1/nodes').send(payload);
    expect(res.status).toBe(200);
    expect(res.body.name).toBe('MyService');
    expect(res.body.id).toBeDefined();
    expect(res.body.filePath).toBe('src/services/MyService.service.ts');
  });

  test('POST /api/v1/nodes returns 404 when template missing', async () => {
    const storage = new MockStorage();
    delete storage.templates['tmpl1'];
    const app = express();
    app.use(express.json());
    await registerRoutes(app, storage);

    const payload = {
      name: 'MyService',
      type: 'service',
      position: { x: 0, y: 0 },
      templateId: 'tmpl1',
      projectId: 'proj1',
    };

    const res = await request(app).post('/api/v1/nodes').send(payload);
    expect(res.status).toBe(404);
  });
});
