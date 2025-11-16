import express from 'express';
import request from 'supertest';

import { registerRoutes } from '../routes';
import { PermaGraphController } from '../services/permagraph-controller';

process.env.GROQ_API_KEY = 'test';

const mockStorage = {
  listProjects: jest.fn(),
  createProject: jest.fn(),
};

describe('semantic query presets', () => {
  let app: express.Express;

  beforeEach(async () => {
    app = express();
    app.use(express.json());
    await registerRoutes(app, mockStorage as any);
    const controllers = app.get('permagraphControllers') as Map<
      string,
      PermaGraphController
    >;
    controllers.set('test', new PermaGraphController('test'));
  });

  it('lists semantic query presets', async () => {
    const res = await request(app).get(
      '/api/v1/projects/test/semantic/queries'
    );
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.queries)).toBe(true);
  });

  it('executes semantic query preset', async () => {
    const res = await request(app)
      .post('/api/v1/projects/test/semantic/queries/sample')
      .send({});
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('rows');
    expect(Array.isArray(res.body.rows)).toBe(true);
  });
});
