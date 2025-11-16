import type { Request, Response } from 'express';

import { ProjectGraphController } from '../../../controllers/projects/ProjectGraphController';

describe('ProjectGraphController', () => {
  const createResponse = () => {
    const res: Partial<Response> = {};
    res.status = jest.fn().mockReturnValue(res);
    res.json = jest.fn().mockReturnValue(res);
    return res as Response & {
      status: jest.MockedFunction<Response['status']>;
      json: jest.MockedFunction<Response['json']>;
    };
  };

  const createRequest = (overrides: Partial<Request> = {}) =>
    ({ ...overrides } as Request);

  let graphService: any;
  let controller: ProjectGraphController;

  beforeEach(() => {
    graphService = {
      getGraphData: jest.fn().mockResolvedValue({ nodes: [], edges: [] }),
      refreshGraph: jest.fn().mockResolvedValue({ nodesCreated: 1, edgesCreated: 2 }),
    };
    controller = new ProjectGraphController(graphService);
  });

  it('returns graph data', async () => {
    const res = createResponse();
    await controller.getGraph(createRequest({ params: { projectId: 'p1' } as any }), res);
    expect(graphService.getGraphData).toHaveBeenCalledWith('p1');
    expect(res.json).toHaveBeenCalledWith({ nodes: [], edges: [] });
  });

  it('refreshes graph via service', async () => {
    const res = createResponse();
    await controller.refreshGraph(
      createRequest({ params: { id: 'p1' } as any, get: () => 'host' } as any),
      res
    );

    expect(graphService.refreshGraph).toHaveBeenCalledWith('p1', 'host');
    expect(res.json).toHaveBeenCalledWith({ nodesCreated: 1, edgesCreated: 2 });
  });
});
