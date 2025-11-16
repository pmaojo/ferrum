/**
 * @jest-environment node
 */

import express from 'express';
import type { AddressInfo } from 'node:net';
import http from 'node:http';
import request from 'supertest';

describe('multiProjectRoutes integration', () => {
  let server: http.Server;
  let baseUrl: string;
  let lastListQuery: Record<string, any> | undefined;
  let lastActivityQuery: Record<string, any> | undefined;
  let activityResponseStatus = 200;
  let activityResponseBody: any;

  beforeAll(async () => {
    const mockApp = express();
    mockApp.use(express.json());

    mockApp.get('/api/v1/projects', (req, res) => {
      lastListQuery = req.query;
      res.json([
        {
          project_id: 'alpha',
          name: 'Alpha',
          tenant_id: req.query.tenant_id ?? 'default',
        },
      ]);
    });

    mockApp.post('/api/v1/projects', (req, res) => {
      if (req.body.name === 'explode') {
        return res.status(422).json({ error: 'invalid project name' });
      }

      res.status(201).json({
        project_id: 'generated-id',
        name: req.body.name,
      });
    });

    mockApp.get('/api/v1/projects/:projectId', (req, res) => {
      res.json({ project_id: req.params.projectId, name: `Project ${req.params.projectId}` });
    });

    mockApp.get('/api/v1/projects/:projectId/statistics', (req, res) => {
      res.json({ project_id: req.params.projectId, triple_count: 42 });
    });

    mockApp.get('/api/v1/projects/:projectId/activity', (req, res) => {
      lastActivityQuery = req.query;
      if (activityResponseStatus >= 400) {
        return res.status(activityResponseStatus).json(activityResponseBody);
      }

      return res.status(activityResponseStatus).json(
        activityResponseBody ?? {
          project_id: req.params.projectId,
          activity: [],
          total: 0,
        }
      );
    });

    mockApp.get('/api/v1/projects/templates', (_req, res) => {
      res.json([{ template_id: 'tpl-1', name: 'Template' }]);
    });

    mockApp.post('/api/v1/projects/templates', (req, res) => {
      res.status(201).json({ template_id: 'tpl-2', name: req.body.name });
    });

    mockApp.post('/api/v1/projects/compare', (req, res) => {
      res.json({
        project_a: req.body.project_a,
        project_b: req.body.project_b,
        similarity_score: 0.5,
      });
    });

    mockApp.post('/api/v1/projects/bulk', (req, res) => {
      res.json({ ...req.body, processed: req.body.project_ids?.length ?? 0 });
    });

    mockApp.post('/api/v1/projects/:projectId/clone', (req, res) => {
      res.status(201).json({ project_id: `${req.params.projectId}-clone`, name: req.body.name });
    });

    mockApp.put('/api/v1/projects/:projectId', (req, res) => {
      res.json({ project_id: req.params.projectId, ...req.body });
    });

    mockApp.post('/api/v1/projects/:projectId/archive', (_req, res) => {
      res.status(204).send();
    });

    mockApp.delete('/api/v1/projects/:projectId', (_req, res) => {
      res.status(204).send();
    });

    mockApp.get('/api/v1/tenants/:tenantId/projects', (req, res) => {
      res.json([
        {
          project_id: 'tenant-project',
          tenant_id: req.params.tenantId,
          status: req.query.status ?? 'active',
        },
      ]);
    });

    server = mockApp.listen(0);
    await new Promise(resolve => server.once('listening', resolve));

    const address = server.address() as AddressInfo;
    baseUrl = `http://127.0.0.1:${address.port}`;
  });

  afterAll(async () => {
    await new Promise(resolve => server.close(resolve));
  });

  afterEach(() => {
    lastListQuery = undefined;
    lastActivityQuery = undefined;
    activityResponseStatus = 200;
    activityResponseBody = undefined;
  });

  const createApp = async () => {
    jest.resetModules();
    process.env.PERMAGRAPH_API_URL = baseUrl;
    const { default: multiProjectRoutes } = await import('../routes/multiProjectRoutes');
    const app = express();
    app.use(express.json());
    app.use('/', multiProjectRoutes);
    return app;
  };

  it('lists projects using the PermaGraph API filters', async () => {
    const app = await createApp();

    const response = await request(app).get(
      '/?tenant_id=tenant-a&status=active&owner=jane&tags=core,api'
    );

    expect(response.status).toBe(200);
    expect(response.body.projects).toHaveLength(1);
    expect(response.body.projects[0].project_id).toBe('alpha');
    expect(response.body.projects[0].tenant_id).toBe('tenant-a');
    expect(lastListQuery).toMatchObject({
      tenant_id: 'tenant-a',
      status: 'active',
      owner: 'jane',
      tags: 'core,api',
    });
  });

  it('surfaces backend validation errors when project creation fails', async () => {
    const app = await createApp();

    const response = await request(app).post('/').send({
      name: 'explode',
      tenant_id: 'tenant-a',
    });

    expect(response.status).toBe(422);
    expect(response.body).toMatchObject({
      success: false,
      error: 'invalid project name',
    });
  });

  it('retrieves project activity with pagination params', async () => {
    activityResponseBody = {
      project_id: 'alpha',
      activity: [
        { id: 'evt-1', type: 'project_created' },
        { id: 'evt-2', type: 'ontology_updated' },
      ],
      total: 2,
    };

    const app = await createApp();

    const response = await request(app).get('/alpha/activity?limit=5&offset=10');

    expect(lastActivityQuery).toMatchObject({ limit: '5', offset: '10' });
    expect(response.status).toBe(200);
    expect(response.body).toMatchObject({
      success: true,
      project_id: 'alpha',
      total: 2,
    });
    expect(response.body.activity).toHaveLength(2);
  });

  it('propagates PermaGraph activity errors', async () => {
    activityResponseStatus = 503;
    activityResponseBody = { error: 'permagaph unavailable' };

    const app = await createApp();

    const response = await request(app).get('/beta/activity');

    expect(response.status).toBe(503);
    expect(response.body).toMatchObject({
      success: false,
      error: 'permagaph unavailable',
      details: activityResponseBody,
    });
  });
});
