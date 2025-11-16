"""Infrastructure adapters - External system integrations."""

try:
    from .repositories.prometheus_metrics_repository import PrometheusMetricsRepository
except Exception:  # pragma: no cover - optional dependency
    PrometheusMetricsRepository = None  # type: ignore

from .inmemory_message_bus_adapter import InMemoryMessageBusAdapter
from .inmemory_tracing_adapter import InMemoryTracingAdapter
from .redis_cache_adapter import RedisCacheAdapter
from .contract import SimpleContractAdapter
from .numpy_vector_math import NumpyVectorMathAdapter
from .repositories.inmemory_webhook_repository import InMemoryWebhookRepository
from .hydra.persona_generator_adapter import PersonaGeneratorAdapter
from .hydra.scope_generator_adapter import ScopeGeneratorAdapter

try:  # Optional dependencies
    from .llm.openai_image_embedding_adapter import OpenAIImageEmbeddingAdapter
except Exception:  # pragma: no cover - optional dependency
    OpenAIImageEmbeddingAdapter = None  # type: ignore

try:
    from .llm.openai_audio_embedding_adapter import OpenAIAudioEmbeddingAdapter
except Exception:  # pragma: no cover - optional dependency
    OpenAIAudioEmbeddingAdapter = None  # type: ignore

try:  # Optional dependency
    from .whisper_audio_embedding_adapter import WhisperAudioEmbeddingAdapter
except Exception:  # pragma: no cover - optional dependency
    WhisperAudioEmbeddingAdapter = None  # type: ignore

try:
    from .windmill_mcp_adapter import WindmillMCPAdapter
except Exception:  # pragma: no cover - optional dependency
    WindmillMCPAdapter = None  # type: ignore

try:
    from .windmill_message_bus_adapter import WindmillMessageBusAdapter
except Exception:  # pragma: no cover - optional dependency
    WindmillMessageBusAdapter = None  # type: ignore

__all__ = [
    "PrometheusMetricsRepository",
    "InMemoryMessageBusAdapter",
    "InMemoryWebhookRepository",
    "SimpleContractAdapter",
    "NumpyVectorMathAdapter",
    "InMemoryTracingAdapter",
    "RedisCacheAdapter",
    "PersonaGeneratorAdapter",
    "ScopeGeneratorAdapter",
    "OpenAIImageEmbeddingAdapter",
    "OpenAIAudioEmbeddingAdapter",
    "WhisperAudioEmbeddingAdapter",
    "WindmillMCPAdapter",
    "WindmillMessageBusAdapter",
]
