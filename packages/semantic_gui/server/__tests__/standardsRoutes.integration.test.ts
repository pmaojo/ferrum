/** @jest-environment node */

import http from 'node:http';
import type { AddressInfo } from 'node:net';
import express from 'express';
import request from 'supertest';

interface ResponseSpec {
  status?: number;
  headers?: Record<string, string>;
  body?: string | Buffer | Record<string, unknown>;
}

type ScenarioMap = Record<string, ResponseSpec>;

describe('standardsRoutes integration', () => {
  const recordedRequests: Array<{
    method: string;
    url: string;
    headers: http.IncomingHttpHeaders;
    body: Buffer;
  }> = [];
  let scenario: ScenarioMap;
  let permaServer: http.Server;
  let app: express.Express;

  function routeKey(method = 'GET', url = ''): string {
    return `${method.toUpperCase()} ${url}`;
  }

  function handlePermaGraphRequest(
    req: http.IncomingMessage,
    res: http.ServerResponse<http.IncomingMessage>,
    body: Buffer
  ) {
    const key = routeKey(req.method, req.url);
    const spec = scenario[key];

    if (!spec) {
      res.writeHead(404);
      res.end();
      return;
    }

    let responseBody: string | Buffer | undefined;
    if (Buffer.isBuffer(spec.body)) {
      responseBody = spec.body;
    } else if (typeof spec.body === 'string') {
      responseBody = spec.body;
    } else if (spec.body) {
      responseBody = JSON.stringify(spec.body);
    }

    const headers: Record<string, string> = {
      ...(spec.headers ?? {}),
    };

    if (!headers['Content-Type'] && spec.body && typeof spec.body === 'object') {
      headers['Content-Type'] = 'application/json';
    }

    if (
      responseBody &&
      !headers['Content-Length'] &&
      (typeof responseBody === 'string' || Buffer.isBuffer(responseBody))
    ) {
      const buffer = Buffer.isBuffer(responseBody)
        ? responseBody
        : Buffer.from(responseBody);
      headers['Content-Length'] = buffer.length.toString();
      responseBody = buffer;
    }

    res.writeHead(spec.status ?? 200, headers);
    res.end(responseBody);
  }

  beforeAll(async () => {
    scenario = {};
    permaServer = http.createServer((req, res) => {
      const chunks: Buffer[] = [];
      req.on('data', (chunk) => chunks.push(chunk as Buffer));
      req.on('end', () => {
        const body = Buffer.concat(chunks);
        recordedRequests.push({
          method: req.method ?? 'GET',
          url: req.url ?? '',
          headers: req.headers,
          body,
        });
        handlePermaGraphRequest(req, res, body);
      });
    });

    await new Promise<void>((resolve) =>
      permaServer.listen(0, '127.0.0.1', resolve)
    );
    const { port } = permaServer.address() as AddressInfo;
    process.env.PERMAGRAPH_API_URL = `http://127.0.0.1:${port}`;

    const { default: standardsRouter } = await import('../routes/standardsRoutes');
    app = express();
    app.use(express.json());
    app.use('/api/v1/standards', standardsRouter);
  });

  afterAll(async () => {
    await new Promise<void>((resolve) => permaServer.close(() => resolve()));
  });

  beforeEach(() => {
    scenario = {};
    recordedRequests.length = 0;
  });

  it('streams exports with headers from PermaGraph', async () => {
    const projectId = 'project-42';
    const payload = '@prefix ex: <http://example.com/> .';
    scenario[routeKey('POST', `/api/v1/projects/${projectId}/standards/export`)] = {
      status: 200,
      headers: {
        'Content-Type': 'text/turtle',
        'Content-Length': Buffer.byteLength(payload).toString(),
      },
      body: payload,
    };

    const response = await request(app)
      .post('/api/v1/standards/export')
      .send({ projectId, format: 'turtle', options: { includeMetadata: true } })
      .expect(200);

    expect(response.text).toBe(payload);
    expect(response.headers['content-type']).toBe('text/turtle');

    expect(recordedRequests).toHaveLength(1);
    const forwarded = JSON.parse(recordedRequests[0].body.toString());
    expect(forwarded.project_id).toBe(projectId);
    expect(forwarded.export_format).toBe('turtle');
    expect(forwarded.options).toEqual({ includeMetadata: true });
  });

  it('forwards file uploads and returns validation warnings from PermaGraph', async () => {
    const projectId = 'project-42';
    const endpoint = `/api/v1/projects/${projectId}/standards/import/file`;
    scenario[routeKey('POST', endpoint)] = {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: {
        triples_imported: 3,
        validation_warnings: ['missing labels'],
      },
    };

    const response = await request(app)
      .post('/api/v1/standards/import')
      .field('projectId', projectId)
      .field('format', 'turtle')
      .field('options', JSON.stringify({ mergeStrategy: 'merge' }))
      .attach('file', Buffer.from('@prefix ex: <http://example.com/> .'), 'ontology.ttl')
      .expect(200);

    expect(response.body.success).toBe(true);
    expect(response.body.triples_imported).toBe(3);
    expect(response.body.validation_warnings).toEqual(['missing labels']);

    expect(recordedRequests).toHaveLength(1);
    const forwardedBody = recordedRequests[0].body.toString();
    expect(forwardedBody).toContain('@prefix ex: <http://example.com/> .');
    expect(recordedRequests[0].headers['content-type']).toContain('multipart/form-data');
  });

  it('propagates validation errors from PermaGraph URL imports', async () => {
    const projectId = 'project-42';
    const endpoint = `/api/v1/projects/${projectId}/standards/import/url`;
    scenario[routeKey('POST', endpoint)] = {
      status: 422,
      headers: { 'Content-Type': 'application/json' },
      body: {
        error: 'Validation failed',
        validation_warnings: ['class ex:Thing is undefined'],
      },
    };

    const response = await request(app)
      .post('/api/v1/standards/import')
      .field('projectId', projectId)
      .field('format', 'turtle')
      .field('url', 'https://example.com/ontology.ttl')
      .expect(422);

    expect(response.body.success).toBe(false);
    expect(response.body.error).toBe('Validation failed');
    expect(response.body.validation_warnings).toEqual([
      'class ex:Thing is undefined',
    ]);
  });

  it('returns upstream HTTP failures for export shapes', async () => {
    const projectId = 'project-42';
    scenario[routeKey('POST', `/api/v1/projects/${projectId}/standards/shapes/export`)] = {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
      body: { error: 'Service unavailable' },
    };

    const response = await request(app)
      .post('/api/v1/standards/export/shapes')
      .send({ projectId })
      .expect(503);

    expect(response.body.error).toBe('Service unavailable');
  });

  it('rejects missing files and URLs before calling PermaGraph', async () => {
    const projectId = 'project-42';
    await request(app)
      .post('/api/v1/standards/import')
      .field('projectId', projectId)
      .field('format', 'turtle')
      .expect(400);

    expect(recordedRequests).toHaveLength(0);
  });
});
