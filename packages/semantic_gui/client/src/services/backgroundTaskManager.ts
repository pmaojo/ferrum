/**
 * Background Task Manager for SCG Frontend
 *
 * Manages heavy operations in the background to maintain UI responsiveness
 */

import { createLogger } from '../utils/logger';

export enum TaskStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum TaskPriority {
  LOW = 1,
  NORMAL = 2,
  HIGH = 3,
  CRITICAL = 4,
}

export interface BackgroundTask {
  id: string;
  name: string;
  type: string;
  status: TaskStatus;
  priority: TaskPriority;
  progress: number;
  result?: any;
  error?: string;
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  estimatedDuration?: number;
  dependencies: string[];
}

export interface TaskResult<T = any> {
  taskId: string;
  status: TaskStatus;
  result?: T;
  error?: string;
  executionTime?: number;
  progress: number;
}

export interface TaskProgressCallback {
  onProgress: (taskId: string, progress: number, message?: string) => void;
  onStatusChange: (taskId: string, status: TaskStatus) => void;
  onComplete: (taskId: string, result: any) => void;
  onError: (taskId: string, error: string) => void;
}

export interface QueueStatus {
  queueSize: number;
  pendingTasks: number;
  runningTasks: number;
  completedTasks: number;
  failedTasks: number;
  totalTasks: number;
}

/**
 * Background Task Manager with Web Workers support
 */
export class BackgroundTaskManager {
  private tasks: Map<string, BackgroundTask> = new Map();
  private workers: Map<string, Worker> = new Map();
  private callbacks: Map<string, TaskProgressCallback[]> = new Map();
  private maxConcurrentTasks = 4;
  private runningTasks = 0;
  private taskQueue: BackgroundTask[] = [];
  private isProcessing = false;
  private logger = createLogger('BackgroundTaskManager');

  constructor(maxConcurrentTasks = 4) {
    this.maxConcurrentTasks = maxConcurrentTasks;
    this.startProcessing();
  }

  /**
   * Submit a task for background execution
   */
  async submitTask<T = any>(
    name: string,
    type: string,
    taskFunction: () => Promise<T>,
    options: {
      priority?: TaskPriority;
      dependencies?: string[];
      estimatedDuration?: number;
      useWebWorker?: boolean;
    } = {}
  ): Promise<string> {
    const taskId = this.generateTaskId();
    const task: BackgroundTask = {
      id: taskId,
      name,
      type,
      status: TaskStatus.PENDING,
      priority: options.priority || TaskPriority.NORMAL,
      progress: 0,
      createdAt: new Date(),
      dependencies: options.dependencies || [],
      estimatedDuration: options.estimatedDuration,
    };

    this.tasks.set(taskId, task);

    // Store task function for execution
    (task as any).taskFunction = taskFunction;
    (task as any).useWebWorker = options.useWebWorker || false;

    // Add to queue
    this.addToQueue(task);

    // Notify callbacks
    this.notifyStatusChange(taskId, TaskStatus.PENDING);

    return taskId;
  }

  /**
   * Submit a SPARQL query task
   */
  async submitSparqlQuery(
    query: string,
    priority = TaskPriority.NORMAL
  ): Promise<string> {
    return this.submitTask(
      `SPARQL Query: ${query.substring(0, 50)}...`,
      'sparql_query',
      async () => {
        const response = await fetch('/api/v1/sparql/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query }),
        });
        return response.json();
      },
      { priority }
    );
  }

  /**
   * Submit an ontology validation task
   */
  async submitOntologyValidation(
    ontologyData: any,
    priority = TaskPriority.HIGH
  ): Promise<string> {
    return this.submitTask(
      'Ontology Validation',
      'ontology_validation',
      async () => {
        const response = await fetch('/api/v1/validate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ontologyData }),
        });
        return response.json();
      },
      { priority, estimatedDuration: 5000 }
    );
  }

  /**
   * Submit a graph analysis task
   */
  async submitGraphAnalysis(
    graphData: any,
    analysisType: string
  ): Promise<string> {
    return this.submitTask(
      `Graph Analysis: ${analysisType}`,
      'graph_analysis',
      async () => {
        const response = await fetch('/api/v1/semantic/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ graphData, analysisType }),
        });
        return response.json();
      },
      {
        priority: TaskPriority.NORMAL,
        estimatedDuration: 10000,
        useWebWorker: true,
      }
    );
  }

  /**
   * Submit a code generation task
   */
  async submitCodeGeneration(
    template: string,
    parameters: any,
    priority = TaskPriority.HIGH
  ): Promise<string> {
    return this.submitTask(
      'Code Generation',
      'code_generation',
      async () => {
        const response = await fetch('/api/v1/kthulu/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ template, parameters }),
        });
        return response.json();
      },
      { priority, estimatedDuration: 3000 }
    );
  }

  /**
   * Get task status
   */
  getTaskStatus(taskId: string): TaskResult | null {
    const task = this.tasks.get(taskId);
    if (!task) return null;

    const executionTime =
      task.startedAt && task.completedAt
        ? task.completedAt.getTime() - task.startedAt.getTime()
        : undefined;

    return {
      taskId,
      status: task.status,
      result: task.result,
      error: task.error,
      executionTime,
      progress: task.progress,
    };
  }

  /**
   * Cancel a task
   */
  cancelTask(taskId: string): boolean {
    const task = this.tasks.get(taskId);
    if (!task) return false;

    if (task.status === TaskStatus.PENDING) {
      task.status = TaskStatus.CANCELLED;
      this.removeFromQueue(taskId);
      this.notifyStatusChange(taskId, TaskStatus.CANCELLED);
      return true;
    }

    if (task.status === TaskStatus.RUNNING) {
      const worker = this.workers.get(taskId);
      if (worker) {
        worker.terminate();
        this.workers.delete(taskId);
      }
      task.status = TaskStatus.CANCELLED;
      this.runningTasks--;
      this.notifyStatusChange(taskId, TaskStatus.CANCELLED);
      return true;
    }

    return false;
  }

  /**
   * Get queue status
   */
  getQueueStatus(): QueueStatus {
    const tasks = Array.from(this.tasks.values());
    return {
      queueSize: this.taskQueue.length,
      pendingTasks: tasks.filter((t) => t.status === TaskStatus.PENDING).length,
      runningTasks: tasks.filter((t) => t.status === TaskStatus.RUNNING).length,
      completedTasks: tasks.filter((t) => t.status === TaskStatus.COMPLETED)
        .length,
      failedTasks: tasks.filter((t) => t.status === TaskStatus.FAILED).length,
      totalTasks: tasks.length,
    };
  }

  /**
   * Add progress callback
   */
  addCallback(taskId: string, callback: TaskProgressCallback): void {
    if (!this.callbacks.has(taskId)) {
      this.callbacks.set(taskId, []);
    }
    this.callbacks.get(taskId)!.push(callback);
  }

  /**
   * Remove progress callback
   */
  removeCallback(taskId: string, callback: TaskProgressCallback): void {
    const callbacks = this.callbacks.get(taskId);
    if (callbacks) {
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  /**
   * Clear completed tasks
   */
  clearCompletedTasks(): void {
    const completedTasks = Array.from(this.tasks.entries())
      .filter(
        ([_, task]) =>
          task.status === TaskStatus.COMPLETED ||
          task.status === TaskStatus.FAILED
      )
      .map(([id, _]) => id);

    completedTasks.forEach((taskId) => {
      this.tasks.delete(taskId);
      this.callbacks.delete(taskId);
    });
  }

  private generateTaskId(): string {
    return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private addToQueue(task: BackgroundTask): void {
    // Insert task in priority order
    let inserted = false;
    for (let i = 0; i < this.taskQueue.length; i++) {
      if (task.priority > this.taskQueue[i].priority) {
        this.taskQueue.splice(i, 0, task);
        inserted = true;
        break;
      }
    }
    if (!inserted) {
      this.taskQueue.push(task);
    }
  }

  private removeFromQueue(taskId: string): void {
    const index = this.taskQueue.findIndex((task) => task.id === taskId);
    if (index > -1) {
      this.taskQueue.splice(index, 1);
    }
  }

  private startProcessing(): void {
    if (this.isProcessing) return;
    this.isProcessing = true;
    this.processQueue();
  }

  private async processQueue(): Promise<void> {
    while (this.isProcessing) {
      // Check if we can start more tasks
      if (
        this.runningTasks >= this.maxConcurrentTasks ||
        this.taskQueue.length === 0
      ) {
        await new Promise((resolve) => setTimeout(resolve, 100));
        continue;
      }

      // Get next task
      const task = this.getNextReadyTask();
      if (!task) {
        await new Promise((resolve) => setTimeout(resolve, 100));
        continue;
      }

      // Remove from queue
      this.removeFromQueue(task.id);

      // Execute task
      this.executeTask(task);
    }
  }

  private getNextReadyTask(): BackgroundTask | null {
    for (const task of this.taskQueue) {
      if (this.areDependenciesSatisfied(task)) {
        return task;
      }
    }
    return null;
  }

  private areDependenciesSatisfied(task: BackgroundTask): boolean {
    return task.dependencies.every((depId) => {
      const depTask = this.tasks.get(depId);
      return depTask && depTask.status === TaskStatus.COMPLETED;
    });
  }

  private async executeTask(task: BackgroundTask): Promise<void> {
    this.runningTasks++;
    task.status = TaskStatus.RUNNING;
    task.startedAt = new Date();
    this.notifyStatusChange(task.id, TaskStatus.RUNNING);

    try {
      const taskFunction = (task as any).taskFunction;
      const useWebWorker = (task as any).useWebWorker;

      let result: any;

      if (useWebWorker && typeof Worker !== 'undefined') {
        result = await this.executeInWebWorker(task, taskFunction);
      } else {
        result = await this.executeInMainThread(task, taskFunction);
      }

      task.result = result;
      task.status = TaskStatus.COMPLETED;
      task.completedAt = new Date();
      task.progress = 100;

      this.notifyComplete(task.id, result);
      this.notifyStatusChange(task.id, TaskStatus.COMPLETED);
    } catch (error) {
      task.error = error instanceof Error ? error.message : String(error);
      task.status = TaskStatus.FAILED;
      task.completedAt = new Date();

      this.notifyError(task.id, task.error);
      this.notifyStatusChange(task.id, TaskStatus.FAILED);
    } finally {
      this.runningTasks--;
      this.workers.delete(task.id);
    }
  }

  private async executeInMainThread(
    task: BackgroundTask,
    taskFunction: () => Promise<any>
  ): Promise<any> {
    // Update progress periodically
    const progressInterval = setInterval(() => {
      if (task.status === TaskStatus.RUNNING) {
        const elapsed = Date.now() - task.startedAt!.getTime();
        if (task.estimatedDuration) {
          const progress = Math.min(
            90,
            (elapsed / task.estimatedDuration) * 100
          );
          task.progress = progress;
          this.notifyProgress(task.id, progress);
        }
      }
    }, 500);

    try {
      return await taskFunction();
    } finally {
      clearInterval(progressInterval);
    }
  }

  private async executeInWebWorker(
    task: BackgroundTask,
    taskFunction: () => Promise<any>
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      // Create worker blob
      const workerCode = `
        self.onmessage = async function(e) {
          try {
            const { taskFunction, taskData } = e.data;
            const func = new Function('return ' + taskFunction)();
            const result = await func(taskData);
            self.postMessage({ type: 'success', result });
          } catch (error) {
            self.postMessage({ type: 'error', error: error.message });
          }
        };
      `;

      const blob = new Blob([workerCode], { type: 'application/javascript' });
      const worker = new Worker(URL.createObjectURL(blob));

      this.workers.set(task.id, worker);

      worker.onmessage = (e: MessageEvent) => {
        const { type, result, error } = e.data;
        if (type === 'success') {
          resolve(result);
        } else if (type === 'error') {
          reject(new Error(error));
        }
        worker.terminate();
      };

      worker.onerror = (error: ErrorEvent) => {
        reject(error);
        worker.terminate();
      };

      // Send task to worker
      worker.postMessage({
        taskFunction: taskFunction.toString(),
        taskData: task,
      });
    });
  }

  private notifyProgress(
    taskId: string,
    progress: number,
    message?: string
  ): void {
    const callbacks = this.callbacks.get(taskId);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback.onProgress(taskId, progress, message);
        } catch (error) {
          this.logger.error('Error in progress callback', error instanceof Error ? error : new Error(String(error)), { taskId });
        }
      });
    }
  }

  private notifyStatusChange(taskId: string, status: TaskStatus): void {
    const callbacks = this.callbacks.get(taskId);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback.onStatusChange(taskId, status);
        } catch (error) {
          this.logger.error('Error in status change callback', error instanceof Error ? error : new Error(String(error)), { taskId, status });
        }
      });
    }
  }

  private notifyComplete(taskId: string, result: any): void {
    const callbacks = this.callbacks.get(taskId);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback.onComplete(taskId, result);
        } catch (error) {
          this.logger.error('Error in complete callback', error instanceof Error ? error : new Error(String(error)), { taskId });
        }
      });
    }
  }

  private notifyError(taskId: string, error: string): void {
    const callbacks = this.callbacks.get(taskId);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback.onError(taskId, error);
        } catch (error) {
          this.logger.error('Error in error callback', error instanceof Error ? error : new Error(String(error)), { taskId });
        }
      });
    }
  }

  /**
   * Stop processing and cleanup
   */
  destroy(): void {
    this.isProcessing = false;

    // Terminate all workers
    this.workers.forEach((worker) => worker.terminate());
    this.workers.clear();

    // Clear all data
    this.tasks.clear();
    this.callbacks.clear();
    this.taskQueue = [];
  }
}

// Singleton instance
export const backgroundTaskManager = new BackgroundTaskManager();
