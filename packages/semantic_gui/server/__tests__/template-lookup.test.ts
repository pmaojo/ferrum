import express from 'express';
import request from 'supertest';

import { registerRoutes } from '../routes';

describe('template lookup', () => {
  let app: express.Express;
  const mockStorage = {
    getTemplate: jest.fn().mockResolvedValue(undefined),
  } as any;

  beforeAll(async () => {
    app = express();
    app.use(express.json());
    await registerRoutes(app, mockStorage);
  });

  const ids = ['kthulu-hexagonal', 'enhanced-kthulu', 'laravel-hexagonal'];

  test.each(ids)('GET /api/v1/templates/%s', async id => {
    const res = await request(app).get(`/api/v1/templates/${id}`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(id);
    expect(mockStorage.getTemplate).toHaveBeenCalledWith(id);
  });
});
