import { PermaGraphController } from '../permagraph-controller';
import type { ProjectMetricsService } from './ProjectMetricsService';

type SyncMode = 'initial' | 'incremental';

type TraceabilityPayload = unknown;

type WsManager = {
  unsubscribeProject?: (projectId: string) => void;
};

export class PermaGraphService {
  constructor(
    private readonly controllers: Map<string, PermaGraphController>,
    private readonly metrics: ProjectMetricsService,
    private readonly controllerFactory: (projectId: string) => PermaGraphController
  ) {}

  ensureController(projectId: string): PermaGraphController {
    let controller = this.controllers.get(projectId);
    if (!controller) {
      controller = this.controllerFactory(projectId);
      this.controllers.set(projectId, controller);
    }
    return controller;
  }

  async init(projectId: string, projectPath: string): Promise<void> {
    const controller = this.ensureController(projectId);
    await this.metrics.recordSync(projectId, 'initial', () =>
      controller.init(projectId, projectPath)
    );
  }

  async ingestDocs(
    projectId: string,
    docs: { name: string; content: string }[]
  ): Promise<void> {
    if (!docs.length) {
      return;
    }
    const controller = this.ensureController(projectId);
    await controller.ingestDocs(projectId, docs);
  }

  async sync(projectId: string, mode: SyncMode): Promise<unknown> {
    const controller = this.controllers.get(projectId);
    if (!controller) {
      return undefined;
    }
    return this.metrics.recordSync(projectId, mode, () =>
      controller.sync(projectId, { mode })
    );
  }

  async recordTraceability(
    projectId: string,
    action: string,
    payload: TraceabilityPayload
  ): Promise<void> {
    const controller = this.controllers.get(projectId);
    await controller?.recordTraceability(action, payload);
  }

  async shutdown(projectId: string, wsManager?: WsManager): Promise<void> {
    const controller = this.controllers.get(projectId);
    if (controller) {
      await controller.shutdown();
      this.controllers.delete(projectId);
    }
    wsManager?.unsubscribeProject?.(projectId);
  }
}

export default PermaGraphService;
