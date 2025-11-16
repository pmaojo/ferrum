/**
 * Cache Synchronization Service
 * 
 * Implements cache synchronization with PermaGraph updates,
 * cache invalidation and refresh strategies for the 2FA payment
 * service integration system.
 */

import { EventEmitter } from 'events';
import { localPatternCache, LocalPatternCache, SyncResult } from './local-pattern-cache';
import { AuthPattern, ServicePattern, RequirementChain } from './pattern-models';
import { healthMonitor } from './health-monitor';
import {
  createPermaGraphPatternClient,
  PermaGraphPatternClient,
  PermaGraphRateLimitError,
} from './permagraph-pattern-client';

export interface SyncStrategy {
  name: string;
  interval: number; // in milliseconds
  enabled: boolean;
  priority: number;
  conditions: SyncCondition[];
}

export interface SyncCondition {
  type: 'service-health' | 'cache-age' | 'cache-size' | 'manual-trigger';
  threshold?: number;
  serviceName?: string;
}

export interface SyncSchedule {
  strategy: string;
  nextRun: Date;
  lastRun: Date | null;
  lastResult: SyncResult | null;
  consecutiveFailures: number;
}

export interface CacheInvalidationRule {
  name: string;
  trigger: 'tag-based' | 'pattern-based' | 'time-based' | 'external-event';
  criteria: {
    tags?: string[];
    patterns?: string[];
    maxAge?: number;
    eventType?: string;
  };
  action: 'invalidate' | 'refresh' | 'mark-stale';
}

export class CacheSyncService extends EventEmitter {
  private syncStrategies: Map<string, SyncStrategy> = new Map();
  private syncSchedules: Map<string, SyncSchedule> = new Map();
  private invalidationRules: Map<string, CacheInvalidationRule> = new Map();
  private syncTimer: NodeJS.Timeout | null = null;
  private isRunning = false;
  private readonly exportPageSize: number;
  private readonly maxPagesPerSync: number;
  private readonly defaultRateLimitDelayMs: number;

  constructor(
    private cache: LocalPatternCache = localPatternCache,
    private readonly patternClient: PermaGraphPatternClient = createPermaGraphPatternClient(),
    private readonly sleep: (ms: number) => Promise<void> = (ms: number) =>
      new Promise(resolve => setTimeout(resolve, ms))
  ) {
    super();
    this.exportPageSize = Number(process.env.PERMAGRAPH_EXPORT_PAGE_SIZE) || 200;
    this.maxPagesPerSync = Number(process.env.PERMAGRAPH_EXPORT_MAX_PAGES) || 100;
    this.defaultRateLimitDelayMs = Number(process.env.PERMAGRAPH_RATE_LIMIT_DELAY_MS) || 5_000;
    this.setupDefaultStrategies();
    this.setupDefaultInvalidationRules();
    this.setupHealthMonitorListeners();
  }

  private setupDefaultStrategies(): void {
    // Periodic full sync when PermaGraph is healthy
    this.registerSyncStrategy({
      name: 'periodic-full-sync',
      interval: 24 * 60 * 60 * 1000, // 24 hours
      enabled: true,
      priority: 1,
      conditions: [
        { type: 'service-health', serviceName: 'permagraph' }
      ]
    });

    // Incremental sync for recent changes
    this.registerSyncStrategy({
      name: 'incremental-sync',
      interval: 60 * 60 * 1000, // 1 hour
      enabled: true,
      priority: 2,
      conditions: [
        { type: 'service-health', serviceName: 'permagraph' },
        { type: 'cache-age', threshold: 60 * 60 * 1000 } // 1 hour
      ]
    });

    // Emergency sync when cache is nearly empty
    this.registerSyncStrategy({
      name: 'emergency-sync',
      interval: 5 * 60 * 1000, // 5 minutes
      enabled: true,
      priority: 3,
      conditions: [
        { type: 'cache-size', threshold: 10 } // Less than 10 patterns
      ]
    });

    // Opportunistic sync when service recovers
    this.registerSyncStrategy({
      name: 'recovery-sync',
      interval: 0, // Immediate
      enabled: true,
      priority: 4,
      conditions: [
        { type: 'service-health', serviceName: 'permagraph' }
      ]
    });
  }

  private setupDefaultInvalidationRules(): void {
    // Invalidate 2FA patterns when security standards change
    this.registerInvalidationRule({
      name: 'security-standards-update',
      trigger: 'external-event',
      criteria: {
        eventType: 'security-standards-updated',
        tags: ['2fa', 'security', 'compliance']
      },
      action: 'refresh'
    });

    // Invalidate old patterns periodically
    this.registerInvalidationRule({
      name: 'age-based-invalidation',
      trigger: 'time-based',
      criteria: {
        maxAge: 7 * 24 * 60 * 60 * 1000 // 7 days
      },
      action: 'mark-stale'
    });

    // Invalidate framework-specific patterns when framework updates
    this.registerInvalidationRule({
      name: 'framework-update-invalidation',
      trigger: 'external-event',
      criteria: {
        eventType: 'framework-updated'
      },
      action: 'refresh'
    });

    // Invalidate payment patterns when compliance requirements change
    this.registerInvalidationRule({
      name: 'compliance-update-invalidation',
      trigger: 'external-event',
      criteria: {
        eventType: 'compliance-requirements-updated',
        tags: ['payment', 'pci-dss', 'compliance']
      },
      action: 'refresh'
    });
  }

  private setupHealthMonitorListeners(): void {
    healthMonitor.on('service-healthy', ({ serviceName }) => {
      if (serviceName === 'permagraph') {
        console.log('🔄 PermaGraph recovered, triggering recovery sync');
        this.triggerSync('recovery-sync');
      }
    });

    healthMonitor.on('service-unhealthy', ({ serviceName }) => {
      if (serviceName === 'permagraph') {
        console.log('⚠️ PermaGraph unhealthy, relying on local cache');
        this.emit('permagraph-unavailable');
      }
    });
  }

  registerSyncStrategy(strategy: SyncStrategy): void {
    this.syncStrategies.set(strategy.name, strategy);
    
    // Initialize schedule
    const schedule: SyncSchedule = {
      strategy: strategy.name,
      nextRun: new Date(Date.now() + strategy.interval),
      lastRun: null,
      lastResult: null,
      consecutiveFailures: 0
    };
    
    this.syncSchedules.set(strategy.name, schedule);
    
    console.log(`📋 Registered sync strategy: ${strategy.name}`);
  }

  registerInvalidationRule(rule: CacheInvalidationRule): void {
    this.invalidationRules.set(rule.name, rule);
    console.log(`📋 Registered invalidation rule: ${rule.name}`);
  }

  async start(): Promise<void> {
    if (this.isRunning) {
      console.log('⚠️ Cache sync service is already running');
      return;
    }

    this.isRunning = true;
    console.log('🚀 Starting cache synchronization service');

    // Start the sync timer
    this.syncTimer = setInterval(() => {
      this.processSyncSchedules();
    }, 60 * 1000); // Check every minute

    // Trigger initial sync if needed
    await this.triggerInitialSync();

    this.emit('sync-service-started');
  }

  async stop(): Promise<void> {
    if (!this.isRunning) {
      return;
    }

    this.isRunning = false;
    
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
      this.syncTimer = null;
    }

    console.log('🛑 Cache synchronization service stopped');
    this.emit('sync-service-stopped');
  }

  private async triggerInitialSync(): Promise<void> {
    const cacheStats = this.cache.getPatternStats();
    
    // If cache is empty or very small, trigger emergency sync
    if (cacheStats.totalPatterns < 5) {
      console.log('🚨 Cache is nearly empty, triggering emergency sync');
      await this.triggerSync('emergency-sync');
    } else {
      // Otherwise, trigger incremental sync
      console.log('🔄 Triggering initial incremental sync');
      await this.triggerSync('incremental-sync');
    }
  }

  private async processSyncSchedules(): Promise<void> {
    const now = new Date();
    
    for (const [strategyName, schedule] of this.syncSchedules) {
      if (now >= schedule.nextRun) {
        const strategy = this.syncStrategies.get(strategyName);
        if (strategy && strategy.enabled && this.shouldExecuteStrategy(strategy)) {
          await this.executeSync(strategyName);
        }
      }
    }
  }

  private shouldExecuteStrategy(strategy: SyncStrategy): boolean {
    for (const condition of strategy.conditions) {
      if (!this.evaluateCondition(condition)) {
        return false;
      }
    }
    return true;
  }

  private evaluateCondition(condition: SyncCondition): boolean {
    switch (condition.type) {
      case 'service-health':
        if (condition.serviceName) {
          return healthMonitor.isServiceHealthy(condition.serviceName);
        }
        return true;

      case 'cache-age':
        // Check if cache has patterns older than threshold
        const stats = this.cache.getPatternStats();
        // This is a simplified check - in reality, we'd check individual pattern ages
        return condition.threshold ? stats.totalPatterns > 0 : true;

      case 'cache-size':
        const cacheStats = this.cache.getPatternStats();
        return condition.threshold ? cacheStats.totalPatterns < condition.threshold : true;

      case 'manual-trigger':
        return true; // Manual triggers are always valid when explicitly called

      default:
        return false;
    }
  }

  async triggerSync(strategyName: string): Promise<SyncResult | null> {
    const strategy = this.syncStrategies.get(strategyName);
    if (!strategy) {
      console.error(`Unknown sync strategy: ${strategyName}`);
      return null;
    }

    return this.executeSync(strategyName);
  }

  private async executeSync(strategyName: string): Promise<SyncResult | null> {
    const strategy = this.syncStrategies.get(strategyName);
    const schedule = this.syncSchedules.get(strategyName);
    
    if (!strategy || !schedule) {
      return null;
    }

    console.log(`🔄 Executing sync strategy: ${strategyName}`);
    const startTime = Date.now();

    try {
      const result = await this.cache.syncWithPermaGraph(async () => {
        return this.fetchPatternsFromPermaGraph(strategy, schedule);
      });

      // Update schedule
      schedule.lastRun = new Date();
      schedule.lastResult = result;
      schedule.consecutiveFailures = 0;
      schedule.nextRun = new Date(Date.now() + strategy.interval);

      const duration = Date.now() - startTime;
      console.log(`✅ Sync strategy ${strategyName} completed in ${duration}ms: +${result.added}, ~${result.updated}, -${result.removed}`);

      this.emit('sync-completed', {
        strategy: strategyName,
        result,
        duration
      });

      return result;

    } catch (error) {
      schedule.consecutiveFailures++;
      
      // Exponential backoff for failed syncs
      const backoffMultiplier = Math.min(Math.pow(2, schedule.consecutiveFailures), 8);
      schedule.nextRun = new Date(Date.now() + (strategy.interval * backoffMultiplier));

      const duration = Date.now() - startTime;
      console.error(`❌ Sync strategy ${strategyName} failed after ${duration}ms:`, error);

      this.emit('sync-failed', {
        strategy: strategyName,
        error: error as Error,
        duration,
        consecutiveFailures: schedule.consecutiveFailures
      });

      return null;
    }
  }

  private async fetchPatternsFromPermaGraph(
    strategy: SyncStrategy,
    schedule: SyncSchedule
  ): Promise<(AuthPattern | ServicePattern | RequirementChain)[]> {
    console.log(`📡 Fetching patterns from PermaGraph for strategy: ${strategy.name}`);

    const metadata = this.buildStrategyMetadata(strategy, schedule);
    const collected: (AuthPattern | ServicePattern | RequirementChain)[] = [];
    let pageToken: string | undefined;
    let pageCount = 0;

    while (true) {
      if (pageCount >= this.maxPagesPerSync) {
        throw new Error(
          `Exceeded maximum pages (${this.maxPagesPerSync}) while exporting patterns for ${strategy.name}`
        );
      }

      try {
        const response = await this.patternClient.exportPatterns({
          strategy: strategy.name,
          metadata,
          pageToken,
          pageSize: this.exportPageSize,
        });

        pageCount++;
        collected.push(...response.patterns);

        if (response.rateLimit?.retryAfterMs) {
          await this.sleep(response.rateLimit.retryAfterMs);
        }

        if (!response.nextPageToken) {
          break;
        }

        if (response.nextPageToken === pageToken) {
          throw new Error(
            `PermaGraph returned a repeated page token for strategy ${strategy.name}`
          );
        }

        pageToken = response.nextPageToken;
      } catch (error) {
        if (error instanceof PermaGraphRateLimitError) {
          const delay = error.retryAfterMs ?? this.defaultRateLimitDelayMs;
          console.warn(
            `⚠️ PermaGraph rate limit encountered for ${strategy.name}, retrying in ${delay}ms`
          );
          await this.sleep(delay);
          continue;
        }

        throw error;
      }
    }

    return collected;
  }

  private buildStrategyMetadata(strategy: SyncStrategy, schedule: SyncSchedule): Record<string, unknown> {
    const baseMetadata = {
      strategy: strategy.name,
      requestedAt: new Date().toISOString(),
      intervalMs: strategy.interval,
      priority: strategy.priority,
      enabled: strategy.enabled,
      conditions: strategy.conditions,
      lastRun: schedule.lastRun ? schedule.lastRun.toISOString() : null,
      consecutiveFailures: schedule.consecutiveFailures,
      lastResult: schedule.lastResult
        ? {
            added: schedule.lastResult.added,
            updated: schedule.lastResult.updated,
            removed: schedule.lastResult.removed,
            errorCount: schedule.lastResult.errors.length,
          }
        : null,
    } as const;

    switch (strategy.name) {
      case 'periodic-full-sync':
        return {
          ...baseMetadata,
          mode: 'full',
          reason: 'scheduled_full_export',
        };

      case 'incremental-sync':
        return {
          ...baseMetadata,
          mode: 'incremental',
          since: schedule.lastRun ? schedule.lastRun.toISOString() : null,
        };

      case 'emergency-sync':
        return {
          ...baseMetadata,
          mode: 'emergency',
          cacheStats: this.cache.getPatternStats(),
        };

      case 'recovery-sync':
        return {
          ...baseMetadata,
          mode: 'recovery',
          recoveryReason:
            schedule.consecutiveFailures > 0 ? 'post-failure' : 'service-recovery',
        };

      default:
        return baseMetadata;
    }
  }

  async processInvalidationRules(): Promise<void> {
    for (const [ruleName, rule] of this.invalidationRules) {
      if (this.shouldApplyInvalidationRule(rule)) {
        await this.applyInvalidationRule(rule);
      }
    }
  }

  private shouldApplyInvalidationRule(rule: CacheInvalidationRule): boolean {
    // This would implement logic to determine if an invalidation rule should be applied
    // For now, we'll return false to avoid automatic invalidation during testing
    return false;
  }

  private async applyInvalidationRule(rule: CacheInvalidationRule): Promise<void> {
    console.log(`🔄 Applying invalidation rule: ${rule.name}`);
    
    switch (rule.action) {
      case 'invalidate':
        if (rule.criteria.tags) {
          await this.cache.invalidateByTags(rule.criteria.tags);
        }
        break;
      
      case 'refresh':
        // Would trigger refresh of matching patterns
        console.log(`🔄 Refreshing patterns matching rule: ${rule.name}`);
        break;
      
      case 'mark-stale':
        // Would mark patterns as stale without removing them
        console.log(`⚠️ Marking patterns as stale for rule: ${rule.name}`);
        break;
    }
  }

  // External event handlers
  async handleExternalEvent(eventType: string, data: any): Promise<void> {
    console.log(`📡 Received external event: ${eventType}`);
    
    // Check if any invalidation rules match this event
    for (const [ruleName, rule] of this.invalidationRules) {
      if (rule.trigger === 'external-event' && rule.criteria.eventType === eventType) {
        await this.applyInvalidationRule(rule);
      }
    }
    
    // Trigger appropriate sync if needed
    if (eventType === 'permagraph-updated') {
      await this.triggerSync('incremental-sync');
    }
  }

  // Status and monitoring
  getSyncStatus(): {
    isRunning: boolean;
    strategies: Array<{
      name: string;
      enabled: boolean;
      lastRun: Date | null;
      nextRun: Date;
      consecutiveFailures: number;
      lastResult: SyncResult | null;
    }>;
  } {
    const strategies = Array.from(this.syncSchedules.entries()).map(([name, schedule]) => {
      const strategy = this.syncStrategies.get(name)!;
      return {
        name,
        enabled: strategy.enabled,
        lastRun: schedule.lastRun,
        nextRun: schedule.nextRun,
        consecutiveFailures: schedule.consecutiveFailures,
        lastResult: schedule.lastResult
      };
    });

    return {
      isRunning: this.isRunning,
      strategies
    };
  }
}

// Singleton instance
export const cacheSyncService = new CacheSyncService();