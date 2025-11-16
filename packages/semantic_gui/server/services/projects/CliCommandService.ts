export class CliCommandService {
  constructor(private readonly fetchFn: typeof fetch = fetch) {}

  async execute(
    host: string | null | undefined,
    projectId: string,
    operation: string,
    args: Record<string, unknown> = {},
    dryRun = false
  ): Promise<any> {
    if (!host) {
      throw new Error('Host header is required for CLI execution');
    }
    const response = await this.fetchFn(
      `http://${host}/api/v1/projects/${projectId}/cli/execute`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operation, args, dryRun }),
      }
    );
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`CLI execution failed: ${response.status} ${text}`);
    }
    return response.json();
  }
}

export default CliCommandService;
