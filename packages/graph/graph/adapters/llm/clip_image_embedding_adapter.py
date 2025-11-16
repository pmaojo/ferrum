"""Image embedding adapter leveraging OpenAI CLIP."""

from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List, Optional, Union

import torch
from PIL import Image

from application.ports import ImageEmbeddingPort


class CLIPImageEmbeddingAdapter(ImageEmbeddingPort):
    """Generate image embeddings using a CLIP model."""

    def __init__(
        self,
        *,
        model: Optional[Any] = None,
        preprocess: Optional[Any] = None,
        device: str = "cpu",
        model_name: str = "ViT-B/32",
    ) -> None:
        self.device = device
        if model is None or preprocess is None:
            import clip

            self.model, self.preprocess = clip.load(model_name, device=device)
        else:
            self.model = model
            self.preprocess = preprocess

    def _load_image(self, data: Any) -> Image.Image:
        if isinstance(data, Image.Image):
            return data.convert("RGB")
        if isinstance(data, bytes):
            return Image.open(BytesIO(data)).convert("RGB")
        return Image.open(str(data)).convert("RGB")

    def _embed_single(self, data: Any) -> List[float]:
        image = self._load_image(data)
        tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            embedding = self.model.encode_image(tensor)
        return embedding[0].cpu().tolist()

    def embed(
        self,
        *,
        images: Union[Any, List[Any]],
        tenant_id: str,  # noqa: ARG002 - part of interface
        opts: Optional[Dict[str, Any]] = None,  # noqa: ARG002 - for future use
    ) -> Union[List[float], List[List[float]]]:
        if isinstance(images, list):
            return [self._embed_single(img) for img in images]
        return self._embed_single(images)
