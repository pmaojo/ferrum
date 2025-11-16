import { kthuluService } from '../kthuluService';

describe('kthuluService', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('initializes Kthulu project', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });

    const result = await kthuluService.initialize('123', '/tmp/path');

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/kthulu/projects/123/initialize',
      expect.objectContaining({
        method: 'POST',
      })
    );
    expect(result).toEqual({ success: true });
  });

  it('executes a command', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ output: 'ok' }),
    });

    const result = await kthuluService.executeCommand('123', 'plan', [
      '--graph',
    ]);

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/kthulu/projects/123/commands/plan',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ args: ['--graph'] }),
      })
    );
    expect(result).toEqual({ output: 'ok' });
  });
});
