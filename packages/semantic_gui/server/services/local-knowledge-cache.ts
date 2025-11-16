/**
 * Local Knowledge Cache Service
 * 
 * Implements local caching for PermaGraph data with TTL management,
 * cache synchronization, and intelligent cache invalidation strategies.
 */

import { promises as fs } from 'fs';
import { join } from 'path';
import { EventEmitter } from 'events';

export interface CacheEntry<T = any> {
  key: string;
  data: T;
  timestamp: Date;
  ttl: number; // Time to live in milliseconds
  accessCount: number;
  lastAccessed: Date;
  tags: string[];
  metadata: Record<string, any>;
}

export interface CacheStats {
  totalEntries: number;
  hitRate: number;
  missRate: number;
  totalHits: number;
  totalMisses: number;
  cacheSize: number; // in bytes
  oldestEntry: Date | null;
  newestEntry: Date | null;
}

export interface CacheConfig {
  maxSize: number; // Maximum cache size in bytes
  maxEntries: number; // Maximum number of entries
  defaultTTL: number; // Default TTL in milliseconds
  cleanupInterval: number; // Cleanup interval in milliseconds
  persistToDisk: boolean;
  cacheDirectory: string;
  compressionEnabled: boolean;
}

export interface KnowledgePattern {
  id: string;
  type: 'auth-pattern' | 'service-pattern' | 'requirement-chain' | 'historical-case';
  framework: string;
  domain: string;
  pattern: any;
  successRate: number;
  usageCount: number;
  lastUpdated: Date;
  relationships: string[];
  metadata: Record<string, any>;
}

export interface QueryResult<T = any> {
  data: T;
  source: 'cache' | 'permagraph';
  confidence: number;
  timestamp: Date;
  metadata: Record<string, any>;
}

export class LocalKnowledgeCache extends EventEmitter {
  private cache: Map<string, CacheEntry> = new Map();
  private stats = {
    hits: 0,
    misses: 0,
    totalSize: 0
  };
  private cleanupTimer: NodeJS.Timeout | null = null;
  private config: CacheConfig;

  constructor(config: Partial<CacheConfig> = {}) {
    super();
    
    this.config = {
      maxSize: 100 * 1024 * 1024, // 100MB
      maxEntries: 10000,
      defaultTTL: 24 * 60 * 60 * 1000, // 24 hours
      cleanupInterval: 60 * 60 * 1000, // 1 hour
      persistToDisk: true,
      cacheDirectory: join(process.cwd(), '.cache', 'knowledge'),
      compressionEnabled: true,
      ...config
    };

    this.initialize();
  }

  private async initialize(): Promise<void> {
    try {
      // Create cache directory if it doesn't exist
      if (this.config.persistToDisk) {
        await fs.mkdir(this.config.cacheDirectory, { recursive: true });
        await this.loadFromDisk();
      }

      // Start cleanup timer
      this.startCleanupTimer();
      
      console.log(`📦 Local knowledge cache initialized with ${this.cache.size} entries`);
      this.emit('cache-initialized', { entries: this.cache.size });
      
    } catch (error) {
      console.error('Failed to initialize local knowledge cache:', error);
      this.emit('cache-error', { error, operation: 'initialize' });
    }
  }

  private startCleanupTimer(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
    }

    this.cleanupTimer = setInterval(() => {
      this.cleanup();
    }, this.config.cleanupInterval);
  }

  private async loadFromDisk(): Promise<void> {
    try {
      const cacheFile = join(this.config.cacheDirectory, 'cache.json');
      const data = await fs.readFile(cacheFile, 'utf-8');
      const entries: Array<[string, CacheEntry]> = JSON.parse(data);
      
      for (const [key, entry] of entries) {
        // Restore Date objects
        entry.timestamp = new Date(entry.timestamp);
        entry.lastAccessed = new Date(entry.lastAccessed);
        
        // Check if entry is still valid
        if (this.isEntryValid(entry)) {
          this.cache.set(key, entry);
          this.stats.totalSize += this.calculateEntrySize(entry);
        }
      }
      
      console.log(`📂 Loaded ${this.cache.size} entries from disk cache`);
      
    } catch (error) {
      // Cache file doesn't exist or is corrupted, start fresh
      console.log('🆕 Starting with fresh cache (no existing cache file)');
    }
  }

  private async saveToDisk(): Promise<void> {
    if (!this.config.persistToDisk) return;

    try {
      const cacheFile = join(this.config.cacheDirectory, 'cache.json');
      const entries = Array.from(this.cache.entries());
      await fs.writeFile(cacheFile, JSON.stringify(entries, null, 2));
      
      this.emit('cache-saved', { entries: entries.length });
      
    } catch (error) {
      console.error('Failed to save cache to disk:', error);
      this.emit('cache-error', { error, operation: 'save' });
    }
  }

  private isEntryValid(entry: CacheEntry): boolean {
    const now = Date.now();
    const entryAge = now - entry.timestamp.getTime();
    return entryAge < entry.ttl;
  }

  private calculateEntrySize(entry: CacheEntry): number {
    return JSON.stringify(entry).length * 2; // Rough estimate (UTF-16)
  }

  private cleanup(): void {
    const now = Date.now();
    let removedCount = 0;
    let freedSize = 0;

    // Remove expired entries
    for (const [key, entry] of this.cache) {
      if (!this.isEntryValid(entry)) {
        const size = this.calculateEntrySize(entry);
        this.cache.delete(key);
        this.stats.totalSize -= size;
        removedCount++;
        freedSize += size;
      }
    }

    // If still over limits, remove least recently used entries
    if (this.cache.size > this.config.maxEntries || this.stats.totalSize > this.config.maxSize) {
      const entries = Array.from(this.cache.entries())
        .sort(([, a], [, b]) => a.lastAccessed.getTime() - b.lastAccessed.getTime());

      while ((this.cache.size > this.config.maxEntries || this.stats.totalSize > this.config.maxSize) && entries.length > 0) {
        const [key, entry] = entries.shift()!;
        const size = this.calculateEntrySize(entry);
        this.cache.delete(key);
        this.stats.totalSize -= size;
        removedCount++;
        freedSize += size;
      }
    }

    if (removedCount > 0) {
      console.log(`🧹 Cache cleanup: removed ${removedCount} entries, freed ${Math.round(freedSize / 1024)}KB`);
      this.emit('cache-cleanup', { removedCount, freedSize });
      
      // Save to disk after cleanup
      this.saveToDisk();
    }
  }

  /**
   * Store data in cache
   */
  async set<T>(
    key: string, 
    data: T, 
    options: {
      ttl?: number;
      tags?: string[];
      metadata?: Record<string, any>;
    } = {}
  ): Promise<void> {
    const entry: CacheEntry<T> = {
      key,
      data,
      timestamp: new Date(),
      ttl: options.ttl || this.config.defaultTTL,
      accessCount: 0,
      lastAccessed: new Date(),
      tags: options.tags || [],
      metadata: options.metadata || {}
    };

    const entrySize = this.calculateEntrySize(entry);
    
    // Check if adding this entry would exceed limits
    if (entrySize > this.config.maxSize) {
      throw new Error(`Entry too large: ${Math.round(entrySize / 1024)}KB exceeds max cache size`);
    }

    // Remove existing entry if it exists
    if (this.cache.has(key)) {
      const oldEntry = this.cache.get(key)!;
      this.stats.totalSize -= this.calculateEntrySize(oldEntry);
    }

    this.cache.set(key, entry);
    this.stats.totalSize += entrySize;

    // Trigger cleanup if needed
    if (this.cache.size > this.config.maxEntries || this.stats.totalSize > this.config.maxSize) {
      this.cleanup();
    }

    this.emit('cache-set', { key, size: entrySize });
  }

  /**
   * Retrieve data from cache
   */
  async get<T>(key: string): Promise<T | null> {
    const entry = this.cache.get(key);
    
    if (!entry) {
      this.stats.misses++;
      this.emit('cache-miss', { key });
      return null;
    }

    if (!this.isEntryValid(entry)) {
      // Entry expired, remove it
      const size = this.calculateEntrySize(entry);
      this.cache.delete(key);
      this.stats.totalSize -= size;
      this.stats.misses++;
      this.emit('cache-expired', { key });
      return null;
    }

    // Update access statistics
    entry.accessCount++;
    entry.lastAccessed = new Date();
    this.stats.hits++;
    
    this.emit('cache-hit', { key, accessCount: entry.accessCount });
    return entry.data as T;
  }

  /**
   * Check if key exists in cache
   */
  has(key: string): boolean {
    const entry = this.cache.get(key);
    return entry ? this.isEntryValid(entry) : false;
  }

  /**
   * Remove entry from cache
   */
  async delete(key: string): Promise<boolean> {
    const entry = this.cache.get(key);
    if (entry) {
      const size = this.calculateEntrySize(entry);
      this.cache.delete(key);
      this.stats.totalSize -= size;
      this.emit('cache-delete', { key, size });
      return true;
    }
    return false;
  }

  /**
   * Clear all cache entries
   */
  async clear(): Promise<void> {
    const count = this.cache.size;
    this.cache.clear();
    this.stats.totalSize = 0;
    this.stats.hits = 0;
    this.stats.misses = 0;
    
    console.log(`🗑️ Cache cleared: removed ${count} entries`);
    this.emit('cache-clear', { count });
  }

  /**
   * Get entries by tags
   */
  async getByTags(tags: string[]): Promise<Array<{ key: string; data: any }>> {
    const results: Array<{ key: string; data: any }> = [];
    
    for (const [key, entry] of this.cache) {
      if (this.isEntryValid(entry) && tags.some(tag => entry.tags.includes(tag))) {
        entry.accessCount++;
        entry.lastAccessed = new Date();
        results.push({ key, data: entry.data });
      }
    }
    
    return results;
  }

  /**
   * Store knowledge pattern
   */
  async storeKnowledgePattern(pattern: KnowledgePattern): Promise<void> {
    const key = `pattern:${pattern.type}:${pattern.framework}:${pattern.id}`;
    await this.set(key, pattern, {
      tags: ['knowledge-pattern', pattern.type, pattern.framework, pattern.domain],
      metadata: {
        successRate: pattern.successRate,
        usageCount: pattern.usageCount,
        lastUpdated: pattern.lastUpdated
      }
    });
  }

  /**
   * Retrieve knowledge patterns by type and framework
   */
  async getKnowledgePatterns(
    type: string, 
    framework?: string, 
    domain?: string
  ): Promise<KnowledgePattern[]> {
    const tags = ['knowledge-pattern', type];
    if (framework) tags.push(framework);
    if (domain) tags.push(domain);
    
    const results = await this.getByTags(tags);
    return results.map(r => r.data as KnowledgePattern);
  }

  /**
   * Query cache with fallback to PermaGraph simulation
   */
  async queryWithFallback<T>(
    query: string,
    queryFn: () => Promise<T>,
    options: {
      cacheKey?: string;
      ttl?: number;
      tags?: string[];
    } = {}
  ): Promise<QueryResult<T>> {
    const cacheKey = options.cacheKey || `query:${Buffer.from(query).toString('base64')}`;
    
    // Try cache first
    const cached = await this.get<T>(cacheKey);
    if (cached) {
      return {
        data: cached,
        source: 'cache',
        confidence: 0.8, // Cache confidence is lower than fresh data
        timestamp: new Date(),
        metadata: { fromCache: true }
      };
    }

    try {
      // Execute query function (would be PermaGraph query in real implementation)
      const data = await queryFn();
      
      // Store in cache
      await this.set(cacheKey, data, {
        ttl: options.ttl,
        tags: options.tags
      });
      
      return {
        data,
        source: 'permagraph',
        confidence: 1.0,
        timestamp: new Date(),
        metadata: { cached: true }
      };
      
    } catch (error) {
      // If query fails, try to find similar cached entries
      const similarEntries = await this.findSimilarEntries(query);
      
      if (similarEntries.length > 0) {
        const bestMatch = similarEntries[0];
        return {
          data: bestMatch.data,
          source: 'cache',
          confidence: 0.5, // Lower confidence for similar matches
          timestamp: new Date(),
          metadata: { 
            fallbackMatch: true, 
            originalQuery: query,
            matchedKey: bestMatch.key
          }
        };
      }
      
      throw error;
    }
  }

  /**
   * Find similar cache entries based on query similarity
   */
  private async findSimilarEntries(query: string): Promise<Array<{ key: string; data: any; similarity: number }>> {
    const results: Array<{ key: string; data: any; similarity: number }> = [];
    const queryWords = query.toLowerCase().split(/\s+/);
    
    for (const [key, entry] of this.cache) {
      if (!this.isEntryValid(entry)) continue;
      
      const keyWords = key.toLowerCase().split(/[:\-_\s]+/);
      const commonWords = queryWords.filter(word => keyWords.includes(word));
      const similarity = commonWords.length / Math.max(queryWords.length, keyWords.length);
      
      if (similarity > 0.3) {
        results.push({ key, data: entry.data, similarity });
      }
    }
    
    return results.sort((a, b) => b.similarity - a.similarity);
  }

  /**
   * Get cache statistics
   */
  getStats(): CacheStats {
    const entries = Array.from(this.cache.values());
    const timestamps = entries.map(e => e.timestamp);
    
    return {
      totalEntries: this.cache.size,
      hitRate: this.stats.hits / (this.stats.hits + this.stats.misses) || 0,
      missRate: this.stats.misses / (this.stats.hits + this.stats.misses) || 0,
      totalHits: this.stats.hits,
      totalMisses: this.stats.misses,
      cacheSize: this.stats.totalSize,
      oldestEntry: timestamps.length > 0 ? new Date(Math.min(...timestamps.map(t => t.getTime()))) : null,
      newestEntry: timestamps.length > 0 ? new Date(Math.max(...timestamps.map(t => t.getTime()))) : null
    };
  }

  /**
   * Invalidate cache entries by tags
   */
  async invalidateByTags(tags: string[]): Promise<number> {
    let removedCount = 0;
    
    for (const [key, entry] of this.cache) {
      if (tags.some(tag => entry.tags.includes(tag))) {
        const size = this.calculateEntrySize(entry);
        this.cache.delete(key);
        this.stats.totalSize -= size;
        removedCount++;
      }
    }
    
    if (removedCount > 0) {
      console.log(`🔄 Invalidated ${removedCount} cache entries by tags: ${tags.join(', ')}`);
      this.emit('cache-invalidate', { tags, removedCount });
      await this.saveToDisk();
    }
    
    return removedCount;
  }

  /**
   * Sync with PermaGraph (placeholder for real implementation)
   */
  async syncWithPermaGraph(): Promise<{ updated: number; added: number; removed: number }> {
    // This would implement actual synchronization with PermaGraph
    // For now, we'll simulate the sync process
    
    console.log('🔄 Syncing local cache with PermaGraph...');
    
    // Simulate sync results
    const syncResults = {
      updated: 0,
      added: 0,
      removed: 0
    };
    
    this.emit('cache-sync', syncResults);
    return syncResults;
  }

  /**
   * Shutdown cache and cleanup
   */
  async shutdown(): Promise<void> {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
    
    await this.saveToDisk();
    console.log('💾 Local knowledge cache shutdown complete');
    this.emit('cache-shutdown');
  }
}

// Singleton instance
export const localKnowledgeCache = new LocalKnowledgeCache();