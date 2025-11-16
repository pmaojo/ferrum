# Enhanced Hybrid Intelligence System

This directory contains the implementation of the Enhanced Hybrid Intelligence System with fine-grained fallback mechanisms, as specified in the 2FA Payment Service Integration spec.

## Components Implemented

### 1. Health Monitor (`health-monitor.ts`)
- **Purpose**: Comprehensive health monitoring for LLM, PermaGraph, MCP, and streaming services
- **Features**:
  - Circuit breaker pattern with exponential backoff
  - Automatic failover logic
  - Real-time service status tracking
  - Configurable health check intervals and thresholds
  - Event-driven architecture for service state changes

**Key Services Monitored**:
- Gemini LLM API
- PermaGraph knowledge service
- Tuetano, Kthulu, and Ferrum MCP servers
- Streaming service for real-time updates

### 2. Fallback Service (`fallback-service.ts`)
- **Purpose**: Intelligent fallback orchestration based on service health
- **Features**:
  - Strategy-based fallback chains
  - Confidence scoring for fallback results
  - Operation history tracking
  - Automatic service selection based on health and reliability

**Fallback Strategies**:
- LLM Analysis: Gemini API → Rule-based analysis
- Knowledge Retrieval: PermaGraph → Local cache → Static templates
- Code Generation: Auto-detect MCP → Framework-specific MCP → Direct templates
- Real-time Updates: Streaming service → Batch updates → Polling updates

### 3. Rule-Based Analyzer (`rule-based-analyzer.ts`)
- **Purpose**: Deterministic semantic analysis as LLM fallback
- **Features**:
  - Intent classification using keyword matching and patterns
  - Domain detection through project structure analysis
  - Security assessment based on file patterns and dependencies
  - Framework detection with confidence scoring

**Analysis Capabilities**:
- Intent classification (2FA, payment integration, security audit, etc.)
- Framework detection (Tuetano, Kthulu, Ferrum, Laravel, Spring Boot, etc.)
- Architecture pattern recognition (hexagonal, clean, layered, microservices)
- Security vulnerability detection (hardcoded secrets, SQL injection, XSS, etc.)

### 4. Local Knowledge Cache (`local-knowledge-cache.ts`)
- **Purpose**: Local caching for PermaGraph data with TTL management
- **Features**:
  - Intelligent cache invalidation strategies
  - TTL-based expiration with LRU eviction
  - Tag-based cache organization
  - Disk persistence with compression support
  - Cache synchronization with PermaGraph

**Cache Features**:
- Knowledge pattern storage and retrieval
- Query result caching with fallback support
- Similar entry matching for partial cache hits
- Comprehensive cache statistics and monitoring

### 5. Enhanced Hybrid Intelligence (`hybrid-intelligence-enhanced.ts`)
- **Purpose**: Unified intelligent system integrating all components
- **Features**:
  - End-to-end request processing with fallback support
  - Real-time processing step streaming
  - Confidence calculation and service path tracking
  - Comprehensive error handling and recovery

**Processing Pipeline**:
1. Intent classification (rule-based)
2. Domain detection (project structure analysis)
3. Security assessment (pattern-based vulnerability detection)
4. Knowledge pattern retrieval (PermaGraph with cache fallback)
5. Recommendation generation (multi-source synthesis)

## Architecture Benefits

### Reliability
- **Circuit Breaker Pattern**: Prevents cascade failures when services are down
- **Exponential Backoff**: Reduces load on failing services while allowing recovery
- **Health Monitoring**: Proactive detection of service degradation
- **Graceful Degradation**: System continues operating with reduced functionality

### Performance
- **Local Caching**: Reduces latency and external service dependencies
- **Intelligent Fallbacks**: Faster deterministic analysis when LLM is unavailable
- **Parallel Processing**: Multiple services can be queried simultaneously
- **Resource Optimization**: Efficient memory and disk usage with cleanup

### Scalability
- **Service Isolation**: Each component can be scaled independently
- **Event-Driven Architecture**: Loose coupling between components
- **Configurable Thresholds**: Adaptable to different load patterns
- **Modular Design**: Easy to add new services and fallback strategies

## Configuration

Each service supports extensive configuration options:

```typescript
// Health Monitor Configuration
{
  interval: 30000,        // Health check interval (ms)
  timeout: 5000,          // Request timeout (ms)
  retryAttempts: 3,       // Number of retry attempts
  circuitBreakerThreshold: 5,  // Failures before circuit opens
  circuitBreakerTimeout: 60000, // Circuit breaker timeout (ms)
}

// Cache Configuration
{
  maxSize: 100 * 1024 * 1024,  // 100MB max cache size
  maxEntries: 10000,           // Maximum cache entries
  defaultTTL: 24 * 60 * 60 * 1000, // 24 hour TTL
  cleanupInterval: 60 * 60 * 1000,  // 1 hour cleanup interval
}
```

## Usage Example

```typescript
import { enhancedHybridIntelligence } from './hybrid-intelligence-enhanced';

const request = {
  text: 'add 2FA to my payment service',
  context: {
    projectPath: '/my/project',
    files: ['package.json', 'src/auth.js'],
    fileContents: new Map([...])
  },
  options: {
    enableStreaming: true,
    allowFallbacks: true,
    cacheResults: true
  }
};

const response = await enhancedHybridIntelligence.processRequest(request);
console.log('Intent:', response.intent.intent);
console.log('Confidence:', response.confidence);
console.log('Fallbacks used:', response.fallbacksUsed);
```

## Event System

The system emits various events for monitoring and integration:

- `system-ready`: System initialization complete
- `service-degraded`: Service became unhealthy
- `service-recovered`: Service recovered
- `processing-step`: Individual processing step completed
- `cache-hit`/`cache-miss`: Cache access events
- `operation-success`/`operation-failure`: Fallback operation results

## Testing

The implementation includes comprehensive test coverage:
- Unit tests for individual components
- Integration tests for service interactions
- Health monitoring validation
- Fallback mechanism verification
- Cache behavior testing

## Requirements Satisfied

This implementation satisfies the following requirements from the 2FA Payment Service Integration spec:

- **Requirement 3.1**: Fine-grained fallback mechanisms with service health monitoring
- **Requirement 3.2**: Rule-based semantic analysis as LLM fallback with confidence scoring
- **Requirement 3.3**: Local knowledge cache for PermaGraph fallback with TTL management
- **Requirement 3.4**: Automatic failover logic with circuit breaker pattern

The system provides enterprise-ready reliability, performance, and scalability for the hybrid intelligence workflow.