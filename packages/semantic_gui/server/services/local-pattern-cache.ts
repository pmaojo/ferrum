/**
 * Local Pattern Cache
 * 
 * Implements file-based pattern storage with JSON serialization,
 * cache indexing for fast pattern lookup and filtering,
 * and cache size management with LRU eviction policy.
 * 
 * This extends the LocalKnowledgeCache to provide specialized
 * pattern storage and retrieval for 2FA payment service integration.
 */

import { promises as fs } from 'fs';
import { join } from 'path';
import { EventEmitter } from 'events';
import { AuthPattern, ServicePattern, RequirementChain, PatternMetadata } from './pattern-models';
import { LocalKnowledgeCache, CacheConfig, CacheEntry } from './local-knowledge-cache';

export interface PatternCacheEntry extends CacheEntry {
  patternType: 'auth' | 'service' | 'requirement';
  framework: string;
  domain: string;
  successRate: number;
  architecturalFit: number;
  securityScore: number;
  lastUsed: Date;
}

export interface CacheIndexEntry {
  id: string;
  type: 'auth' | 'service' | 'requirement';
  framework: string;
  tags: string[];
  successRate: number;
  architecturalFit: number;
  lastAccessed: Date;
  filePath: string;
}

export interface PatternSearchCriteria {
  type?: 'auth' | 'service' | 'requirement';
  framework?: string;
  tags?: string[];
  minSuccessRate?: number;
  minArchitecturalFit?: number;
  maxAge?: number; // in milliseconds
  deprecated?: boolean;
}

export interface PatternCacheStats {
  totalPatterns: number;
  authPatterns: number;
  servicePatterns: number;
  requirementChains: number;
  frameworks: Record<string, number>;
  averageSuccessRate: number;
  cacheHitRate: number;
  diskUsage: number;
  indexSize: number;
}

export interface SyncResult {
  updated: number;
  added: number;
  removed: number;
  errors: string[];
}

export class LocalPatternCache extends LocalKnowledgeCache {
  private patternIndex: Map<string, CacheIndexEntry> = new Map();
  private frameworkIndex: Map<string, Set<string>> = new Map();
  private tagIndex: Map<string, Set<string>> = new Map();
  private typeIndex: Map<string, Set<string>> = new Map();
  private indexFile: string;
  private patternsDirectory: string;

  constructor(config: Partial<CacheConfig> = {}) {
    super({
      ...config,
      cacheDirectory: config.cacheDirectory || join(process.cwd(), '.cache', 'patterns')
    });

    this.indexFile = join(this.config.cacheDirectory, 'pattern-index.json');
    this.patternsDirectory = join(this.config.cacheDirectory, 'patterns');
  }

  protected async initialize(): Promise<void> {
    await super.initialize();
    
    try {
      // Create patterns directory
      await fs.mkdir(this.patternsDirectory, { recursive: true });
      
      // Load pattern index
      await this.loadPatternIndex();
      
      console.log(`📋 Pattern cache initialized with ${this.patternIndex.size} indexed patterns`);
      this.emit('pattern-cache-initialized', { 
        patterns: this.patternIndex.size,
        frameworks: this.frameworkIndex.size,
        tags: this.tagIndex.size
      });
      
    } catch (error) {
      console.error('Failed to initialize pattern cache:', error);
      this.emit('pattern-cache-error', { error, operation: 'initialize' });
    }
  }

  private async loadPatternIndex(): Promise<void> {
    try {
      const indexData = await fs.readFile(this.indexFile, 'utf-8');
      const entries: CacheIndexEntry[] = JSON.parse(indexData);
      
      for (const entry of entries) {
        // Restore Date objects
        entry.lastAccessed = new Date(entry.lastAccessed);
        
        // Check if pattern file still exists
        const patternExists = await this.fileExists(entry.filePath);
        if (patternExists) {
          this.addToIndex(entry);
        }
      }
      
      console.log(`📂 Loaded ${this.patternIndex.size} pattern index entries`);
      
    } catch (error) {
      // Index file doesn't exist or is corrupted, start fresh
      console.log('🆕 Starting with fresh pattern index');
      await this.rebuildIndex();
    }
  }

  private async rebuildIndex(): Promise<void> {
    console.log('🔄 Rebuilding pattern index from disk...');
    
    try {
      const patternFiles = await fs.readdir(this.patternsDirectory);
      let rebuiltCount = 0;
      
      for (const fileName of patternFiles) {
        if (!fileName.endsWith('.json')) continue;
        
        try {
          const filePath = join(this.patternsDirectory, fileName);
          const patternData = await fs.readFile(filePath, 'utf-8');
          const pattern = JSON.parse(patternData);
          
          // Create index entry
          const indexEntry: CacheIndexEntry = {
            id: pattern.id,
            type: this.determinePatternType(pattern),
            framework: pattern.framework || 'generic',
            tags: pattern.tags || [],
            successRate: pattern.successRate || 0,
            architecturalFit: pattern.architecturalFit || 0,
            lastAccessed: new Date(pattern.updatedAt || pattern.createdAt),
            filePath
          };
          
          this.addToIndex(indexEntry);
          rebuiltCount++;
          
        } catch (error) {
          console.warn(`Failed to index pattern file ${fileName}:`, error);
        }
      }
      
      await this.savePatternIndex();
      console.log(`✅ Rebuilt index with ${rebuiltCount} patterns`);
      
    } catch (error) {
      console.error('Failed to rebuild pattern index:', error);
    }
  }

  private addToIndex(entry: CacheIndexEntry): void {
    this.patternIndex.set(entry.id, entry);
    
    // Update framework index
    if (!this.frameworkIndex.has(entry.framework)) {
      this.frameworkIndex.set(entry.framework, new Set());
    }
    this.frameworkIndex.get(entry.framework)!.add(entry.id);
    
    // Update tag index
    for (const tag of entry.tags) {
      if (!this.tagIndex.has(tag)) {
        this.tagIndex.set(tag, new Set());
      }
      this.tagIndex.get(tag)!.add(entry.id);
    }
    
    // Update type index
    if (!this.typeIndex.has(entry.type)) {
      this.typeIndex.set(entry.type, new Set());
    }
    this.typeIndex.get(entry.type)!.add(entry.id);
  }

  private removeFromIndex(patternId: string): void {
    const entry = this.patternIndex.get(patternId);
    if (!entry) return;
    
    // Remove from main index
    this.patternIndex.delete(patternId);
    
    // Remove from framework index
    const frameworkSet = this.frameworkIndex.get(entry.framework);
    if (frameworkSet) {
      frameworkSet.delete(patternId);
      if (frameworkSet.size === 0) {
        this.frameworkIndex.delete(entry.framework);
      }
    }
    
    // Remove from tag index
    for (const tag of entry.tags) {
      const tagSet = this.tagIndex.get(tag);
      if (tagSet) {
        tagSet.delete(patternId);
        if (tagSet.size === 0) {
          this.tagIndex.delete(tag);
        }
      }
    }
    
    // Remove from type index
    const typeSet = this.typeIndex.get(entry.type);
    if (typeSet) {
      typeSet.delete(patternId);
      if (typeSet.size === 0) {
        this.typeIndex.delete(entry.type);
      }
    }
  }

  private async savePatternIndex(): Promise<void> {
    try {
      // Ensure directory exists
      await fs.mkdir(this.config.cacheDirectory, { recursive: true });
      
      const entries = Array.from(this.patternIndex.values());
      await fs.writeFile(this.indexFile, JSON.stringify(entries, null, 2));
      this.emit('pattern-index-saved', { entries: entries.length });
    } catch (error) {
      console.error('Failed to save pattern index:', error);
      this.emit('pattern-cache-error', { error, operation: 'save-index' });
    }
  }

  private determinePatternType(pattern: any): 'auth' | 'service' | 'requirement' {
    if (pattern.type && ['2fa', 'oauth', 'jwt', 'session', 'totp', 'backup_codes', 'biometric'].includes(pattern.type)) {
      return 'auth';
    }
    if (pattern.type && ['payment_gateway', 'payment_processor', 'billing', 'subscription', 'wallet', 'fraud_detection'].includes(pattern.type)) {
      return 'service';
    }
    if (pattern.sourceRequirement || pattern.linkedRequirements) {
      return 'requirement';
    }
    throw new Error(`Unable to determine pattern type for pattern: ${pattern.id}`);
  }

  private async fileExists(filePath: string): Promise<boolean> {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }

  private generatePatternFileName(pattern: AuthPattern | ServicePattern | RequirementChain): string {
    const type = this.determinePatternType(pattern);
    const framework = 'framework' in pattern ? pattern.framework : 'generic';
    const timestamp = Date.now();
    return `${type}-${framework}-${pattern.id}-${timestamp}.json`;
  }

  /**
   * Store a pattern in the cache with indexing
   */
  async storePattern(
    pattern: AuthPattern | ServicePattern | RequirementChain,
    options: {
      ttl?: number;
      tags?: string[];
      metadata?: Record<string, any>;
    } = {}
  ): Promise<void> {
    const fileName = this.generatePatternFileName(pattern);
    const filePath = join(this.patternsDirectory, fileName);
    
    try {
      // Store pattern to disk
      await fs.writeFile(filePath, JSON.stringify(pattern, null, 2));
      
      // Create index entry
      const indexEntry: CacheIndexEntry = {
        id: pattern.id,
        type: this.determinePatternType(pattern),
        framework: 'framework' in pattern ? pattern.framework : 'generic',
        tags: [...(pattern.tags || []), ...(options.tags || [])],
        successRate: pattern.successRate,
        architecturalFit: 'architecturalFit' in pattern ? pattern.architecturalFit : 0,
        lastAccessed: new Date(),
        filePath
      };
      
      // Update indexes
      this.addToIndex(indexEntry);
      
      // Also store in memory cache for fast access
      await this.set(pattern.id, pattern, {
        ttl: options.ttl,
        tags: indexEntry.tags,
        metadata: options.metadata
      });
      
      // Save index to disk
      await this.savePatternIndex();
      
      console.log(`💾 Stored pattern ${pattern.id} (${indexEntry.type}/${indexEntry.framework})`);
      this.emit('pattern-stored', { 
        patternId: pattern.id, 
        type: indexEntry.type, 
        framework: indexEntry.framework 
      });
      
    } catch (error) {
      console.error(`Failed to store pattern ${pattern.id}:`, error);
      this.emit('pattern-cache-error', { error, operation: 'store', patternId: pattern.id });
      throw error;
    }
  }

  /**
   * Retrieve a pattern by ID
   */
  async getPattern(patternId: string): Promise<AuthPattern | ServicePattern | RequirementChain | null> {
    // Try memory cache first
    const cached = await this.get<AuthPattern | ServicePattern | RequirementChain>(patternId);
    if (cached) {
      // Update access time in index
      const indexEntry = this.patternIndex.get(patternId);
      if (indexEntry) {
        indexEntry.lastAccessed = new Date();
        await this.savePatternIndex();
      }
      return cached;
    }
    
    // Try disk cache
    const indexEntry = this.patternIndex.get(patternId);
    if (!indexEntry) {
      return null;
    }
    
    try {
      const patternData = await fs.readFile(indexEntry.filePath, 'utf-8');
      const pattern = JSON.parse(patternData);
      
      // Restore Date objects
      if (pattern.createdAt) pattern.createdAt = new Date(pattern.createdAt);
      if (pattern.updatedAt) pattern.updatedAt = new Date(pattern.updatedAt);
      if (pattern.historicalUsage?.lastUsed) {
        pattern.historicalUsage.lastUsed = new Date(pattern.historicalUsage.lastUsed);
      }
      
      // Update access time
      indexEntry.lastAccessed = new Date();
      await this.savePatternIndex();
      
      // Store in memory cache for future access
      await this.set(patternId, pattern);
      
      return pattern;
      
    } catch (error) {
      console.error(`Failed to load pattern ${patternId} from disk:`, error);
      // Remove invalid entry from index
      this.removeFromIndex(patternId);
      await this.savePatternIndex();
      return null;
    }
  }

  /**
   * Find patterns by type
   */
  async findPatternsByType(type: 'auth' | 'service' | 'requirement'): Promise<(AuthPattern | ServicePattern | RequirementChain)[]> {
    const patternIds = this.typeIndex.get(type) || new Set();
    const patterns: (AuthPattern | ServicePattern | RequirementChain)[] = [];
    
    for (const patternId of patternIds) {
      const pattern = await this.getPattern(patternId);
      if (pattern) {
        patterns.push(pattern);
      }
    }
    
    return patterns.sort((a, b) => b.successRate - a.successRate);
  }

  /**
   * Find patterns by framework
   */
  async findPatternsByFramework(framework: string): Promise<(AuthPattern | ServicePattern | RequirementChain)[]> {
    const patternIds = this.frameworkIndex.get(framework) || new Set();
    const patterns: (AuthPattern | ServicePattern | RequirementChain)[] = [];
    
    for (const patternId of patternIds) {
      const pattern = await this.getPattern(patternId);
      if (pattern) {
        patterns.push(pattern);
      }
    }
    
    return patterns.sort((a, b) => b.successRate - a.successRate);
  }

  /**
   * Find patterns by tags
   */
  async findPatternsByTags(tags: string[]): Promise<(AuthPattern | ServicePattern | RequirementChain)[]> {
    const matchingIds = new Set<string>();
    
    for (const tag of tags) {
      const tagIds = this.tagIndex.get(tag) || new Set();
      for (const id of tagIds) {
        matchingIds.add(id);
      }
    }
    
    const patterns: (AuthPattern | ServicePattern | RequirementChain)[] = [];
    for (const patternId of matchingIds) {
      const pattern = await this.getPattern(patternId);
      if (pattern) {
        patterns.push(pattern);
      }
    }
    
    return patterns.sort((a, b) => b.successRate - a.successRate);
  }

  /**
   * Search patterns with complex criteria
   */
  async searchPatterns(criteria: PatternSearchCriteria): Promise<(AuthPattern | ServicePattern | RequirementChain)[]> {
    let candidateIds = new Set<string>(this.patternIndex.keys());
    
    // Filter by type
    if (criteria.type) {
      const typeIds = this.typeIndex.get(criteria.type) || new Set();
      candidateIds = new Set([...candidateIds].filter(id => typeIds.has(id)));
    }
    
    // Filter by framework
    if (criteria.framework) {
      const frameworkIds = this.frameworkIndex.get(criteria.framework) || new Set();
      candidateIds = new Set([...candidateIds].filter(id => frameworkIds.has(id)));
    }
    
    // Filter by tags
    if (criteria.tags && criteria.tags.length > 0) {
      const tagIds = new Set<string>();
      for (const tag of criteria.tags) {
        const ids = this.tagIndex.get(tag) || new Set();
        for (const id of ids) {
          tagIds.add(id);
        }
      }
      candidateIds = new Set([...candidateIds].filter(id => tagIds.has(id)));
    }
    
    // Apply additional filters
    const filteredIds: string[] = [];
    for (const patternId of candidateIds) {
      const indexEntry = this.patternIndex.get(patternId);
      if (!indexEntry) continue;
      
      // Filter by success rate
      if (criteria.minSuccessRate && indexEntry.successRate < criteria.minSuccessRate) {
        continue;
      }
      
      // Filter by architectural fit
      if (criteria.minArchitecturalFit && indexEntry.architecturalFit < criteria.minArchitecturalFit) {
        continue;
      }
      
      // Filter by age
      if (criteria.maxAge) {
        const age = Date.now() - indexEntry.lastAccessed.getTime();
        if (age > criteria.maxAge) {
          continue;
        }
      }
      
      filteredIds.push(patternId);
    }
    
    // Load and return patterns
    const patterns: (AuthPattern | ServicePattern | RequirementChain)[] = [];
    for (const patternId of filteredIds) {
      const pattern = await this.getPattern(patternId);
      if (pattern) {
        // Apply deprecated filter
        if (criteria.deprecated !== undefined && pattern.deprecated !== criteria.deprecated) {
          continue;
        }
        patterns.push(pattern);
      }
    }
    
    return patterns.sort((a, b) => b.successRate - a.successRate);
  }

  /**
   * Refresh a pattern with updated data
   */
  async refreshPattern(updatedPattern: AuthPattern | ServicePattern | RequirementChain): Promise<void> {
    // Remove old version
    await this.deletePattern(updatedPattern.id);
    
    // Store updated version
    await this.storePattern(updatedPattern);
    
    console.log(`🔄 Refreshed pattern ${updatedPattern.id}`);
    this.emit('pattern-refreshed', { patternId: updatedPattern.id });
  }

  /**
   * Delete a pattern from cache
   */
  async deletePattern(patternId: string): Promise<boolean> {
    const indexEntry = this.patternIndex.get(patternId);
    if (!indexEntry) {
      return false;
    }
    
    try {
      // Remove from disk
      await fs.unlink(indexEntry.filePath);
      
      // Remove from memory cache
      await this.delete(patternId);
      
      // Remove from indexes
      this.removeFromIndex(patternId);
      await this.savePatternIndex();
      
      console.log(`🗑️ Deleted pattern ${patternId}`);
      this.emit('pattern-deleted', { patternId });
      
      return true;
      
    } catch (error) {
      console.error(`Failed to delete pattern ${patternId}:`, error);
      this.emit('pattern-cache-error', { error, operation: 'delete', patternId });
      return false;
    }
  }

  /**
   * Invalidate patterns by tags
   */
  async invalidateByTags(tags: string[]): Promise<number> {
    const patternsToInvalidate = new Set<string>();
    
    for (const tag of tags) {
      const tagIds = this.tagIndex.get(tag) || new Set();
      for (const id of tagIds) {
        patternsToInvalidate.add(id);
      }
    }
    
    let invalidatedCount = 0;
    for (const patternId of patternsToInvalidate) {
      const success = await this.deletePattern(patternId);
      if (success) {
        invalidatedCount++;
      }
    }
    
    console.log(`🔄 Invalidated ${invalidatedCount} patterns by tags: ${tags.join(', ')}`);
    this.emit('patterns-invalidated', { tags, count: invalidatedCount });
    
    return invalidatedCount;
  }

  /**
   * Sync cache with external source (PermaGraph)
   */
  async syncWithPermaGraph(
    fetchPatterns: () => Promise<(AuthPattern | ServicePattern | RequirementChain)[]>
  ): Promise<SyncResult> {
    console.log('🔄 Syncing pattern cache with PermaGraph...');
    
    const result: SyncResult = {
      updated: 0,
      added: 0,
      removed: 0,
      errors: []
    };
    
    try {
      const externalPatterns = await fetchPatterns();
      const externalIds = new Set(externalPatterns.map(p => p.id));
      const localIds = new Set(this.patternIndex.keys());
      
      // Add or update patterns
      for (const pattern of externalPatterns) {
        try {
          const existsLocally = localIds.has(pattern.id);
          
          if (existsLocally) {
            const localPattern = await this.getPattern(pattern.id);
            if (localPattern && localPattern.updatedAt < pattern.updatedAt) {
              await this.refreshPattern(pattern);
              result.updated++;
            }
          } else {
            await this.storePattern(pattern);
            result.added++;
          }
        } catch (error) {
          result.errors.push(`Failed to sync pattern ${pattern.id}: ${(error as Error).message}`);
        }
      }
      
      // Remove patterns that no longer exist externally
      for (const localId of localIds) {
        if (!externalIds.has(localId)) {
          try {
            await this.deletePattern(localId);
            result.removed++;
          } catch (error) {
            result.errors.push(`Failed to remove pattern ${localId}: ${(error as Error).message}`);
          }
        }
      }
      
      console.log(`✅ Sync complete: +${result.added}, ~${result.updated}, -${result.removed}, errors: ${result.errors.length}`);
      this.emit('sync-complete', result);
      
    } catch (error) {
      result.errors.push(`Sync failed: ${(error as Error).message}`);
      console.error('Pattern cache sync failed:', error);
      this.emit('sync-error', { error });
    }
    
    return result;
  }

  /**
   * Force sync to disk
   */
  async syncToDisk(): Promise<void> {
    await this.savePatternIndex();
    await this.saveToDisk();
    console.log('💾 Pattern cache synced to disk');
  }

  /**
   * Get pattern cache statistics
   */
  getPatternStats(): PatternCacheStats {
    const baseStats = this.getStats();
    
    const frameworks: Record<string, number> = {};
    for (const [framework, ids] of this.frameworkIndex) {
      frameworks[framework] = ids.size;
    }
    
    const authPatterns = this.typeIndex.get('auth')?.size || 0;
    const servicePatterns = this.typeIndex.get('service')?.size || 0;
    const requirementChains = this.typeIndex.get('requirement')?.size || 0;
    
    const totalSuccessRate = Array.from(this.patternIndex.values())
      .reduce((sum, entry) => sum + entry.successRate, 0);
    const averageSuccessRate = this.patternIndex.size > 0 ? totalSuccessRate / this.patternIndex.size : 0;
    
    return {
      totalPatterns: this.patternIndex.size,
      authPatterns,
      servicePatterns,
      requirementChains,
      frameworks,
      averageSuccessRate,
      cacheHitRate: baseStats.hitRate,
      diskUsage: baseStats.cacheSize,
      indexSize: JSON.stringify(Array.from(this.patternIndex.values())).length
    };
  }

  /**
   * Cleanup and shutdown
   */
  async shutdown(): Promise<void> {
    await this.savePatternIndex();
    await super.shutdown();
    console.log('💾 Pattern cache shutdown complete');
  }
}

// Singleton instance
export const localPatternCache = new LocalPatternCache();