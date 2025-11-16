import type { Request, Response } from 'express';

import { ProjectCliController } from '../../../controllers/projects/ProjectCliController';

describe('ProjectCliController', () => {
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

  let cliService: any;
  let permaGraphService: any;
  let lockService: any;
  let controller: ProjectCliController;

  beforeEach(() => {
    cliService = { execute: jest.fn().mockResolvedValue({ diffs: [] }) };
    permaGraphService = { recordTraceability: jest.fn().mockResolvedValue(undefined) };
    lockService = { acquire: jest.fn().mockResolvedValue(jest.fn()) };
    controller = new ProjectCliController(cliService, permaGraphService, lockService);
  });

  it('executes CLI scaffold operations', async () => {
    const res = createResponse();
    await controller.scaffoldModule(
      createRequest({ params: { id: 'p1' } as any, body: { name: 'test' }, get: () => 'host' } as any),
      res
    );

    expect(cliService.execute).toHaveBeenCalledWith('host', 'p1', 'make:module', { name: 'test' }, true);
    expect(permaGraphService.recordTraceability).toHaveBeenCalledWith('p1', 'scaffold:module', {
      diffs: [],
    });
  });
});
