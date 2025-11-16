# PermaGraph REST API

A production-ready REST API for GraphRAG Ontology services with comprehensive features for document ingestion, natural language querying, workflow orchestration, and token budget management.

## Features

- **Document Ingestion**: Process documents with GraphRAG extraction and ontological validation
- **Natural Language Querying**: Query knowledge graphs using natural language
- **Workflow Orchestration**: Register and execute multi-step workflows
- **Token Budget Management**: Track and manage LLM token usage and costs
- **Context Compression**: Optimize LLM context windows through triple relevance filtering
- **LLM Fallback Policy**: Resilient LLM operations with circuit breaker pattern
- **Observability**: Comprehensive metrics and monitoring
- **API Versioning**: Support for multiple API versions
- **Caching**: Performance optimization for frequently accessed data
- **Async Operations**: Background processing for long-running tasks
- **Rate Limiting**: Protection against API abuse
- **Detailed Error Responses**: Helpful error messages with suggestions
- **OpenAPI Documentation**: Interactive API documentation

## Getting Started

### Prerequisites

- Python 3.11+
- FastAPI
- Redis (optional, for production caching)
- Prometheus (optional, for metrics collection)

### Installation

1. Install dependencies:

```bash
pip install -e .
```

2. (Optional) Create a `.env` file or export environment variables. See
   [`.env.example`](.env.example) for a full list of options. At minimum, set
   a `PERMAGRAPH_API_KEY`:

```bash
export PERMAGRAPH_API_KEY=your-api-key
# optional LLM providers
export OPENAI_API_KEY=
export GEMINI_API_KEY=
export PERPLEXICA_API_KEY=
export GROQ_API_KEY=
export ANTHROPIC_API_KEY=
export DEEPSEEK_API_KEY=
```

3. Run the server:

```bash
uvicorn ui_adapters.rest_api.server:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

You can also run the API using Docker:

```bash
docker build -t permagraph-api .
docker run -p 8000:8000 -e PERMAGRAPH_API_KEY=your-api-key permagraph-api
```

### Configuration

The API loads its configuration from environment variables using
`RestApiSettings`. Below are the most common options with their default
values:

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | `permagraph-api` | Service name for tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | *(none)* | OTEL collector endpoint |
| `ENVIRONMENT` | `production` | Environment tag for tracing |
| `GEMINI_API_KEY` | *(none)* | API key for Gemini LLM |
| `PERPLEXICA_API_KEY` | *(none)* | API key for Perplexica LLM |
| `GROQ_API_KEY` | *(none)* | API key for Groq LLM |
| `ANTHROPIC_API_KEY` | *(none)* | API key for Anthropic LLM |
| `DEEPSEEK_API_KEY` | *(none)* | API key for DeepSeek LLM |
| `OPENAI_API_KEY` | *(none)* | API key for OpenAI LLM |
| `MEMGRAPH_CONNECTION_STRING` | *(none)* | Use Memgraph-based retriever when set |
| `GRAPHRAG_HOST` | `localhost` | Host de FalkorDB para GraphRAG SDK |
| `GRAPHRAG_PORT` | `6379` | Puerto de FalkorDB para GraphRAG SDK |
| `GRAPHRAG_USERNAME` | *(none)* | Usuario opcional de FalkorDB |
| `GRAPHRAG_PASSWORD` | *(none)* | Contraseña opcional de FalkorDB |
| `GRAPHRAG_API_KEY` | *(none)* | API key para GraphRAG SDK |
| `FALKORDB_CONNECTION_STRING` | `redis://localhost:6379` | FalkorDB connection |
| `PROMETHEUS_BASE_URL` | `http://localhost:9090` | Prometheus endpoint |
| `TOKEN_BUDGET_STORAGE_PATH` | *(none)* | File path for token usage data |
| `DEFAULT_MONTHLY_BUDGET_USD` | `100.0` | Default monthly token budget |
| `ALERT_THRESHOLD_PERCENT` | `80.0` | Alert threshold for budget |
| `ENABLE_DEGRADATION` | `true` | Enable fallback when budget exceeded |
| `DEFAULT_COMPRESSION_RATIO` | `0.7` | Default context compression ratio |
| `MIN_TRIPLES` | `10` | Minimum triples before compression |
| `USE_EMBEDDINGS` | `true` | Use embeddings for compression |
| `LLM_ERROR_THRESHOLD` | `5` | Errors before circuit breaker trips |
| `LLM_LATENCY_THRESHOLD_MS` | `800` | LLM latency threshold |
| `LLM_RESET_TIMEOUT_SECONDS` | `60` | Circuit breaker reset timeout |
| `CLIP_IMAGE_EMBEDDING` | `false` | Use CLIP for image embeddings |
| `GEMINI_IMAGE_EMBEDDING` | `false` | Use Gemini for image embeddings |
| `GEMINI_AUDIO_EMBEDDING` | `false` | Use Gemini for audio embeddings |
| `PERMAGRAPH_API_KEY` | *(none)* | API key required for authenticated calls |

## API Documentation

Interactive API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Authentication

The API supports two authentication methods:

1. Bearer token:
```
Authorization: Bearer your-api-key
```

2. API key header:
```
X-API-Key: your-api-key
```

Event ingestion endpoints under `/api/v1/ecommerce` require a valid `X-API-Key`
that maps to a tenant in the registry. The registry is configured through the
`TENANT_REGISTRY` environment variable which accepts a JSON object of
`{"api-key": "tenant-id"}` pairs. Requests with missing or unregistered keys are
rejected with `401 Unauthorized`.

## API Endpoints

### Health Checks

- `GET /api/health`: Basic health check
- `GET /api/v1/health/detailed`: Detailed health check with service status

-### Document Ingestion

- `POST /api/v1/ingest`: Synchronous document ingestion
- `POST /api/ingest` (deprecated): Thin wrapper around `/api/v1/ingest`
- `POST /api/v1/ingest/async`: Asynchronous document ingestion
- `POST /api/v1/repo-ingest`: Asynchronous repository ingestion from archive or URL
- `GET /api/v1/jobs/{job_id}`: Get status of asynchronous job

-### Natural Language Querying

- `POST /api/v1/query`: Natural language query with optional caching
- `POST /api/query` (deprecated): Delegates to `/api/v1/query`

### Workflow Orchestration

- `POST /api/workflows/register`: Register a multi-step workflow
- `POST /api/workflows/execute`: Execute a registered workflow

### Token Budget Management

- `POST /api/token-budget/track`: Track token usage
- `GET /api/token-budget/{tenant_id}`: Get token usage for a tenant
- `POST /api/token-budget/budget`: Set budget parameters for a tenant

### Context Compression

- `POST /api/v1/context/compress`: Compress context for LLM optimization

### LLM Fallback Policy

- `GET /api/v1/llm/circuit-status`: Get LLM circuit breaker status
- `POST /api/v1/llm/generate`: Generate text using LLM with fallback

### Monitoring

- `GET /metrics`: Prometheus metrics endpoint
- `GET /api/metrics`: Performance metrics for a tenant

### Cache Management

- `POST /api/v1/cache/clear`: Clear the API cache
- `GET /api/v1/cache/stats`: Get cache statistics

### System Information

- `GET /api/v1/system/info`: System information endpoint

## Rate Limiting

The API implements rate limiting to prevent abuse:

- Most endpoints: 100 requests per minute per IP
- Ingestion endpoints: 10 requests per minute per IP

## Error Handling

The API provides detailed error responses with helpful suggestions:

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid parameter format",
  "context": {
    "param": "tenant_id"
  },
  "suggestions": [
    "Check input parameter formats",
    "Ensure all required fields are provided",
    "Verify data types match expected formats"
  ],
  "timestamp": 1626912345.678,
  "path": "/api/v1/query"
}
```

## Async Operations

For long-running operations like document ingestion, the API provides asynchronous endpoints:

1. Start an async job:
```
POST /api/v1/ingest/async
```

2. Check job status:
```
GET /api/v1/jobs/{job_id}
```

## Caching

The API implements caching for frequently accessed data to improve performance. Cache statistics are available at:

```
GET /api/v1/cache/stats
```

## Monitoring

The API provides Prometheus metrics for monitoring:

- `api_requests_total`: Total API requests by method, endpoint, and status
- `api_request_duration_seconds`: API request duration by method and endpoint
- `ingestion_jobs_total`: Total ingestion jobs by status
- `queries_total`: Total queries processed by tenant

## Testing

Run the integration tests:

```bash
pytest tests/test_rest_api_integration.py -v
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.