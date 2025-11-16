"""FastAPI dependency helpers relying on the application container."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Optional

from fastapi import Depends, Request

from adapters.opentelemetry_tracing_adapter import OpenTelemetryTracingAdapter
from adapters.llm.openai_audio_embedding_adapter import OpenAIAudioEmbeddingAdapter
from adapters.llm.openai_image_embedding_adapter import OpenAIImageEmbeddingAdapter
from adapters.retrievers.falkordb_graph_adapter import FalkorGraphAdapter
from application.ports.base import CachePort, TracingPort
from application.ports.multimodal import AudioEmbeddingPort, ImageEmbeddingPort
from domain.ecommerce_context_manager import EcommerceContextManager

from .settings import RestApiSettings
from .settings_factory import get_settings
from kernel.container import ServiceContainer, create_container

logger = logging.getLogger(__name__)


class MockTracingAdapter:
    """Simple tracing mock used in tests."""

    def start_span(
        self, *, name: str, tenant_id: str, **kwargs: Any
    ) -> Any:  # pragma: no cover - test helper
        from adapters.opentelemetry_tracing_adapter import NoOpSpan

        return NoOpSpan(name=name, tenant_id=tenant_id, attributes=kwargs)

    def record_metric(
        self, *, name: str, value: float, tenant_id: str, **tags: Any
    ) -> None:  # pragma: no cover - test helper
        return None


ApplicationContainer = ServiceContainer  # Backwards compatibility


def resolve(container: ServiceContainer, name: str) -> Any:
    """Resolve provider or attribute on a container to a concrete instance."""
    try:
        from dependency_injector import providers
    except Exception:  # pragma: no cover
        providers = None  # type: ignore
    attr = getattr(container, name, None)
    if providers is not None and isinstance(attr, providers.Provider):
        return attr()
    return attr


class ContainerProxy:
    """Proxy that resolves dependency-injector providers to instances on access."""

    def __init__(self, raw_container: ServiceContainer) -> None:
        self._raw_container = raw_container

    def __getattr__(self, name: str) -> Any:
        from dependency_injector import providers

        attr = getattr(self._raw_container, name)
        if isinstance(attr, providers.Provider):
            return attr()
        return attr


def create_default_container(
    settings: RestApiSettings, **overrides: Any
) -> ServiceContainer:
    """Backward compatible wrapper around :func:`create_container`."""

    return create_container(settings, **overrides)


def get_container(
    request: Request,
) -> ServiceContainer:
    """Return application container stored on the app or create a new one."""

    container: Optional[ServiceContainer] = getattr(
        request.app.state, "container", None
    )
    if container is None:
        settings = get_settings()
        container = create_container(settings)
        request.app.state.container = container
    return ContainerProxy(container)  # type: ignore[return-value]


def get_llm(container: ServiceContainer = Depends(get_container)) -> Any:
    """Retrieve configured LLM instance."""
    return container.llm


def get_llm_adapter(container: ServiceContainer = Depends(get_container)) -> Any:
    """Alias for ``get_llm`` for backward compatibility."""
    return container.llm


def get_tracer(container: ServiceContainer = Depends(get_container)) -> Any:
    """Return the configured tracing adapter."""
    return container.tracer


def get_message_bus(container: ServiceContainer = Depends(get_container)) -> Any:
    """Return the configured message bus adapter."""
    return container.message_bus


@lru_cache()
def get_context_manager() -> EcommerceContextManager:
    """Get configured :class:`EcommerceContextManager` instance."""

    settings = RestApiSettings()
    tracer: TracingPort = OpenTelemetryTracingAdapter(
        service_name=settings.service_name,
        otlp_endpoint=settings.tracing_endpoint,
        environment=settings.environment,
    )
    graph_port = FalkorGraphAdapter(
        connection_string=settings.falkordb_connection_string
    )
    from adapters.redis_cache_adapter import RedisCacheAdapter

    cache_port: CachePort = RedisCacheAdapter(url=settings.redis_url)
    image_embedding_port: ImageEmbeddingPort = OpenAIImageEmbeddingAdapter()
    audio_embedding_port: AudioEmbeddingPort = OpenAIAudioEmbeddingAdapter()

    return EcommerceContextManager(
        graph_port=graph_port,
        image_embedding_port=image_embedding_port,
        audio_embedding_port=audio_embedding_port,
        cache_port=cache_port,
        tracer=tracer,
    )


@lru_cache()
def get_event_adapter() -> Any:
    """Get configured :class:`KafkaEventAdapter` instance."""

    from adapters.event_ingestion.kafka_event_adapter import KafkaEventAdapter

    context_manager = get_context_manager()
    settings = RestApiSettings()
    tracer = OpenTelemetryTracingAdapter(
        service_name=settings.service_name,
        otlp_endpoint=settings.tracing_endpoint,
        environment=settings.environment,
    )

    return KafkaEventAdapter(
        context_manager=context_manager,
        tracer=tracer,
        bootstrap_servers=settings.kafka_bootstrap_servers,
    )
