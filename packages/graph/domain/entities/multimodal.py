import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Set
from ..exceptions import ValidationError, VersioningException

class EmbeddingModel(Enum):
    """Available embedding models."""

    OPENAI_ADA_002 = "text-embedding-ada-002"
    OPENAI_3_SMALL = "text-embedding-3-small"
    OPENAI_3_LARGE = "text-embedding-3-large"
    CLIP_VIT_B32 = "clip-vit-b-32"
    CLIP_VIT_L14 = "clip-vit-l-14"
    OPENAI_AUDIO = "openai-audio"
    VIDEO_EMBEDDING = "video-embedding"
    SENTENCE_TRANSFORMERS = "sentence-transformers"
    CUSTOM = "custom"


@dataclass
class EmbeddingCache:
    """Cache entity for embeddings to improve performance."""

    id: str
    content_hash: str
    embedding_model: EmbeddingModel
    embedding_vector: List[float]
    tenant_id: str
    content_type: str  # text, image, audio, video
    metadata: Dict[str, Any]
    created_at: datetime
    last_accessed_at: datetime
    access_count: int = 0

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate the embedding cache entity."""
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(message="Cache ID must be a non-empty string", param="id")
        if not self.content_hash or not isinstance(self.content_hash, str):
            raise ValidationError(message="Content hash must be a non-empty string", param="content_hash")
        if not isinstance(self.embedding_model, EmbeddingModel):
            raise ValidationError(message="Embedding model must be a valid EmbeddingModel", param="embedding_model")
        if not isinstance(self.embedding_vector, list) or not self.embedding_vector:
            raise ValidationError(message="Embedding vector must be a non-empty list", param="embedding_vector")
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(message="Tenant ID must be a non-empty string", param="tenant_id")
        if self.content_type not in ["text", "image", "audio", "video"]:
            raise ValidationError(
                message="Content type must be 'text', 'image', 'audio', or 'video'",
                param="content_type",
            )

    @classmethod
    def create(
        cls,
        content_hash: str,
        embedding_model: EmbeddingModel,
        embedding_vector: List[float],
        tenant_id: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "EmbeddingCache":
        """Create a new embedding cache entry."""
        now = datetime.utcnow()
        cache_id = str(uuid.uuid4())

        return cls(
            id=cache_id,
            content_hash=content_hash,
            embedding_model=embedding_model,
            embedding_vector=embedding_vector,
            tenant_id=tenant_id,
            content_type=content_type,
            metadata=metadata or {},
            created_at=now,
            last_accessed_at=now,
            access_count=1,
        )

    def record_access(self) -> None:
        """Record an access to this cache entry."""
        self.access_count += 1
        self.last_accessed_at = datetime.utcnow()


class MultimodalContentType(Enum):
    """Types of multimodal content."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    CODE = "code"


@dataclass
class MultimodalEntity:
    """Entity representing multimodal content in the knowledge graph."""

    id: str
    tenant_id: str
    kg_id: str
    content_type: MultimodalContentType
    content_path: str
    embeddings: Dict[str, List[float]]  # model_name -> embedding_vector
    metadata: Dict[str, Any]
    extracted_text: Optional[str]
    relationships: List[str]  # Entity IDs this is related to
    created_at: datetime
    updated_at: datetime
    processing_status: str  # pending, processing, completed, failed

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate the multimodal entity."""
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(message="Entity ID must be a non-empty string", param="id")
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(message="Tenant ID must be a non-empty string", param="tenant_id")
        if not self.kg_id or not isinstance(self.kg_id, str):
            raise ValidationError(message="Knowledge graph ID must be a non-empty string", param="kg_id")
        if not isinstance(self.content_type, MultimodalContentType):
            raise ValidationError(message="Content type must be a valid MultimodalContentType", param="content_type")
        if not self.content_path or not isinstance(self.content_path, str):
            raise ValidationError(message="Content path must be a non-empty string", param="content_path")
        if not isinstance(self.embeddings, dict):
            raise ValidationError(message="Embeddings must be a dictionary", param="embeddings")
        if not isinstance(self.metadata, dict):
            raise ValidationError(message="Metadata must be a dictionary", param="metadata")
        if not isinstance(self.relationships, list):
            raise ValidationError(message="Relationships must be a list", param="relationships")

    @classmethod
    def create(
        cls,
        tenant_id: str,
        kg_id: str,
        content_type: MultimodalContentType,
        content_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "MultimodalEntity":
        """Create a new multimodal entity."""
        now = datetime.utcnow()
        entity_id = str(uuid.uuid4())

        return cls(
            id=entity_id,
            tenant_id=tenant_id,
            kg_id=kg_id,
            content_type=content_type,
            content_path=content_path,
            embeddings={},
            metadata=metadata or {},
            extracted_text=None,
            relationships=[],
            created_at=now,
            updated_at=now,
            processing_status="pending",
        )

