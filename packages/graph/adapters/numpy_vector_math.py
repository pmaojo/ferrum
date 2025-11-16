"""Numpy-based implementation of VectorMathPort."""

from typing import List

import numpy as np

from application.ports import VectorMathPort


class NumpyVectorMathAdapter(VectorMathPort):
    """Vector math adapter using NumPy for efficient operations."""

    def cosine_similarities(
        self,
        *,
        query_embedding: List[float],
        embeddings: List[List[float]],
    ) -> List[float]:
        query_vec = np.array(query_embedding)
        vecs = np.array(embeddings)

        query_norm = np.linalg.norm(query_vec)
        vec_norms = np.linalg.norm(vecs, axis=1)
        if query_norm == 0 or np.any(vec_norms == 0):
            return [0.0 for _ in embeddings]

        query_vec = query_vec / query_norm
        vecs = vecs / vec_norms[:, np.newaxis]
        sims = np.dot(vecs, query_vec)
        return [float(max(0.0, min(1.0, sim))) for sim in sims]
