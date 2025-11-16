from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np

from application.ports.base import AudioEmbeddingPort

logger = logging.getLogger(__name__)

WHISPER_AVAILABLE = False
try:  # pragma: no cover - optional dependency
    import torch
    import whisper

    WHISPER_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    whisper = None  # type: ignore[assignment]
    torch = None  # type: ignore[assignment]


class WhisperAudioEmbeddingAdapter(AudioEmbeddingPort):
    """Audio embedding adapter using Whisper when available."""

    def __init__(
        self,
        model_name: str = "base",
        device: Optional[str] = None,
        cache_dir: Optional[str] = None,
        enable_preprocessing: bool = True,
        model: Optional[Any] = None,
        load_audio: Optional[Callable[[Any], np.ndarray]] = None,
        preprocess: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    ):
        """Initialize Whisper audio embedding adapter.

        If ``model`` is not provided, Whisper must be available so the model can be
        loaded dynamically. ``load_audio`` and ``preprocess`` functions can also be
        injected to avoid relying on Whisper utilities during testing.
        """
        if model is None and not WHISPER_AVAILABLE:
            raise ImportError(
                "torch and whisper are required for WhisperAudioEmbeddingAdapter. "
                "Install them with: pip install torch whisper-openai"
            )

        self.model_name = model_name
        self.device = device or (
            "cuda" if WHISPER_AVAILABLE and torch and torch.cuda.is_available() else "cpu"
        )
        self.cache_dir = cache_dir
        self.enable_preprocessing = enable_preprocessing
        self._model = model
        self._load_audio = load_audio
        self._preprocess = preprocess

    @property
    def model(self) -> Any:
        """Return the embedding model, loading it if necessary."""
        if self._model is None:
            assert WHISPER_AVAILABLE
            self._model = whisper.load_model(
                self.model_name, device=self.device, download_root=self.cache_dir
            )
        return self._model

    def _load(self, data: Any) -> np.ndarray:
        if self._load_audio is not None:
            return self._load_audio(data)
        if not WHISPER_AVAILABLE:
            raise RuntimeError(
                "load_audio function not provided and whisper is unavailable"
            )
        return whisper.audio.load_audio(data)

    def _preprocess_audio(self, audio: np.ndarray) -> np.ndarray:
        if not self.enable_preprocessing:
            return audio
        if self._preprocess is not None:
            return self._preprocess(audio)
        if not WHISPER_AVAILABLE:
            raise RuntimeError(
                "preprocess function not provided and whisper is unavailable"
            )
        return whisper.log_mel_spectrogram(whisper.pad_or_trim(audio)).to(self.device)

    def _embed_single(self, data: Any) -> List[float]:
        """Embed a single audio sample."""
        audio = self._load(data)
        audio = self._preprocess_audio(audio)
        embedding = self.model.encode(audio)
        if hasattr(embedding, "cpu"):
            embedding = embedding.cpu()
        return np.asarray(embedding).flatten().tolist()

    def embed(
        self,
        *,
        audio: Union[Any, List[Any]],
        tenant_id: str,  # noqa: ARG002 - part of interface
        opts: Optional[Dict[str, Any]] = None,  # noqa: ARG002 - for future use
    ) -> Union[List[float], List[List[float]]]:
        """Embed audio or a list of audio samples."""
        if isinstance(audio, list):
            return [self._embed_single(a) for a in audio]
        return self._embed_single(audio)
