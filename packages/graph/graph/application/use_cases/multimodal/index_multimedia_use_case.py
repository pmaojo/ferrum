from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path

from application.exceptions import ValidationError
from application.ports import (
    AudioEmbeddingPort,
    EmbeddingCachePort,
    ImageEmbeddingPort,
    VideoEmbeddingPort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO
from domain.entities import EmbeddingModel


@dataclass
class IndexMultimediaRequestDTO:
    tenant_id: str
    user_id: str
    kg_id: str
    content_path: str
    content_type: str


@dataclass
class IndexMultimediaResponseDTO(BaseResponseDTO):
    content_hash: str = ""
    embedding_model: str = ""


class IndexMultimediaUseCase(
    BaseUseCase[IndexMultimediaRequestDTO, IndexMultimediaResponseDTO]
):
    """Index multimedia files by generating embeddings and caching them."""

    def __init__(
        self,
        *,
        cache_port: EmbeddingCachePort,
        image_port: ImageEmbeddingPort,
        audio_port: AudioEmbeddingPort,
        video_port: VideoEmbeddingPort,
    ) -> None:
        super().__init__()
        self.cache_port = cache_port
        self.image_port = image_port
        self.audio_port = audio_port
        self.video_port = video_port

    async def _execute_internal(
        self, request: IndexMultimediaRequestDTO
    ) -> IndexMultimediaResponseDTO:
        start = time.time()
        path = Path(request.content_path)
        data = path.read_bytes()
        content_hash = hashlib.sha256(data).hexdigest()

        if request.content_type == "image":
            embedding = await self.image_port.generate_image_embedding(
                image_path=str(path), model=EmbeddingModel.CLIP_VIT_B32
            )
            model = EmbeddingModel.CLIP_VIT_B32
        elif request.content_type == "audio":
            embedding = await self.audio_port.generate_audio_embedding(
                audio_path=str(path), model="openai"
            )
            model = EmbeddingModel.OPENAI_AUDIO
        elif request.content_type == "video":
            embedding = await self.video_port.generate_video_embedding(
                video_path=str(path)
            )
            model = EmbeddingModel.VIDEO_EMBEDDING
        else:
            raise ValidationError(
                f"Unsupported content type: {request.content_type}",
                field="content_type",
            )

        await self.cache_port.cache_embedding(
            content_hash=content_hash,
            embedding_model=model,
            embedding_vector=embedding,
            tenant_id=request.tenant_id,
            content_type=request.content_type,
        )

        elapsed_ms = (time.time() - start) * 1000
        return IndexMultimediaResponseDTO(
            success=True,
            processing_time_ms=elapsed_ms,
            content_hash=content_hash,
            embedding_model=model.value,
        )

    def _validate_request_internal(self, request: IndexMultimediaRequestDTO) -> None:
        if not request.tenant_id:
            raise ValidationError("tenant_id is required", field="tenant_id")
        if not request.user_id:
            raise ValidationError("user_id is required", field="user_id")
        if not request.kg_id:
            raise ValidationError("kg_id is required", field="kg_id")
        if not request.content_path:
            raise ValidationError("content_path is required", field="content_path")
        if request.content_type not in {"image", "audio", "video"}:
            raise ValidationError(
                "content_type must be 'image', 'audio', or 'video'",
                field="content_type",
            )
        if not Path(request.content_path).is_file():
            raise ValidationError(
                "content_path must point to an existing file", field="content_path"
            )
