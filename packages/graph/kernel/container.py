"""Dependency injection container for core services."""
from __future__ import annotations

import logging
import importlib
from typing import Any, Optional

from dependency_injector import containers, providers

from adapters.logging_alert_adapter import LoggingAlertAdapter
from domain.context_compression_service import ContextCompressionService
from domain.llm_fallback_policy import LLMFallbackPolicy
from domain.graph_visualizer import GraphVisualizer
from domain.services import (
    IngestionService,
    ObservabilityService,
    QueryService,
    WorkflowOrchestrator,
    CodeIngestionService,
    ConfigTemplateService,
)
from domain.query_translation import QueryTranslationService
from domain.token_budget_service import TokenBudgetService
from domain.ontology_version_service import OntologyVersionService
from adapters.retrievers.falkordb_graph_adapter import FalkorGraphAdapter
from adapters.louvain_clustering_adapter import LouvainClusteringAdapter
from adapters.python_ast_analyzer_adapter import PythonASTAnalyzerAdapter
from adapters.inmemory_configuration_adapter import InMemoryConfigurationAdapter
from adapters.redis_cache_adapter import RedisCacheAdapter
from ui_adapters.rest_api.settings import RestApiSettings
from application.ports.ontology_adapter import OntologyAdapter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Adapter factory helpers
# ---------------------------------------------------------------------------

def create_tracer(settings: RestApiSettings) -> Any:
    from adapters.opentelemetry_tracing_adapter import OpenTelemetryTracingAdapter

    return OpenTelemetryTracingAdapter(
        service_name=settings.service_name,
        otlp_endpoint=settings.tracing_endpoint,
        environment=settings.environment,
    )


def create_message_bus(tracer: Any, settings: RestApiSettings) -> Optional[Any]:
    if settings.windmill_mcp_url:
        from adapters.windmill_mcp_adapter import WindmillMCPAdapter

        logger.info("Initializing Windmill MCP adapter: %s", settings.windmill_mcp_url)
        return WindmillMCPAdapter(
            base_url=settings.windmill_mcp_url,
            token=settings.windmill_mcp_token,
            tracer=tracer,
        )
    from adapters.inmemory_message_bus_adapter import InMemoryMessageBusAdapter

    return InMemoryMessageBusAdapter(tracer=tracer)


def create_llm(tracer: Any, settings: RestApiSettings) -> Any:
    from adapters.llm.gemini_llm_adapter import GeminiLLMAdapter
    from adapters.llm.openai_llm_adapter import OpenAILLMAdapter
    from adapters.llm.perplexica_llm_adapter import PerplexicaLLMAdapter
    from adapters.llm.micro_llm_adapter import MicroLLMAdapter, MicroLLMConfig
    from adapters.llm.transformers_server_adapter import (
        TransformersServerAdapter,
        TransformersServerConfig,
    )

    if getattr(settings, "transformers_server_url", None):
        logger.info(
            "Initializing Transformers Server LLM at: %s",
            settings.transformers_server_url,
        )
        server_config = TransformersServerConfig(
            base_url=settings.transformers_server_url,
            model_name=getattr(settings, "transformers_model_name", "microsoft/DialoGPT-medium"),
            timeout_seconds=getattr(settings, "transformers_timeout", 120),
            max_retries=getattr(settings, "transformers_max_retries", 3),
        )
        return TransformersServerAdapter(
            server_config=server_config,
            embedding_model=getattr(
                settings,
                "transformers_embedding_model",
                "sentence-transformers/all-MiniLM-L6-v2",
            ),
            tracer=tracer,
        )

    if getattr(settings, "tiny_mode", False):
        logger.info("Initializing Micro LLM adapter for tiny mode")
        return MicroLLMAdapter(config=MicroLLMConfig(), tracer=tracer)

    if settings.perplexica_api_key:
        logger.info(
            "Initializing Perplexica LLM with API key: %s...",
            settings.perplexica_api_key[:10],
        )
        return PerplexicaLLMAdapter(api_key=settings.perplexica_api_key, tracer=tracer)
    if settings.gemini_api_key:
        logger.info("Initializing Gemini LLM with API key: %s...", settings.gemini_api_key[:10])
        return GeminiLLMAdapter(api_key=settings.gemini_api_key, tracer=tracer)
    if settings.openai_api_key:
        return OpenAILLMAdapter(api_key=settings.openai_api_key, tracer=tracer)
    raise RuntimeError(
        "TRANSFORMERS_SERVER_URL, GEMINI_API_KEY or OPENAI_API_KEY must be set"
    )


def create_graph_retriever(tracer: Any, llm: Any, settings: RestApiSettings) -> Any:
    from adapters.retrievers.memgraph_graphrag_adapter import MemgraphGraphRAGAdapter
    from adapters.retrievers.graphrag_cli_adapter import GraphRAGCLIAdapter, GraphragCLIClient
    from adapters.retrievers.fallback_graph_adapter import FallbackGraphAdapter
    from domain.exceptions import GraphRAGException

    memgraph_conn = settings.memgraph_connection_string
    if memgraph_conn:
        return MemgraphGraphRAGAdapter(memgraph_connection_string=memgraph_conn)

    litellm_fallbacks: list[str] = []
    if settings.gemini_api_key:
        litellm_fallbacks.append("gemini/gemini-2.0-flash")
    if settings.openai_api_key:
        litellm_fallbacks.append("openai/gpt-4o-mini")
    if settings.anthropic_api_key:
        litellm_fallbacks.append("anthropic/claude-3-haiku-20240307")
    if settings.groq_api_key:
        litellm_fallbacks.append("groq/llama-3.1-8b-instant")

    try:
        from adapters.retrievers.graphrag_sdk_adapter import GraphRAGSDKAdapter

        return GraphRAGSDKAdapter(
            host=settings.graphrag_host,
            port=settings.graphrag_port,
            username=settings.graphrag_username,
            password=settings.graphrag_password,
            api_key=settings.graphrag_api_key or settings.gemini_api_key,
            tracer=tracer,
            use_litellm=True,
            litellm_fallbacks=litellm_fallbacks if litellm_fallbacks else None,
        )
    except (ImportError, GraphRAGException) as exc:
        logger.warning("GraphRAG SDK unavailable: %s", exc)

    try:
        root_dir = settings.graphrag_config or "rag"
        client = GraphragCLIClient(root_dir=root_dir)
        return GraphRAGCLIAdapter(client)
    except Exception as exc:
        logger.error("Failed to initialize GraphRAG CLI adapter: %s", exc)

    return FallbackGraphAdapter(connection_string=settings.falkordb_connection_string)


def create_translator() -> Any:
    from adapters.simple_query_translator_adapter import SimpleQueryTranslatorAdapter

    return SimpleQueryTranslatorAdapter()


def create_sparql_translator() -> Any:
    from adapters.simple_sparql_translator_adapter import SimpleSparqlTranslatorAdapter

    return SimpleSparqlTranslatorAdapter()


def create_shacl_translator() -> Any:
    from adapters.simple_shacl_translator_adapter import SimpleShaclTranslatorAdapter

    return SimpleShaclTranslatorAdapter()


def create_validator(settings: RestApiSettings) -> Any:
    from adapters.hybrid_reasoner_adapter import HybridReasonerAdapter
    from adapters.repositories.falkordb_ontology_repository import FalkorDBOntologyRepository
    from adapters.repositories.inmemory_graph_metadata_repository import InMemoryGraphMetadataRepository

    connection = settings.falkordb_connection_string or "redis://localhost:6379"
    try:
        repo = FalkorDBOntologyRepository(connection)
        return HybridReasonerAdapter(
            ontology_repository=repo,
            falkordb_connection_string=connection,
        )
    except Exception:
        return create_translator()


def create_metrics_repository(settings: RestApiSettings) -> Any:
    from adapters.repositories.prometheus_metrics_repository import PrometheusMetricsRepository

    return PrometheusMetricsRepository(base_url=settings.prometheus_base_url)


def create_vector_math() -> Any:
    from adapters.numpy_vector_math import NumpyVectorMathAdapter

    return NumpyVectorMathAdapter()


def create_ontology_adapter(settings: RestApiSettings) -> OntologyAdapter:
    """Load an ontology adapter implementation based on configuration."""
    module_path, class_name = settings.ontology_adapter.split(":")
    module = importlib.import_module(module_path)
    adapter_cls = getattr(module, class_name)
    return adapter_cls()


def create_image_embedding(settings: RestApiSettings) -> Any:
    if settings.gemini_image_embedding:
        try:
            from adapters.llm.gemini_image_embedding_adapter import GeminiImageEmbeddingAdapter

            return GeminiImageEmbeddingAdapter(api_key=settings.gemini_api_key)
        except Exception as exc:
            logger.error("Failed to load GeminiImageEmbeddingAdapter: %s", exc)
    if settings.clip_image_embedding:
        from adapters.llm.clip_image_embedding_adapter import CLIPImageEmbeddingAdapter

        return CLIPImageEmbeddingAdapter()
    from adapters.llm.openai_image_embedding_adapter import OpenAIImageEmbeddingAdapter

    return OpenAIImageEmbeddingAdapter()


def create_audio_embedding(settings: RestApiSettings) -> Any:
    if settings.gemini_audio_embedding:
        try:
            from adapters.llm.gemini_audio_embedding_adapter import GeminiAudioEmbeddingAdapter

            return GeminiAudioEmbeddingAdapter(api_key=settings.gemini_api_key)
        except Exception as exc:
            logger.error("Failed to load GeminiAudioEmbeddingAdapter: %s", exc)
    from adapters.llm.openai_audio_embedding_adapter import OpenAIAudioEmbeddingAdapter

    return OpenAIAudioEmbeddingAdapter()


def create_graph_traversal(settings: RestApiSettings) -> Optional[Any]:
    try:
        from adapters.retrievers.tinkerpop_adapter import TinkerPopAdapter

        return TinkerPopAdapter(endpoint=settings.gremlin_endpoint)
    except Exception as exc:
        logger.warning("Failed to connect to Gremlin endpoint: %s", exc)
        return None


def create_job_repository(settings: RestApiSettings) -> Any:
    """Return job repository based on ``JOB_REPOSITORY_URL``."""
    from infrastructure.storage import (
        RedisJobRepository,
        SQLAlchemyIngestionRepository,
        Base as IngestionBase,
    )

    if settings.job_repository_url.startswith("redis://"):
        return RedisJobRepository(url=settings.job_repository_url)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.job_repository_url)
    IngestionBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return SQLAlchemyIngestionRepository(Session())


def create_cache_port(settings: RestApiSettings) -> Any:
    """Return Redis-backed cache adapter."""

    return RedisCacheAdapter(url=settings.redis_url)


def create_code_analyzer() -> Any:
    return PythonASTAnalyzerAdapter()


def create_configuration_port(settings: RestApiSettings) -> Any:
    return InMemoryConfigurationAdapter()


def create_ontology_version_repository(settings: RestApiSettings) -> Any:
    from adapters.repositories.falkordb_ontology_repository import FalkorDBOntologyRepository

    if isinstance(settings, dict):  # type: ignore
        connection_string = settings.get("falkordb_connection_string") or "redis://localhost:6379"
    else:
        connection_string = getattr(settings, "falkordb_connection_string", None) or "redis://localhost:6379"
    repo = FalkorDBOntologyRepository(connection_string)
    return repo


class ServiceContainer(containers.DeclarativeContainer):
    """Container building adapters and domain services."""

    config = providers.Configuration()

    tracer = providers.Singleton(create_tracer, settings=config)
    message_bus = providers.Singleton(create_message_bus, tracer=tracer, settings=config)
    llm = providers.Singleton(create_llm, tracer=tracer, settings=config)
    graph_retriever = providers.Singleton(
        create_graph_retriever, tracer=tracer, llm=llm, settings=config
    )
    translator = providers.Singleton(create_translator)
    sparql_translator = providers.Singleton(create_sparql_translator)
    shacl_translator = providers.Singleton(create_shacl_translator)
    translation_service = providers.Singleton(QueryTranslationService, translator)
    sparql_translation_service = providers.Singleton(
        QueryTranslationService, sparql_translator
    )
    shacl_translation_service = providers.Singleton(
        QueryTranslationService, shacl_translator
    )
    validator = providers.Singleton(create_validator, settings=config)
    metrics_repo = providers.Singleton(create_metrics_repository, settings=config)
    vector_math = providers.Singleton(create_vector_math)
    job_repository = providers.Singleton(create_job_repository, settings=config)
    cache_port = providers.Singleton(create_cache_port, settings=config)
    ontology_repo = providers.Singleton(create_ontology_version_repository, settings=config)
    graph_traversal = providers.Singleton(create_graph_traversal, settings=config)
    image_embedding = providers.Singleton(create_image_embedding, settings=config)
    audio_embedding = providers.Singleton(create_audio_embedding, settings=config)

    configuration_port = providers.Singleton(create_configuration_port, settings=config)
    code_analyzer = providers.Singleton(create_code_analyzer)

    ingestion_service = providers.Singleton(
        IngestionService,
        retriever=graph_retriever,
        validator=validator,
        tracer=tracer,
        logger=logger,
    )
    code_ingestion_service = providers.Singleton(
        CodeIngestionService,
        analyzer=code_analyzer,
        ingestion_service=ingestion_service,
    )
    config_template_service = providers.Singleton(
        ConfigTemplateService,
        llm=llm,
        configuration_port=configuration_port,
    )
    query_service = providers.Singleton(
        QueryService,
        translator=translator,
        retriever=graph_retriever,
        tracer=tracer,
        translation_service=translation_service,
        sparql_translation_service=sparql_translation_service,
        shacl_translation_service=shacl_translation_service,
    )
    workflow_orchestrator = providers.Singleton(
        WorkflowOrchestrator,
        retriever=graph_retriever,
        translator=translator,
        message_bus=message_bus,
        tracer=tracer,
    )
    token_budget_service = providers.Singleton(
        TokenBudgetService,
        tracer=tracer,
        alerting_service=providers.Factory(LoggingAlertAdapter),
        storage_path=config.token_budget_storage_path,
        default_monthly_budget_usd=config.default_monthly_budget_usd,
        alert_threshold_percent=config.alert_threshold_percent,
        enable_degradation=config.enable_degradation,
        tenant_budget_limits=config.tenant_budget_limits,
    )
    observability_service = providers.Singleton(
        ObservabilityService,
        tracer=tracer,
        metrics_repository=metrics_repo,
        message_bus=message_bus,
    )
    context_compression_service = providers.Singleton(
        ContextCompressionService,
        llm=llm,
        tracer=tracer,
        vector_math=vector_math,
        default_compression_ratio=config.default_compression_ratio,
        min_triples=config.min_triples,
        use_embeddings=config.use_embeddings,
        important_keywords=providers.Callable(lambda s: set(s.split(',')) if s else None, config.important_keywords),
        logger=logger,
    )
    llm_fallback_policy = providers.Singleton(
        LLMFallbackPolicy,
        primary_llm=llm,
        fallback_llm=llm,
        tracer=tracer,
        error_threshold=config.llm_error_threshold,
        latency_threshold_ms=config.llm_latency_threshold_ms,
        reset_timeout_seconds=config.llm_reset_timeout_seconds,
    )
    ontology_version_service = providers.Singleton(
        OntologyVersionService, ontology_repo
    )
    ontology_adapter = providers.Singleton(create_ontology_adapter, settings=config)
    falkor_adapter = providers.Singleton(
        FalkorGraphAdapter, connection_string=config.falkordb_connection_string
    )
    clustering_adapter = providers.Singleton(
        LouvainClusteringAdapter, falkor_adapter=falkor_adapter
    )
    graph_visualizer = providers.Singleton(
        GraphVisualizer, clustering_port=clustering_adapter
    )

    cross_modal_port = providers.Object(None)

    def __getattribute__(self, item: str) -> Any:  # pragma: no cover - thin proxy
        attr = super().__getattribute__(item)
        if isinstance(attr, providers.Provider):
            return attr()
        return attr


def create_container(settings: RestApiSettings, **overrides: Any) -> ServiceContainer:
    """Return configured :class:`ServiceContainer` with optional overrides."""

    container = ServiceContainer()
    # Pydantic v1 BaseSettings expone .dict(); aceptar dict directo también
    if isinstance(settings, dict):  # type: ignore
        cfg_dict = settings
    else:
        cfg_dict = getattr(settings, 'dict', lambda: settings.__dict__)()
    container.config.from_dict(cfg_dict)

    for name, value in overrides.items():
        if value is not None and hasattr(container, name):
            getattr(container, name).override(providers.Object(value))

    return container
