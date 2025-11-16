from __future__ import annotations

from typing import Any, Dict, List, Optional

from application.ports.multimodal import (
    TextResponseGeneratorPort,
    ImageSelectionPort,
    AudioSynthesisPort,
)


class MultimodalResponseGenerator:
    """Compose unified responses from cross-modal retrieval results."""

    def __init__(
        self,
        text_generator: TextResponseGeneratorPort,
        image_selector: ImageSelectionPort,
        audio_generator: Optional[AudioSynthesisPort] = None,
    ) -> None:
        self._text_generator = text_generator
        self._image_selector = image_selector
        self._audio_generator = audio_generator

    async def generate(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a multimodal response from retrieval outputs."""
        text_chunks: List[str] = []
        if text := inputs.get("text"):
            text_chunks.append(str(text))
        for doc in inputs.get("documents", []):
            content = doc.get("content")
            if content:
                text_chunks.append(str(content))
        for aud in inputs.get("audio", []):
            transcription = aud.get("transcription")
            if transcription:
                text_chunks.append(str(transcription))

        summary = await self._text_generator.compose(text_chunks)

        image_paths = [img.get("path") for img in inputs.get("images", []) if img.get("path")]
        selected_images = await self._image_selector.select(image_paths)

        audio_resp = None
        if self._audio_generator:
            audio_resp = await self._audio_generator.synthesize(summary)

        return {
            "text": summary,
            "images": selected_images,
            "audio": audio_resp,
        }
