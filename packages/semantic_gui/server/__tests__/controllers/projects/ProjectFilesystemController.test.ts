import type { Request, Response } from 'express';

import { ProjectFilesystemController } from '../../../controllers/projects/ProjectFilesystemController';

describe('ProjectFilesystemController', () => {
  const createResponse = () => {
    const res: Partial<Response> = {};
    res.status = jest.fn().mockReturnValue(res);
    res.json = jest.fn().mockReturnValue(res);
    res.type = jest.fn().mockReturnValue(res);
    res.send = jest.fn().mockReturnValue(res);
    return res as Response & {
      status: jest.MockedFunction<Response['status']>;
      json: jest.MockedFunction<Response['json']>;
      type: jest.MockedFunction<Response['type']>;
      send: jest.MockedFunction<Response['send']>;
    };
  };

  const createRequest = (overrides: Partial<Request> = {}) =>
    ({ ...overrides } as Request);

  let fileService: any;
  let graphService: any;
  let metrics: any;
  let lockService: any;
  let controller: ProjectFilesystemController;

  beforeEach(() => {
    fileService = {
      readFile: jest.fn().mockResolvedValue('content'),
      applyChanges: jest
        .fn()
        .mockResolvedValue({ diffs: [], linesModified: 10, filesApplied: 0 }),
      rollback: jest.fn().mockResolvedValue(undefined),
    };
    graphService = {
      handlePostApply: jest.fn().mockResolvedValue(undefined),
    };
    metrics = {
      incrementChangesApplied: jest.fn(),
      incrementLinesModified: jest.fn(),
    };
    lockService = { acquire: jest.fn().mockResolvedValue(() => {}) };
    controller = new ProjectFilesystemController(
      fileService,
      graphService,
      metrics,
      lockService
    );
  });

  it('reads project files', async () => {
    const res = createResponse();
    await controller.getFile(
      createRequest({ params: { id: 'p1', 0: 'file.txt' } as any } as any),
      res
    );

    expect(fileService.readFile).toHaveBeenCalledWith('p1', 'file.txt');
    expect(res.type).toHaveBeenCalledWith('text/plain');
    expect(res.send).toHaveBeenCalledWith('content');
  });

  it('applies file changes and triggers metrics', async () => {
    lockService.acquire.mockResolvedValueOnce(jest.fn());
    const res = createResponse();
    await controller.applyChanges(
      createRequest({ params: { id: 'p1' } as any, body: { files: [] }, get: () => 'host' } as any),
      res
    );

    expect(fileService.applyChanges).toHaveBeenCalledWith('p1', []);
    expect(metrics.incrementChangesApplied).toHaveBeenCalledWith('p1', 0);
    expect(metrics.incrementLinesModified).toHaveBeenCalledWith('p1', 10);
    expect(graphService.handlePostApply).toHaveBeenCalledWith('p1', 'host');
  });

  it('rolls back changes', async () => {
    const res = createResponse();
    await controller.rollback(createRequest({ params: { id: 'p1' } as any }), res);
    expect(fileService.rollback).toHaveBeenCalledWith('p1');
    expect(res.json).toHaveBeenCalledWith({ success: true });
  });
});
