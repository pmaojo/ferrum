/**
 * Cache Manager for Frequently Accessed Data
 * Implements multi-level caching with Redis fallback to memory
 */

import { serviceManager } from './service-manager';

export interface CacheEntry<T = any> {
  data: T;
  timestamp: number;
  ttl: number;
  hits: number;
}

export interface CacheStats {
  memoryEntries: number;
  memorySize: number;
  redisAvailable: boolean;
  hitRate: number;
  totalHits: number;
  totalMisses: number;
}

export class CacheManager {
  private memoryCache: Map<string, CacheEntry> = new Map();
  private readonly MAX_MEMORY_ENTRIES = 1000;
  private readonly DEFAULT_TTL = 300000; // 5 minutes
  private totalHits = 0;
  private totalMisses = 0;
  private cleanupInterval: NodeJS.Timeout | null = null;

  constructor() {
    this.startCleanupInterval();
  }

  private startCleanupInterval() {
    // Clean up expired entries every minute
    this.cleanupInterval = setInterval(() => {
      this.cleanupExpiredEntries();
    }, 60000);
  }

  private cleanupExpiredEntries() {
    const now = Date.now();
    const expiredKeys: string[] = [];

    for (const [key, entry] of this.memoryCache.entries()) {
      if (now - entry.timestamp > entry.ttl) {
        expiredKeys.push(key);
      }
    }

    expiredKeys.forEach(key => this.memoryCache.delete(key));

    // If memory cache is too large, remove least recently used entries
    if (this.memoryCache.size > this.MAX_MEMORY_ENTRIES) {
      const entries = Array.from(this.memoryCache.entries())
        .sort((a, b) => a[1].timestamp - b[1].timestamp);
      
      const toRemove = entries.slice(0, entries.length - this.MAX_MEMORY_ENTRIES);
      toRemove.forEach(([key]) => this.memoryCache.delete(key));
    }
  }

  public async get<T = any>(key: string): Promise<T | null> {
    // Try memory cache first
    const memoryEntry = this.memoryCache.get(key);
    if (memoryEntry && Date.now() - memoryEntry.timestamp < memoryEntry.ttl) {
      memoryEntry.hits++;
      this.totalHits++;
      return memoryEntry.data as T;
    }

    // Try Redis cache if available
    try {
      const redisService = await serviceManager.getService('redis');
      if (redisService) {
        const redisData = await this.getFromRedis<T>(key);
        if (redisData !== null) {
          // Store in memory cache for faster access
          this.memoryCache.set(key, {
            data: redisData,
            timestamp: Date.now(),
            ttl: this.DEFAULT_TTL,
            hits: 1
          });
          this.totalHits++;
          return redisData;
        }
      }
    } catch (error) {
      console.warn('Redis cache unavailable, using memory cache only:', error);
    }

    this.totalMisses++;
    return null;
  }

  public async set<T = any>(
    key: string, 
    data: T, 
    ttl: number = this.DEFAULT_TTL
  ): Promise<void> {
    // Store in memory cache
    this.memoryCache.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
      hits: 0
    });

    // Store in Redis if available
    try {
      const redisService = await serviceManager.getService('redis');
      if (redisService) {
        await this.setInRedis(key, data, ttl);
      }
    } catch (error) {
      console.warn('Redis cache unavailable for write, using memory cache only:', error);
    }
  }

  public async delete(key: string): Promise<void> {
    // Remove from memory cache
    this.memoryCache.delete(key);

    // Remove from Redis if available
    try {
      const redisService = await serviceManager.getService('redis');
      if (redisService) {
        await this.deleteFromRedis(key);
      }
    } catch (error) {
      console.warn('Redis cache unavailable for delete:', error);
    }
  }

  public async clear(): Promise<void> {
    // Clear memory cache
    this.memoryCache.clear();

    // Clear Redis if available
    try {
      const redisService = await serviceManager.getService('redis');
      if (redisService) {
        await this.clearRedis();
      }
    } catch (error) {
      console.warn('Redis cache unavailable for clear:', error);
    }
  }

  private async getFromRedis<T>(key: string): Promise<T | null> {
    try {
      // This would be implemented with actual Redis client
      const response = await fetch(`${process.env.REDIS_URL}/get`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key })
      });

      if (!response.ok) {
        return null;
      }

      const result = await response.json();
      return result.data ? JSON.parse(result.data) : null;
    } catch (error) {
      console.warn('Redis get failed:', error);
      return null;
    }
  }

  private async setInRedis<T>(key: string, data: T, ttl: number): Promise<void> {
    try {
      // This would be implemented with actual Redis client
      await fetch(`${process.env.REDIS_URL}/set`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          key, 
          data: JSON.stringify(data), 
          ttl: Math.floor(ttl / 1000) // Redis expects seconds
        })
      });
    } catch (error) {
      console.warn('Redis set failed:', error);
    }
  }

  private async deleteFromRedis(key: string): Promise<void> {
    try {
      await fetch(`${process.env.REDIS_URL}/del`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key })
      });
    } catch (error) {
      console.warn('Redis delete failed:', error);
    }
  }

  private async clearRedis(): Promise<void> {
    try {
      await fetch(`${process.env.REDIS_URL}/flushall`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
    } catch (error) {
      console.warn('Redis clear failed:', error);
    }
  }

  public getStats(): CacheStats {
    const memorySize = Array.from(this.memoryCache.values())
      .reduce((size, entry) => size + JSON.stringify(entry.data).length, 0);

    const totalRequests = this.totalHits + this.totalMisses;
    const hitRate = totalRequests > 0 ? this.totalHits / totalRequests : 0;

    return {
      memoryEntries: this.memoryCache.size,
      memorySize,
      redisAvailable: serviceManager.getServiceStatus('redis').available,
      hitRate,
      totalHits: this.totalHits,
      totalMisses: this.totalMisses
    };
  }

  public destroy() {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
    this.memoryCache.clear();
  }
}

// Specialized cache instances for different data types
export class TemplateCache extends CacheManager {
  private readonly TEMPLATE_TTL = 600000; // 10 minutes

  public async getTemplate(templateId: string): Promise<any | null> {
    return this.get(`template:${templateId}`);
  }

  public async setTemplate(templateId: string, template: any): Promise<void> {
    return this.set(`template:${templateId}`, template, this.TEMPLATE_TTL);
  }
}

export class ProjectCache extends CacheManager {
  private readonly PROJECT_TTL = 300000; // 5 minutes

  public async getProject(projectId: string): Promise<any | null> {
    return this.get(`project:${projectId}`);
  }

  public async setProject(projectId: string, project: any): Promise<void> {
    return this.set(`project:${projectId}`, project, this.PROJECT_TTL);
  }

  public async getProjectList(userId: string): Promise<any[] | null> {
    return this.get(`projects:${userId}`);
  }

  public async setProjectList(userId: string, projects: any[]): Promise<void> {
    return this.set(`projects:${userId}`, projects, this.PROJECT_TTL);
  }
}

export class GraphCache extends CacheManager {
  private readonly GRAPH_TTL = 180000; // 3 minutes

  public async getGraphData(graphId: string): Promise<any | null> {
    return this.get(`graph:${graphId}`);
  }

  public async setGraphData(graphId: string, graphData: any): Promise<void> {
    return this.set(`graph:${graphId}`, graphData, this.GRAPH_TTL);
  }
}

// Singleton instances
export const templateCache = new TemplateCache();
export const projectCache = new ProjectCache();
export const graphCache = new GraphCache();

// Graceful shutdown
process.on('SIGTERM', () => {
  templateCache.destroy();
  projectCache.destroy();
  graphCache.destroy();
});

process.on('SIGINT', () => {
  templateCache.destroy();
  projectCache.destroy();
  graphCache.destroy();
});