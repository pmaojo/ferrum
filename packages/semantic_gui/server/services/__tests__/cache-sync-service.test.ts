import { CacheSyncService } from '../cache-sync-service';
import { SyncResult, PatternCacheStats } from '../local-pattern-cache';
import {
  emergencyExportBatch,
  fullExportBatch,
  incrementalExportBatch,
} from './fixtures/pattern-fixtures';
import {
  PermaGraphPatternClient,
  PermaGraphRateLimitError,
} from '../permagraph-pattern-client';

describe('CacheSyncService synchronization', () => {
  const defaultStats: PatternCacheStats = {
    totalPatterns: 25,
    authPatterns: 10,
    servicePatterns: 10,
    requirementChains: 5,
    frameworks: { tuetano: 5 },
    averageSuccessRate: 0.85,
    cacheHitRate: 0.5,
    diskUsage: 1024,
    indexSize: 512,
  };

  let patternClient: jest.Mocked<PermaGraphPatternClient>;
  let sleep: jest.MockedFunction<(ms: number) => Promise<void>>;
  let cache: {
    syncWithPermaGraph: jest.Mock<Promise<SyncResult>, [() => Promise<any[]>]>;
    getPatternStats: jest.Mock<PatternCacheStats, []>;
    invalidateByTags: jest.Mock;
  };
  let service: CacheSyncService;

  beforeEach(() => {
    patternClient = {
      exportPatterns: jest.fn(),
    } as unknown as jest.Mocked<PermaGraphPatternClient>;

    sleep = jest.fn().mockResolvedValue(undefined);

    cache = {
      syncWithPermaGraph: jest.fn(async fetchPatterns => {
        const patterns = await fetchPatterns();
        return {
          updated: 0,
          added: patterns.length,
          removed: 0,
          errors: [],
        } satisfies SyncResult;
      }),
      getPatternStats: jest.fn(() => defaultStats),
      invalidateByTags: jest.fn(),
    };

    service = new CacheSyncService(
      cache as unknown as any,
      patternClient,
      sleep
    );
  });

  afterEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  it('fetches all paginated results for full sync and persists to cache', async () => {
    const firstPage = fullExportBatch();
    const secondPage = incrementalExportBatch();

    patternClient.exportPatterns
      .mockResolvedValueOnce({
        patterns: firstPage,
        nextPageToken: 'page-2',
      })
      .mockResolvedValueOnce({
        patterns: secondPage,
      });

    const result = await service.triggerSync('periodic-full-sync');

    expect(result).toEqual({ added: 4, updated: 0, removed: 0, errors: [] });
    expect(cache.syncWithPermaGraph).toHaveBeenCalledTimes(1);
    expect(patternClient.exportPatterns).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        strategy: 'periodic-full-sync',
        pageToken: undefined,
        pageSize: 200,
        metadata: expect.objectContaining({ mode: 'full' }),
      })
    );
    expect(patternClient.exportPatterns).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ pageToken: 'page-2' })
    );
  });

  it('passes incremental metadata including last run timestamp', async () => {
    const schedule = (service as unknown as {
      syncSchedules: Map<string, any>;
    }).syncSchedules.get('incremental-sync');
    const lastRun = new Date('2024-02-01T12:00:00Z');
    schedule.lastRun = lastRun;

    patternClient.exportPatterns.mockResolvedValue({ patterns: [] });

    await service.triggerSync('incremental-sync');

    expect(patternClient.exportPatterns).toHaveBeenCalledWith(
      expect.objectContaining({
        strategy: 'incremental-sync',
        metadata: expect.objectContaining({
          mode: 'incremental',
          since: lastRun.toISOString(),
        }),
      })
    );
  });

  it('waits and retries when rate limited', async () => {
    patternClient.exportPatterns
      .mockRejectedValueOnce(new PermaGraphRateLimitError('rate', 75))
      .mockResolvedValueOnce({ patterns: emergencyExportBatch() });

    const result = await service.triggerSync('emergency-sync');

    expect(result).toEqual({ added: 2, updated: 0, removed: 0, errors: [] });
    expect(sleep).toHaveBeenCalledWith(75);
    expect(patternClient.exportPatterns).toHaveBeenCalledTimes(2);
  });

  it('applies exponential backoff when export fails', async () => {
    jest.useFakeTimers();
    const now = new Date('2025-01-01T00:00:00Z');
    jest.setSystemTime(now);

    patternClient.exportPatterns.mockRejectedValue(new Error('network'));

    const outcome = await service.triggerSync('incremental-sync');
    expect(outcome).toBeNull();

    const { syncSchedules, syncStrategies } = service as unknown as {
      syncSchedules: Map<string, any>;
      syncStrategies: Map<string, any>;
    };

    const schedule = syncSchedules.get('incremental-sync');
    const strategy = syncStrategies.get('incremental-sync');

    expect(schedule.consecutiveFailures).toBe(1);
    expect(schedule.nextRun.getTime()).toBe(
      now.getTime() + strategy.interval * 2
    );
  });
});

