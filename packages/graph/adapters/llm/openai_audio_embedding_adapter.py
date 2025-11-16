"""Basic audio embedding adapter using the ``wave`` module.

The adapter implements ``AudioEmbeddingPort`` by computing simple amplitude
statistics from WAV data.  It is intentionally lightweight so that it can be
used in environments without external audio dependencies.
"""

import wave
from io import BytesIO
from typing import Any, Dict, List, Optional, Union

import numpy as np

from application.ports.multimodal import AudioEmbeddingPort


class OpenAIAudioEmbeddingAdapter(AudioEmbeddingPort):
    """Generate embeddings from WAV files or bytes."""

    def __init__(self, features: int = 128) -> None:
        self.features = features

    def _load_audio(self, data: Any) -> np.ndarray:
        if isinstance(data, bytes):
            fh = wave.open(BytesIO(data))
        else:
            fh = wave.open(str(data))
        with fh:
            frames = fh.readframes(fh.getnframes())
            dtype = np.int16 if fh.getsampwidth() == 2 else np.uint8
            arr = np.frombuffer(frames, dtype=dtype).astype(np.float32)
        return arr

    def _embed_single(self, data: Any) -> List[float]:
        samples = self._load_audio(data)
        if len(samples) == 0:
            return [0.0] * self.features
        step = max(1, len(samples) // self.features)
        feats = [
            float(np.mean(np.abs(samples[i : i + step])))
            for i in range(0, len(samples), step)
        ]
        if len(feats) < self.features:
            feats.extend([0.0] * (self.features - len(feats)))
        return feats[: self.features]

    async def generate_audio_embedding(
        self,
        audio_path: str,
        model: str = "whisper-large-v2",
    ) -> List[float]:
        """Generate embedding for audio content."""
        return self._embed_single(audio_path)

    async def transcribe_audio(
        self,
        audio_path: str,
    ) -> str:
        """Transcribe audio to text."""
        # Simple placeholder transcription
        return f"[Audio transcription placeholder for {audio_path}]"

    async def extract_audio_features(
        self,
        audio_path: str,
    ) -> Dict[str, Any]:
        """Extract acoustic features from audio."""
        try:
            samples = self._load_audio(audio_path)
            return {
                "duration": len(samples) / 44100.0,  # Assuming 44.1kHz sample rate
                "sample_count": len(samples),
                "max_amplitude": (
                    float(np.max(np.abs(samples))) if len(samples) > 0 else 0.0
                ),
                "mean_amplitude": (
                    float(np.mean(np.abs(samples))) if len(samples) > 0 else 0.0
                ),
                "rms": float(np.sqrt(np.mean(samples**2))) if len(samples) > 0 else 0.0,
            }
        except Exception:
            return {
                "duration": 0.0,
                "sample_count": 0,
                "max_amplitude": 0.0,
                "mean_amplitude": 0.0,
                "rms": 0.0,
            }

    def embed(
        self,
        *,
        audio: Union[Any, List[Any]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        if isinstance(audio, list):
            return [self._embed_single(a) for a in audio]
        return self._embed_single(audio)
