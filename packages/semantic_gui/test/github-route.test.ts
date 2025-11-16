import express from 'express';
import request from 'supertest';

import { registerRoutes } from '../server/routes';

import { MockStorage } from './mock-storage';

process.env.GROQ_API_KEY = 'test';

describe('github route', () => {
  test('POST /api/v1/projects/:projectId/analyze-github requires repoUrl', async () => {
    const app = express();
    app.use(express.json());
    await registerRoutes(app, new MockStorage());

    const res = await request(app)
      .post('/api/v1/projects/proj1/analyze-github')
      .send({});

    expect(res.status).toBe(400);
  });
});
