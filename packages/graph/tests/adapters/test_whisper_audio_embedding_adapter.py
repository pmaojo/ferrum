import pytest
np = pytest.importorskip("numpy")
from typing import Any

from adapters.whisper_audio_embedding_adapter import WhisperAudioEmbeddingAdapter


class DummyModel:
    def __init__(self) -> None:
        self.counter = 0

    def encode(self, data: Any) -> np.ndarray:  # type: ignore[override]
        start = self.counter * 3
        self.counter += 1
        return np.array([[float(start), float(start + 1), float(start + 2)]], dtype=np.float32)


def dummy_load_audio(data: Any) -> np.ndarray:  # type: ignore[override]
    if isinstance(data, bytes):
        return np.frombuffer(data, dtype=np.uint8).astype(np.float32)
    return np.array(data, dtype=np.float32)


def dummy_preprocess(audio: np.ndarray) -> np.ndarray:
    return audio


def create_adapter() -> WhisperAudioEmbeddingAdapter:
    return WhisperAudioEmbeddingAdapter(
        model=DummyModel(), load_audio=dummy_load_audio, preprocess=dummy_preprocess
    )


def test_embed_single_array() -> None:
    adapter = create_adapter()
    data = np.array([1, 2, 3], dtype=np.float32)

    embedding = adapter.embed(audio=data, tenant_id="t")

    assert embedding == [0.0, 1.0, 2.0]


def test_embed_single_bytes() -> None:
    adapter = create_adapter()
    data = b"abc"

    embedding = adapter.embed(audio=data, tenant_id="t")

    assert embedding == [0.0, 1.0, 2.0]


def test_embed_multiple() -> None:
    adapter = create_adapter()

    embeddings = adapter.embed(audio=[b"a", b"b"], tenant_id="t")

    assert embeddings == [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]
