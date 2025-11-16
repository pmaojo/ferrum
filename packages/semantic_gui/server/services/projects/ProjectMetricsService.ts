import type client from 'prom-client';

type SyncMode = 'initial' | 'incremental';

export class ProjectMetricsService {
  constructor(
    private readonly changesCounter: client.Counter,
    private readonly linesCounter: client.Counter,
    private readonly syncHistogram: client.Histogram
  ) {}

  incrementChangesApplied(projectId: string, amount: number): void {
    this.changesCounter.labels(projectId).inc(amount);
  }

  incrementLinesModified(projectId: string, amount: number): void {
    this.linesCounter.labels(projectId).inc(amount);
  }

  async recordSync<T>(
    projectId: string,
    mode: SyncMode,
    operation: () => Promise<T>
  ): Promise<T> {
    const end = this.syncHistogram.startTimer({ projectId, mode });
    try {
      return await operation();
    } finally {
      end();
    }
  }
}

export default ProjectMetricsService;
