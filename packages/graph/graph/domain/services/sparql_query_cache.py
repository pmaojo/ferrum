"""
SPARQL Query Cache Service for Performance Optimization

This service implements intelligent caching for SPARQL queries to improve
performance for frequently executed queries.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import json
import threading
from collections import OrderedDict
from abc import ABC, abstractmethod
import logging


logger = logging.getLogger(__name__)


@dataclass
class QueryCacheEntry:
    """Cache entry for SPARQL query results"""
    query_hash: str
    query: str
    results: List[Dict[str, Any]]
    timestamp: datetime
    hit_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    execution_time_ms: float = 0.0
    result_size: int = 0


@dataclass
class CacheStats:
    """Statistics for query cache performance"""
    total_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    total_execution_time_saved_ms: float = 0.0
    average_hit_ratio: float = 0.0


class SPARQLExecutorPort(ABC):
    """Port for executing SPARQL queries"""
    
    @abstractmethod
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SPARQL query and return results"""
        pass


class SPARQLQueryCache:
    """
    Intelligent cache for SPARQL queries with the following features:
    
    1. LRU eviction policy
    2. TTL-based expiration
    3. Query pattern analysis for cache decisions
    4. Automatic cache warming for common queries
    5. Statistics tracking for performance monitoring
    """
    
    def __init__(
        self,
        executor: SPARQLExecutorPort,
        max_cache_size: int = 1000,
        default_ttl_minutes: int = 30,
        enable_query_analysis: bool = True
    ):
        self.executor = executor
        self.max_cache_size = max_cache_size
        self.default_ttl = timedelta(minutes=default_ttl_minutes)
        self.enable_query_analysis = enable_query_analysis
        
        # Thread-safe cache using OrderedDict for LRU
        self.cache: OrderedDict[str, QueryCacheEntry] = OrderedDict()
        self.cache_lock = threading.RLock()
        
        # Statistics
        self.stats = CacheStats()
        
        # Query patterns for intelligent caching
        self.cacheable_patterns = {
            'SELECT': True,
            'CONSTRUCT': True,
            'ASK': True,
            'DESCRIBE': True
        }
        
        # Queries that should not be cached
        self.non_cacheable_keywords = {
            'NOW()', 'RAND()', 'UUID()', 'BNODE()'
        }
        
        # Common queries for warming
        self.common_queries = [
            "SELECT ?module ?usecase WHERE { ?module kth:definesUseCase ?usecase }",
            "SELECT ?component ?type WHERE { ?component rdf:type ?type }",
            "SELECT ?violation WHERE { ?violation rdf:type kth:RuleViolation }"
        ]
    
    def execute_query(self, query: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Execute SPARQL query with caching.
        
        Args:
            query: SPARQL query string
            force_refresh: If True, bypass cache and refresh entry
            
        Returns:
            Query results as list of dictionaries
        """
        query_hash = self._compute_query_hash(query)
        
        with self.cache_lock:
            self.stats.total_queries += 1
            
            # Check if query should be cached
            if not self._should_cache_query(query):
                return self._execute_and_time(query)
            
            # Check cache hit
            if not force_refresh and query_hash in self.cache:
                entry = self.cache[query_hash]
                
                # Check TTL
                if datetime.now() - entry.timestamp < self.default_ttl:
                    # Cache hit - move to end (LRU)
                    self.cache.move_to_end(query_hash)
                    entry.hit_count += 1
                    entry.last_accessed = datetime.now()
                    
                    self.stats.cache_hits += 1
                    self.stats.total_execution_time_saved_ms += entry.execution_time_ms
                    
                    return entry.results
                else:
                    # Expired entry
                    del self.cache[query_hash]
            
            # Cache miss - execute query
            self.stats.cache_misses += 1
            start_time = datetime.now()
            results = self.executor.execute_query(query)
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Store in cache
            entry = QueryCacheEntry(
                query_hash=query_hash,
                query=query,
                results=results,
                timestamp=datetime.now(),
                execution_time_ms=execution_time,
                result_size=len(results)
            )
            
            self._add_to_cache(query_hash, entry)
            
            return results
    
    def _execute_and_time(self, query: str) -> List[Dict[str, Any]]:
        """Execute query without caching and return results"""
        return self.executor.execute_query(query)
    
    def _compute_query_hash(self, query: str) -> str:
        """Compute hash for query to use as cache key"""
        # Normalize query (remove extra whitespace, convert to lowercase)
        normalized = ' '.join(query.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def _should_cache_query(self, query: str) -> bool:
        """Determine if query should be cached based on patterns"""
        if not self.enable_query_analysis:
            return True
        
        query_upper = query.upper()
        
        # Check for non-cacheable keywords
        for keyword in self.non_cacheable_keywords:
            if keyword in query_upper:
                return False
        
        # Check for cacheable query types
        for pattern in self.cacheable_patterns:
            if query_upper.strip().startswith(pattern):
                return self.cacheable_patterns[pattern]
        
        # Default to cacheable
        return True
    
    def _add_to_cache(self, query_hash: str, entry: QueryCacheEntry):
        """Add entry to cache with LRU eviction"""
        # Check if cache is full
        if len(self.cache) >= self.max_cache_size:
            # Evict least recently used
            oldest_hash, _ = self.cache.popitem(last=False)
            self.stats.evictions += 1
        
        self.cache[query_hash] = entry
    
    def warm_cache(self):
        """Pre-populate cache with common queries"""
        for query in self.common_queries:
            try:
                self.execute_query(query)
            except Exception as e:
                # Log error but continue warming other queries
                logger.warning(
                    "Failed to warm cache for query: %s, error: %s", query, e
                )
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching a pattern"""
        with self.cache_lock:
            to_remove = []
            for query_hash, entry in self.cache.items():
                if pattern.lower() in entry.query.lower():
                    to_remove.append(query_hash)
            
            for query_hash in to_remove:
                del self.cache[query_hash]
    
    def invalidate_all(self):
        """Clear all cache entries"""
        with self.cache_lock:
            self.cache.clear()
    
    def get_cache_stats(self) -> CacheStats:
        """Get current cache statistics"""
        with self.cache_lock:
            self.stats.average_hit_ratio = (
                self.stats.cache_hits / max(self.stats.total_queries, 1)
            )
            return self.stats
    
    def get_top_queries(self, limit: int = 10) -> List[Tuple[str, int, float]]:
        """Get most frequently accessed queries"""
        with self.cache_lock:
            sorted_entries = sorted(
                self.cache.values(),
                key=lambda x: x.hit_count,
                reverse=True
            )
            
            return [
                (entry.query[:100] + "..." if len(entry.query) > 100 else entry.query,
                 entry.hit_count,
                 entry.execution_time_ms)
                for entry in sorted_entries[:limit]
            ]
    
    def optimize_cache_size(self) -> int:
        """Analyze usage patterns and suggest optimal cache size"""
        with self.cache_lock:
            if not self.cache:
                return self.max_cache_size
            
            # Analyze hit patterns
            total_hits = sum(entry.hit_count for entry in self.cache.values())
            entries_with_hits = sum(1 for entry in self.cache.values() if entry.hit_count > 0)
            
            # Suggest size based on active entries
            suggested_size = max(entries_with_hits * 2, 100)
            return min(suggested_size, 2000)  # Cap at reasonable maximum


class PredefinedQueryCache:
    """Cache for commonly used predefined queries"""
    
    def __init__(self, base_cache: SPARQLQueryCache):
        self.base_cache = base_cache
        self.predefined_queries = {
            'module_dependencies': """
                SELECT ?source ?target WHERE {
                    ?source kth:dependsOnModule ?target
                }
            """,
            'dip_violations': """
                SELECT ?domain ?infra WHERE {
                    ?domain rdf:type kth:DomainComponent .
                    ?infra rdf:type kth:InfrastructureComponent .
                    ?domain kth:calls ?infra
                }
            """,
            'module_use_cases': """
                SELECT ?module ?usecase WHERE {
                    ?module kth:definesUseCase ?usecase
                }
            """,
            'port_implementations': """
                SELECT ?port ?adapter WHERE {
                    ?adapter kth:implementsPort ?port
                }
            """,
            'aggregate_entities': """
                SELECT ?aggregate ?entity WHERE {
                    ?entity kth:partOfAggregate ?aggregate
                }
            """
        }
    
    def execute_predefined(self, query_name: str, **params) -> List[Dict[str, Any]]:
        """Execute a predefined query with parameters"""
        if query_name not in self.predefined_queries:
            raise ValueError(f"Unknown predefined query: {query_name}")
        
        query = self.predefined_queries[query_name]
        
        # Simple parameter substitution
        for param, value in params.items():
            query = query.replace(f"${param}", str(value))
        
        return self.base_cache.execute_query(query)
    
    def list_predefined_queries(self) -> List[str]:
        """Get list of available predefined queries"""
        return list(self.predefined_queries.keys())