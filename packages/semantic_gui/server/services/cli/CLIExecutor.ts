import type { ChildProcessWithoutNullStreams } from 'child_process';
import { spawn } from 'child_process';

import type { WebSocketManager } from '../websocket-manager';

export interface CLIExecutionResult {
  exitCode: number;
  stdout: string;
  stderr: string;
}

export class CLIExecutor {
  private processes = new Map<string, ChildProcessWithoutNullStreams>();

  constructor(private wsManager?: WebSocketManager) {}

  async execute(
    projectId: string,
    command: string,
    traceId: string,
    cwd: string
  ): Promise<CLIExecutionResult> {
    return new Promise((resolve, reject) => {
      const child = spawn(command, { cwd, shell: true });
      this.processes.set(traceId, child);

      let stdout = '';
      let stderr = '';

      child.stdout.on('data', d => {
        const text = d.toString();
        stdout += text;
        this.wsManager?.broadcastToProject(projectId, {
          type: 'cli.progress',
          projectId,
          data: text,
          timestamp: new Date().toISOString(),
        });
      });

      child.stderr.on('data', d => {
        const text = d.toString();
        stderr += text;
        this.wsManager?.broadcastToProject(projectId, {
          type: 'cli.progress',
          projectId,
          data: text,
          timestamp: new Date().toISOString(),
        });
      });

      child.on('close', code => {
        this.processes.delete(traceId);
        resolve({ exitCode: code ?? 0, stdout, stderr });
      });

      child.on('error', err => {
        this.processes.delete(traceId);
        reject(err);
      });
    });
  }

  cancel(traceId: string): boolean {
    const proc = this.processes.get(traceId);
    if (proc) {
      proc.kill('SIGTERM');
      this.processes.delete(traceId);
      return true;
    }
    return false;
  }
}
