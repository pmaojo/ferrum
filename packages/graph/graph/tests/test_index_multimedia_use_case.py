import types
import sys
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
import enum

pkg = types.ModuleType("application.use_cases")
pkg.__path__ = []  # type: ignore[attr-defined]
sys.modules.setdefault("application.use_cases", pkg)
ports_stub = types.ModuleType("application.ports")
class EmbeddingCachePort:
    async def cache_embedding(self, *args, **kwargs): ...
class ImageEmbeddingPort:
    async def generate_image_embedding(self, *args, **kwargs): ...
class AudioEmbeddingPort:
    async def generate_audio_embedding(self, *args, **kwargs): ...
class VideoEmbeddingPort:
    async def generate_video_embedding(self, *args, **kwargs): ...
class CrossModalRetrievalPort:
    async def retrieve_similar(self, **kwargs): ...
class AuthorizationPort:
    async def check_permission(self, user_id: str, resource_id: str, permission: str) -> bool: ...
ports_stub.EmbeddingCachePort = EmbeddingCachePort
ports_stub.ImageEmbeddingPort = ImageEmbeddingPort
ports_stub.AudioEmbeddingPort = AudioEmbeddingPort
ports_stub.VideoEmbeddingPort = VideoEmbeddingPort
ports_stub.CrossModalRetrievalPort = CrossModalRetrievalPort
ports_stub.AuthorizationPort = AuthorizationPort
sys.modules.setdefault("application.ports", ports_stub)

entities_stub = types.ModuleType("domain.entities")
class EmbeddingModel(enum.Enum):
    CLIP_VIT_B32 = "clip"
    OPENAI_AUDIO = "openai-audio"
    VIDEO_EMBEDDING = "video"

entities_stub.EmbeddingModel = EmbeddingModel
sys.modules.setdefault("domain.entities", entities_stub)

root = Path(__file__).resolve().parents[1] / "application" / "use_cases"
base_spec = importlib.util.spec_from_file_location("application.use_cases.base_use_case", root / "base_use_case.py")
base_module = importlib.util.module_from_spec(base_spec)
base_spec.loader.exec_module(base_module)
sys.modules["application.use_cases.base_use_case"] = base_module

dto_spec = importlib.util.spec_from_file_location("application.use_cases.dto", root / "dto.py")
dto_module = importlib.util.module_from_spec(dto_spec)
dto_spec.loader.exec_module(dto_module)
sys.modules["application.use_cases.dto"] = dto_module

spec = importlib.util.spec_from_file_location(
    "index_module",
    root / "multimodal" / "index_multimedia_use_case.py",
)
index_module = importlib.util.module_from_spec(spec)
sys.modules["index_module"] = index_module
spec.loader.exec_module(index_module)

IndexMultimediaUseCase = index_module.IndexMultimediaUseCase
IndexMultimediaRequestDTO = index_module.IndexMultimediaRequestDTO

@pytest.fixture
def cache_port():
    return AsyncMock(spec=EmbeddingCachePort)

@pytest.fixture
def image_port():
    return AsyncMock(spec=ImageEmbeddingPort)

@pytest.fixture
def audio_port():
    return AsyncMock(spec=AudioEmbeddingPort)

@pytest.fixture
def video_port():
    return AsyncMock(spec=VideoEmbeddingPort)

@pytest.fixture
def use_case(cache_port, image_port, audio_port, video_port):
    return IndexMultimediaUseCase(
        cache_port=cache_port,
        image_port=image_port,
        audio_port=audio_port,
        video_port=video_port,
    )

@pytest.mark.asyncio
async def test_index_image(tmp_path, use_case, cache_port, image_port):
    path = tmp_path / "img.bin"
    path.write_bytes(b"img")
    image_port.generate_image_embedding.return_value = [1.0]

    req = IndexMultimediaRequestDTO(
        tenant_id="t",
        user_id="u",
        kg_id="kg",
        content_path=str(path),
        content_type="image",
    )
    res = await use_case.execute(req)

    assert res.success
    cache_port.cache_embedding.assert_called_once()
    image_port.generate_image_embedding.assert_called_once()

@pytest.mark.asyncio
async def test_index_audio(tmp_path, use_case, cache_port, audio_port):
    path = tmp_path / "a.wav"
    path.write_bytes(b"aud")
    audio_port.generate_audio_embedding.return_value = [0.2]

    req = IndexMultimediaRequestDTO(
        tenant_id="t",
        user_id="u",
        kg_id="kg",
        content_path=str(path),
        content_type="audio",
    )
    res = await use_case.execute(req)

    assert res.success
    cache_port.cache_embedding.assert_called_once()
    audio_port.generate_audio_embedding.assert_called_once()

@pytest.mark.asyncio
async def test_index_video(tmp_path, use_case, cache_port, video_port):
    path = tmp_path / "v.mp4"
    path.write_bytes(b"vid")
    video_port.generate_video_embedding.return_value = [0.3]

    req = IndexMultimediaRequestDTO(
        tenant_id="t",
        user_id="u",
        kg_id="kg",
        content_path=str(path),
        content_type="video",
    )
    res = await use_case.execute(req)

    assert res.success
    cache_port.cache_embedding.assert_called_once()
    video_port.generate_video_embedding.assert_called_once()
