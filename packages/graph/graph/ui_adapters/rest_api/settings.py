"""Application settings for the REST API."""

from typing import Dict, Optional
import json

from pydantic import Field, BaseModel, validator


class RestApiSettings(BaseModel):
    """Settings for the PermaGraph REST API.

    Values are loaded from environment variables and validated using
    :class:`pydantic.BaseSettings`. Type coercion and sensible defaults are
    provided for all fields.
    """

    # Basic service configuration
    service_name: str = Field("permagraph-api", env="SERVICE_NAME")
    tracing_endpoint: Optional[str] = Field(
        default=None, env="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    environment: str = Field("production", env="ENVIRONMENT")
    allowed_origins: list[str] = Field(default=[], env="ALLOWED_ORIGINS")

    # LLM API keys
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    perplexica_api_key: Optional[str] = Field(default=None, env="PERPLEXICA_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    deepseek_api_key: Optional[str] = Field(default=None, env="DEEPSEEK_API_KEY")
    tiny_mode: bool = Field(False, env="TINY_MODE")

    memgraph_connection_string: Optional[str] = Field(
        default=None, env="MEMGRAPH_CONNECTION_STRING"
    )

    # Windmill MCP configuration
    windmill_mcp_url: Optional[str] = Field(default=None, env="WINDMILL_MCP_URL")
    windmill_mcp_token: Optional[str] = Field(default=None, env="WINDMILL_MCP_TOKEN")

    # GraphRAG SDK configuration
    graphrag_host: str = Field("localhost", env="GRAPHRAG_HOST")
    graphrag_port: int = Field(6379, env="GRAPHRAG_PORT")
    graphrag_username: Optional[str] = Field(default=None, env="GRAPHRAG_USERNAME")
    graphrag_password: Optional[str] = Field(default=None, env="GRAPHRAG_PASSWORD")
    graphrag_api_key: Optional[str] = Field(default=None, env="GRAPHRAG_API_KEY")
    graphrag_config: Optional[str] = Field(default=None, env="GRAPHRAG_CONFIG")

    falkordb_connection_string: str = Field(
        "redis://localhost:6379", env="FALKORDB_CONNECTION_STRING"
    )  # Falkor / RedisGraph
    job_repository_url: str = Field(
        "redis://localhost:6379/1", env="JOB_REPOSITORY_URL"
    )
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    prometheus_base_url: str = Field("http://localhost:9090", env="PROMETHEUS_BASE_URL")
    kafka_bootstrap_servers: str = Field(
        "localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS"
    )

    token_budget_storage_path: Optional[str] = Field(
        default=None, env="TOKEN_BUDGET_STORAGE_PATH"
    )
    default_monthly_budget_usd: float = Field(100.0, env="DEFAULT_MONTHLY_BUDGET_USD")
    alert_threshold_percent: float = Field(80.0, env="ALERT_THRESHOLD_PERCENT")
    enable_degradation: bool = Field(True, env="ENABLE_DEGRADATION")
    tenant_budget_limits: Dict[str, float] = Field(
        default_factory=dict, env="TENANT_BUDGET_LIMITS"
    )

    default_compression_ratio: float = Field(0.7, env="DEFAULT_COMPRESSION_RATIO")
    min_triples: int = Field(10, env="MIN_TRIPLES")
    use_embeddings: bool = Field(True, env="USE_EMBEDDINGS")
    important_keywords: Optional[str] = Field(default=None, env="IMPORTANT_KEYWORDS")

    gremlin_endpoint: str = Field("ws://localhost:8182/gremlin", env="GREMLIN_ENDPOINT")

    llm_error_threshold: int = Field(5, env="LLM_ERROR_THRESHOLD")
    llm_latency_threshold_ms: int = Field(800, env="LLM_LATENCY_THRESHOLD_MS")
    llm_reset_timeout_seconds: int = Field(60, env="LLM_RESET_TIMEOUT_SECONDS")

    permagraph_api_key: Optional[str] = Field(default=None, env="PERMAGRAPH_API_KEY")

    # Embedding adapter configuration
    gemini_image_embedding: bool = Field(False, env="GEMINI_IMAGE_EMBEDDING")
    clip_image_embedding: bool = Field(False, env="CLIP_IMAGE_EMBEDDING")
    gemini_audio_embedding: bool = Field(False, env="GEMINI_AUDIO_EMBEDDING")

    # Message bus configuration
    windmill_bus_url: Optional[str] = Field(default=None, env="WINDMILL_BUS_URL")
    windmill_bus_api_key: Optional[str] = Field(
        default=None, env="WINDMILL_BUS_API_KEY"
    )

    # Transformers Server configuration
    transformers_server_url: Optional[str] = Field(
        default=None, env="TRANSFORMERS_SERVER_URL"
    )
    transformers_model_name: str = Field(
        "microsoft/DialoGPT-medium", env="TRANSFORMERS_MODEL_NAME"
    )
    transformers_embedding_model: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2", env="TRANSFORMERS_EMBEDDING_MODEL"
    )
    transformers_timeout: int = Field(120, env="TRANSFORMERS_TIMEOUT")
    transformers_max_retries: int = Field(3, env="TRANSFORMERS_MAX_RETRIES")

    # Ontology adapter selection
    ontology_adapter: str = Field(
        "plugins.ontology.kthulu_adapter:KthuluOntologyAdapter",
        env="ONTOLOGY_ADAPTER",
    )

    @validator("allowed_origins", pre=True)
    def _split_allowed_origins(cls, v: Optional[str]):  # pragma: no cover
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v or []

    @validator("tenant_budget_limits", pre=True)
    def _parse_tenant_budget_limits(cls, v):
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except json.JSONDecodeError as exc:  # pragma: no cover - invalid config
                raise ValueError("TENANT_BUDGET_LIMITS must be valid JSON") from exc
        return v

    class Config:
        arbitrary_types_allowed = True
