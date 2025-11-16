import logging
from io import BytesIO
from typing import Any, Dict, List, Optional, Union

import numpy as np

try:
    import aiohttp
    import torch
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    # Provide fallback stubs
    torch = None
    CLIPModel = None
    CLIPProcessor = None

logger = logging.getLogger(__name__)


class CLIPv2EmbeddingAdapter:
    """Advanced CLIP v2 adapter supporting multiple models and modalities."""

    def __init__(
        self,
        model_name: str = "openai/clip-vit-large-patch14-336",
        device: Optional[str] = None,
    ):
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers library is required for CLIP v2 adapter")

        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # Load model and processor
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)

        # Model configuration
        self.embedding_dim = self.model.config.projection_dim

        logger.info(f"Loaded CLIP model {model_name} on {self.device}")

    async def encode_images(
        self, images: List[Union[str, Image.Image]], batch_size: int = 32
    ) -> np.ndarray:
        """Encode images to embeddings with batching support."""
        embeddings = []

        # Process images in batches
        for i in range(0, len(images), batch_size):
            batch = images[i : i + batch_size]
            processed_images = []

            for img in batch:
                if isinstance(img, str):
                    # Load from URL or file path
                    if img.startswith(("http://", "https://")):
                        async with aiohttp.ClientSession() as session:
                            async with session.get(img) as response:
                                img_data = await response.read()
                                processed_images.append(Image.open(BytesIO(img_data)))
                    else:
                        processed_images.append(Image.open(img))
                else:
                    processed_images.append(img)

            # Process batch
            inputs = self.processor(
                images=processed_images, return_tensors="pt", padding=True
            ).to(self.device)

            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                # Normalize embeddings
                image_features = image_features / image_features.norm(
                    p=2, dim=-1, keepdim=True
                )
                embeddings.append(image_features.cpu().numpy())

        return np.vstack(embeddings)

    async def encode_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode texts to embeddings with batching support."""
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            inputs = self.processor(
                text=batch, return_tensors="pt", padding=True, truncation=True
            ).to(self.device)

            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
                # Normalize embeddings
                text_features = text_features / text_features.norm(
                    p=2, dim=-1, keepdim=True
                )
                embeddings.append(text_features.cpu().numpy())

        return np.vstack(embeddings)

    async def compute_similarity(
        self, image_embeddings: np.ndarray, text_embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute cosine similarity between image and text embeddings."""
        # Ensure embeddings are normalized
        image_embeddings = image_embeddings / np.linalg.norm(
            image_embeddings, axis=1, keepdims=True
        )
        text_embeddings = text_embeddings / np.linalg.norm(
            text_embeddings, axis=1, keepdims=True
        )

        # Compute similarity matrix
        similarity = np.dot(image_embeddings, text_embeddings.T)
        return similarity

    async def find_best_matches(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: np.ndarray,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find top-k most similar embeddings."""
        # Compute similarities
        similarities = np.dot(query_embedding, candidate_embeddings.T).flatten()

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append(
                {
                    "index": int(idx),
                    "similarity": float(similarities[idx]),
                    "rank": len(results) + 1,
                }
            )

        return results

    async def cross_modal_search(
        self,
        query: Union[str, Image.Image],
        candidates: List[Union[str, Image.Image]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Perform cross-modal search (text->image or image->text)."""
        # Encode query
        if isinstance(query, str):
            query_embedding = await self.encode_texts([query])
        else:
            query_embedding = await self.encode_images([query])

        # Encode candidates
        text_candidates = [c for c in candidates if isinstance(c, str)]
        image_candidates = [c for c in candidates if not isinstance(c, str)]

        all_embeddings = []
        candidate_info = []

        if text_candidates:
            text_embeddings = await self.encode_texts(text_candidates)
            all_embeddings.append(text_embeddings)
            candidate_info.extend(
                [{"type": "text", "content": c} for c in text_candidates]
            )

        if image_candidates:
            image_embeddings = await self.encode_images(image_candidates)
            all_embeddings.append(image_embeddings)
            candidate_info.extend(
                [{"type": "image", "content": c} for c in image_candidates]
            )

        if not all_embeddings:
            return []

        candidate_embeddings = np.vstack(all_embeddings)

        # Find best matches
        matches = await self.find_best_matches(
            query_embedding[0], candidate_embeddings, top_k
        )

        # Add candidate information
        for match in matches:
            match.update(candidate_info[match["index"]])

        return matches
