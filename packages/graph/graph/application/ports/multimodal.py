"""Port interfaces for multimodal content processing."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from domain.entities import EmbeddingModel, MultimodalContentType, MultimodalEntity


class MultimodalProcessingPort(ABC):
    """Port for processing multimodal content."""

    @abstractmethod
    async def process_content(
        self,
        content_path: str,
        content_type: MultimodalContentType,
        tenant_id: str,
        kg_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MultimodalEntity:
        """Process multimodal content and create entity."""

    @abstractmethod
    async def extract_text_from_content(
        self,
        content_path: str,
        content_type: MultimodalContentType,
    ) -> Optional[str]:
        """Extract text from multimodal content."""

    @abstractmethod
    async def generate_cross_modal_relationships(
        self,
        entity_id: str,
        tenant_id: str,
        kg_id: str,
    ) -> List[str]:
        """Generate relationships with other entities."""


class EmbeddingCachePort(ABC):
    """Port for embedding cache operations."""

    @abstractmethod
    async def get_cached_embedding(
        self,
        content_hash: str,
        embedding_model: EmbeddingModel,
        tenant_id: str,
    ) -> Optional[List[float]]:
        """Get cached embedding if it exists."""

    @abstractmethod
    async def cache_embedding(
        self,
        content_hash: str,
        embedding_model: EmbeddingModel,
        embedding_vector: List[float],
        tenant_id: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Cache an embedding for future use."""

    @abstractmethod
    async def invalidate_cache(
        self,
        content_hash: str,
        tenant_id: str,
    ) -> None:
        """Invalidate cached embeddings for content."""


class ImageEmbeddingPort(ABC):
    """Port for image embedding generation."""

    @abstractmethod
    async def generate_image_embedding(
        self,
        image_path: str,
        model: EmbeddingModel = EmbeddingModel.CLIP_VIT_B32,
    ) -> List[float]:
        """Generate embedding for an image."""

    @abstractmethod
    async def generate_image_features(
        self,
        image_path: str,
    ) -> Dict[str, Any]:
        """Generate visual features from image."""

    @abstractmethod
    async def compare_images(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """Calculate similarity between image embeddings."""


class AudioEmbeddingPort(ABC):
    """Port for audio embedding generation."""

    @abstractmethod
    async def generate_audio_embedding(
        self,
        audio_path: str,
        model: str = "whisper-large-v2",
    ) -> List[float]:
        """Generate embedding for audio content."""

    @abstractmethod
    async def transcribe_audio(
        self,
        audio_path: str,
    ) -> str:
        """Transcribe audio to text."""

    @abstractmethod
    async def extract_audio_features(
        self,
        audio_path: str,
    ) -> Dict[str, Any]:
        """Extract acoustic features from audio."""


class VideoEmbeddingPort(ABC):
    """Port for video embedding generation."""

    @abstractmethod
    async def generate_video_embedding(
        self,
        video_path: str,
    ) -> List[float]:
        """Generate embedding for video content."""

    @abstractmethod
    async def extract_video_frames(
        self,
        video_path: str,
        frame_count: int = 10,
    ) -> List[str]:
        """Extract key frames from video."""

    @abstractmethod
    async def extract_video_features(
        self,
        video_path: str,
    ) -> Dict[str, Any]:
        """Extract visual and temporal features from video."""


class CrossModalRetrievalPort(ABC):
    """Port for cross-modal similarity search leveraging cached embeddings."""

    @abstractmethod
    async def retrieve_similar(
        self,
        *,
        tenant_id: str,
        kg_id: str,
        text_query: Optional[str] = None,
        image_path: Optional[str] = None,
        audio_path: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Return items similar to the provided inputs across modalities."""


class TextResponseGeneratorPort(ABC):
    """Port for generating textual summaries from multimodal inputs."""

    @abstractmethod
    async def compose(self, texts: List[str]) -> str:
        """Compose a textual answer from input text snippets."""


class ImageSelectionPort(ABC):
    """Port for selecting relevant images for a response."""

    @abstractmethod
    async def select(self, image_paths: List[str]) -> List[str]:
        """Return a subset of image paths relevant to the answer."""


class AudioSynthesisPort(ABC):
    """Port for synthesizing audio from text."""

    @abstractmethod
    async def synthesize(self, text: str) -> str:
        """Generate an audio file path from the given text."""
