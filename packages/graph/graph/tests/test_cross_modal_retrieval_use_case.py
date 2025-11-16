import pytest
from unittest.mock import AsyncMock, Mock

import importlib.util
from pathlib import Path
import types
import sys

sys.modules.setdefault("application.use_cases", types.ModuleType("application.use_cases"))
ports_stub = types.ModuleType("application.ports")
class CrossModalRetrievalPort:
    async def retrieve_similar(self, **kwargs): ...
class EmbeddingCachePort: ...
class AuthorizationPort:
    async def check_permission(self, user_id: str, resource_id: str, permission: str) -> bool: ...
ports_stub.CrossModalRetrievalPort = CrossModalRetrievalPort
ports_stub.EmbeddingCachePort = EmbeddingCachePort
ports_stub.AuthorizationPort = AuthorizationPort
sys.modules.setdefault("application.ports", ports_stub)

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
    "cross_modal_use_case",
    Path(__file__).resolve().parents[1]
    / "application"
    / "use_cases"
    / "multimodal"
    / "cross_modal_retrieval_use_case.py",
)
cross_modal_module = importlib.util.module_from_spec(spec)
sys.modules["cross_modal_use_case"] = cross_modal_module
spec.loader.exec_module(cross_modal_module)

CrossModalRetrievalUseCase = cross_modal_module.CrossModalRetrievalUseCase
CrossModalRetrievalRequestDTO = cross_modal_module.CrossModalRetrievalRequestDTO
from application.exceptions import AuthorizationError, ValidationError


@pytest.fixture
def retrieval_port():
    return AsyncMock(spec=CrossModalRetrievalPort)


@pytest.fixture
def cache_port():
    return AsyncMock(spec=EmbeddingCachePort)


@pytest.fixture
def auth_port():
    return AsyncMock(spec=AuthorizationPort)


@pytest.fixture
def use_case(retrieval_port, cache_port, auth_port):
    return CrossModalRetrievalUseCase(
        retrieval_port=retrieval_port,
        embedding_cache_port=cache_port,
        authorization_port=auth_port,
    )


@pytest.fixture
def valid_request():
    return CrossModalRetrievalRequestDTO(
        tenant_id="t1",
        user_id="u1",
        kg_id="kg1",
        text_query="hello",
        image_path="/tmp/img.png",
        limit=5,
        threshold=0.5,
    )


@pytest.mark.asyncio
async def test_execute_success(use_case, retrieval_port, auth_port, valid_request):
    auth_port.check_permission.return_value = True
    retrieval_port.retrieve_similar.return_value = [
        {"entity_id": "e1", "content_type": "image", "content_path": "img1.png", "score": 0.9},
        {"entity_id": "e2", "content_type": "text", "content_path": "doc.txt", "score": 0.8},
    ]

    result = await use_case.execute(valid_request)

    assert result.success
    assert result.total_results == 2
    retrieval_port.retrieve_similar.assert_called_once()
    auth_port.check_permission.assert_called_once()


@pytest.mark.asyncio
async def test_execute_authorization_failure(use_case, auth_port, valid_request):
    auth_port.check_permission.return_value = False
    with pytest.raises(AuthorizationError):
        await use_case.execute(valid_request)


def test_validate_request_missing_inputs(use_case, valid_request):
    req = CrossModalRetrievalRequestDTO(
        tenant_id="t1",
        user_id="u1",
        kg_id="kg1",
    )
    with pytest.raises(ValidationError):
        use_case._validate_request_internal(req)


@pytest.mark.asyncio
async def test_execute_with_audio(use_case, retrieval_port, auth_port):
    auth_port.check_permission.return_value = True
    request = CrossModalRetrievalRequestDTO(
        tenant_id="t1",
        user_id="u1",
        kg_id="kg1",
        audio_path="/tmp/audio.mp3",
    )
    retrieval_port.retrieve_similar.return_value = []
    result = await use_case.execute(request)
    assert result.total_results == 0
