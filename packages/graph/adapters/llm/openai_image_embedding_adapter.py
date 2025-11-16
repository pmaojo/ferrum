"""Simple image embedding adapter using Pillow and NumPy.

This adapter implements ``ImageEmbeddingPort`` using a lightweight approach
that converts images to grayscale arrays and flattens them.  It avoids heavy
dependencies while providing deterministic embeddings suitable for tests.
"""

from io import BytesIO
from typing import Any, Dict, List, Optional, Union

import numpy as np
from PIL import Image

from application.ports.multimodal import ImageEmbeddingPort
from domain.entities.multimodal import EmbeddingModel


class OpenAIImageEmbeddingAdapter(ImageEmbeddingPort):
    """Generate image embeddings from raw data or file paths."""

    def __init__(self, size: int = 32) -> None:
        self.size = size

    def _load_image(self, data: Any) -> Image.Image:
        if isinstance(data, Image.Image):
            return data.convert("L")
        if isinstance(data, bytes):
            return Image.open(BytesIO(data)).convert("L")
        return Image.open(str(data)).convert("L")

    def _embed_single(self, data: Any) -> List[float]:
        image = self._load_image(data).resize((self.size, self.size))
        arr = np.asarray(image, dtype=np.float32).flatten() / 255.0
        return arr.tolist()

    async def generate_image_embedding(
        self,
        image_path: str,
        model: EmbeddingModel = EmbeddingModel.CLIP_VIT_B32,
    ) -> List[float]:
        """Generate embedding for an image."""
        return self._embed_single(image_path)

    async def generate_image_features(
        self,
        image_path: str,
    ) -> Dict[str, Any]:
        """Generate visual features from image."""
        image = self._load_image(image_path)
        return {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "format": getattr(image, "format", "Unknown"),
            "size": image.size,
        }

    async def compare_images(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """Calculate similarity between image embeddings."""
        # Calculate cosine similarity
        arr1 = np.array(embedding1)
        arr2 = np.array(embedding2)

        # Normalize vectors
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(arr1, arr2) / (norm1 * norm2))

    def embed(
        self,
        *,
        images: Union[Any, List[Any]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        if isinstance(images, list):
            return [self._embed_single(img) for img in images]
        return self._embed_single(images)
