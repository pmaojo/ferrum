import type { Request, Response } from 'express';

import { ProjectCrudController } from '../../../controllers/projects/ProjectCrudController';

describe('ProjectCrudController', () => {
  const createResponse = () => {
    const res: Partial<Response> = {};
    res.status = jest.fn().mockReturnValue(res);
    res.json = jest.fn().mockReturnValue(res);
    res.send = jest.fn().mockReturnValue(res);
    return res as Response & {
      status: jest.MockedFunction<Response['status']>;
      json: jest.MockedFunction<Response['json']>;
      send: jest.MockedFunction<Response['send']>;
    };
  };

  const createRequest = (overrides: Partial<Request> = {}) =>
    ({ ...overrides } as Request);

  let storage: any;
  let initService: any;
  let permaGraphService: any;
  let controller: ProjectCrudController;

  beforeEach(() => {
    storage = {
      listProjects: jest.fn().mockResolvedValue([{ id: '1' }]),
      createProject: jest.fn().mockResolvedValue({ id: 'new', projectPath: '/tmp' }),
      getProject: jest.fn().mockResolvedValue({ id: '1' }),
      updateProject: jest.fn().mockResolvedValue({ id: '1', name: 'updated' }),
      deleteProject: jest.fn().mockResolvedValue(undefined),
    };
    initService = { initialize: jest.fn().mockResolvedValue(undefined) };
    permaGraphService = { shutdown: jest.fn().mockResolvedValue(undefined) };
    controller = new ProjectCrudController(
      storage,
      initService,
      permaGraphService,
      { unsubscribeProject: jest.fn() }
    );
  });

  it('lists projects', async () => {
    const res = createResponse();
    await controller.listProjects(createRequest(), res);
    expect(storage.listProjects).toHaveBeenCalled();
    expect(res.json).toHaveBeenCalledWith([{ id: '1' }]);
  });

  it('initializes project on system create', async () => {
    const res = createResponse();
    await controller.createSystemProject(
      createRequest({
        body: {
          templateId: 't',
          projectPath: '/tmp/proj',
        },
      }),
      res
    );

    expect(storage.createProject).toHaveBeenCalled();
    expect(initService.initialize).toHaveBeenCalledWith('new', '/tmp');
  });

  it('shuts down perma graph controller on delete', async () => {
    const res = createResponse();
    await controller.deleteProject(
      createRequest({ params: { id: 'to-delete' } as any }),
      res
    );

    expect(permaGraphService.shutdown).toHaveBeenCalledWith('to-delete', expect.any(Object));
    expect(storage.deleteProject).toHaveBeenCalledWith('to-delete');
    expect(res.status).toHaveBeenCalledWith(204);
  });
});
