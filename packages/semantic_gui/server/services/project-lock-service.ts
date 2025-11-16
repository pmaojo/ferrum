import { EventEmitter } from 'node:events';

import { logger } from '../utils/logger';

export type Release = () => void;

class Mutex {
  private locked = false;

  tryAcquire(): boolean {
    if (!this.locked) {
      this.locked = true;
      return true;
    }
    return false;
  }

  release(): void {
    this.locked = false;
  }
}

export interface AcquireOptions {
  wait?: boolean;
  backoffMs?: number;
  maxAttempts?: number;
}

export class ProjectLockService extends EventEmitter {
  private locks = new Map<string, Mutex>();

  private getMutex(projectId: string): Mutex {
    let mutex = this.locks.get(projectId);
    if (!mutex) {
      mutex = new Mutex();
      this.locks.set(projectId, mutex);
    }
    return mutex;
  }

  private emitWait(projectId: string) {
    this.emit('lock.wait', { projectId });
    logger.debug('lock.wait', { projectId });
  }

  private emitRelease(projectId: string) {
    this.emit('lock.release', { projectId });
    logger.debug('lock.release', { projectId });
  }

  private tryAcquire(projectId: string): Release | null {
    const mutex = this.getMutex(projectId);
    if (mutex.tryAcquire()) {
      return () => {
        mutex.release();
        this.emitRelease(projectId);
      };
    }
    return null;
  }

  async acquire(
    projectId: string,
    { wait = true, backoffMs = 50, maxAttempts = 5 }: AcquireOptions = {}
  ): Promise<Release | null> {
    let release = this.tryAcquire(projectId);
    if (release) return release;
    if (!wait) return null;

    let delay = backoffMs;
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      this.emitWait(projectId);
      await new Promise(resolve => setTimeout(resolve, delay));
      release = this.tryAcquire(projectId);
      if (release) return release;
      delay *= 2;
    }
    return null;
  }
}
