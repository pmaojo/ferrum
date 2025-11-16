import pytest
from unittest.mock import AsyncMock
import types
import sys

ports_stub = types.ModuleType("application.ports.multimodal")

class TextResponseGeneratorPort:
    async def compose(self, texts: list[str]) -> str: ...

class ImageSelectionPort:
    async def select(self, image_paths: list[str]) -> list[str]: ...

class AudioSynthesisPort:
    async def synthesize(self, text: str) -> str: ...

ports_stub.TextResponseGeneratorPort = TextResponseGeneratorPort
ports_stub.ImageSelectionPort = ImageSelectionPort
ports_stub.AudioSynthesisPort = AudioSynthesisPort

sys.modules.setdefault("application.ports.multimodal", ports_stub)

from domain.multimodal_response_generator import MultimodalResponseGenerator


@pytest.mark.asyncio
async def test_generate_unified_response():
    text_gen = AsyncMock(spec=TextResponseGeneratorPort)
    img_sel = AsyncMock(spec=ImageSelectionPort)
    audio_syn = AsyncMock(spec=AudioSynthesisPort)

    text_gen.compose.return_value = "summary"
    img_sel.select.return_value = ["img1", "img2"]
    audio_syn.synthesize.return_value = "audio"

    generator = MultimodalResponseGenerator(text_gen, img_sel, audio_syn)

    inputs = {
        "text": "hello",
        "images": [{"path": "img1"}, {"path": "img2"}],
        "documents": [{"content": "doc"}],
        "audio": [{"transcription": "speech"}],
    }

    result = await generator.generate(inputs)

    text_gen.compose.assert_called_once()
    img_sel.select.assert_called_once_with(["img1", "img2"])
    audio_syn.synthesize.assert_called_once_with("summary")

    assert result == {"text": "summary", "images": ["img1", "img2"], "audio": "audio"}
