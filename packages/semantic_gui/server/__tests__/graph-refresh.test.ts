import { TextEncoder, TextDecoder } from 'util';

import express from 'express';
import request from 'supertest';

import { MockStorage } from '../../test/mock-storage';
import { generateNodeId } from '../utils/generateNodeId';

(global as any).TextEncoder = TextEncoder;
(global as any).TextDecoder = TextDecoder;

describe('graph refresh', () => {
  it('refreshing twice does not duplicate nodes', async () => {
    const storage = new MockStorage();
    const project = await storage.createProject({
      name: 'P',
      templateId: 'tmpl1',
      projectPath: '/tmp/project',
      metadata: {},
    } as any);

    const app = express();
    app.use(express.json());
    app.post('/api/projects/:id/graph/refresh', async (req, res) => {
      const { id } = req.params;
      const { nodes } = req.body;
      for (const node of nodes) {
        const nodeId = generateNodeId(node.type, node.filePath || '');
        await storage.createGraphNode({ ...node, id: nodeId, projectId: id });
      }
      res.json({ nodesCreated: nodes.length });
    });

    const nodes = [
      {
        name: 'A',
        type: 'service',
        filePath: 'src/a.ts',
        position: { x: 0, y: 0 },
        templateId: 'tmpl1',
      },
      {
        name: 'B',
        type: 'service',
        filePath: 'src/b.ts',
        position: { x: 0, y: 0 },
        templateId: 'tmpl1',
      },
    ];

    const url = `/api/projects/${project.id}/graph/refresh`;
    const res1 = await request(app).post(url).send({ nodes });
    expect(res1.status).toBe(200);
    const afterFirst = await storage.getNodesByProject(project.id);
    expect(afterFirst).toHaveLength(nodes.length);

    const res2 = await request(app).post(url).send({ nodes });
    expect(res2.status).toBe(200);
    const afterSecond = await storage.getNodesByProject(project.id);
    expect(afterSecond).toHaveLength(nodes.length);
    const unique = new Set(afterSecond.map(n => n.id));
    expect(unique.size).toBe(nodes.length);
  });
});
