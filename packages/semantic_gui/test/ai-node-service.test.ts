/** @jest-environment jsdom */
import { createNodesFromAI } from '../client/src/services/ai-node-service';

describe('createNodesFromAI', () => {
  afterEach(() => {
    jest.resetAllMocks();
  });

  it('requests AI nodes and creates them', async () => {
    const suggestions = [
      {
        name: 'AI Node',
        type: 'controller',
        description: 'generated',
        position: { x: 10, y: 20 },
      },
    ];

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => suggestions,
    }) as any;

    const createNode = jest.fn().mockResolvedValue({
      id: 'node-1',
      name: 'AI Node',
      type: 'controller',
      description: 'generated',
      metadata: { aiGenerated: true },
      filePath: '/tmp',
    });

    const result = await createNodesFromAI(
      'build login',
      'proj1',
      'tmpl1',
      createNode
    );

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/ai/nodes',
      expect.objectContaining({ method: 'POST' })
    );
    expect(createNode).toHaveBeenCalledWith(
      expect.objectContaining({
        projectId: 'proj1',
        templateId: 'tmpl1',
        name: 'AI Node',
      })
    );
    expect(result[0]).toMatchObject({ id: 'node-1' });
  });
});
