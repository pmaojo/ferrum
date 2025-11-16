"""Tests for the GeminiLLMAdapter with embedding cache integration."""

import unittest
from unittest.mock import MagicMock, patch
import json
import pytest
pytest.importorskip("redis")
from datetime import datetime

from adapters.llm.gemini_llm_adapter import GeminiLLMAdapter, LLMException, QuotaExceededException
from adapters.llm.embedding_cache_adapter import EmbeddingCacheAdapter


class TestGeminiLLMAdapterWithCache(unittest.TestCase):
    """Test cases for the GeminiLLMAdapter with embedding cache integration."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock genai module
        self.genai_patcher = patch('adapters.gemini_llm_adapter.genai')
        self.mock_genai = self.genai_patcher.start()

        # Mock embedding cache
        self.mock_embedding_cache = MagicMock(spec=EmbeddingCacheAdapter)

        # Mock tracer
        self.mock_tracer = MagicMock()

        # Create adapter with mocked dependencies
        self.adapter = GeminiLLMAdapter(
            api_key="test_api_key",
            generation_model="gemini-2.5-flash",
            embedding_model="text-embedding-004",
            embedding_cache=self.mock_embedding_cache,
            tracer=self.mock_tracer
        )

        # Test data
        self.test_text = "This is a test text for embedding"
        self.test_tenant_id = "test_tenant_123"
        self.test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5] * 153  # 765 dimensions

    def tearDown(self):
        """Tear down test fixtures."""
        self.genai_patcher.stop()

    def test_embed_with_cache_hit(self):
        """Test embedding generation with cache hit."""
        # Setup
        self.mock_embedding_cache.get_embedding.return_value = self.test_embedding

        # Execute
        result = self.adapter.embed(
            text=self.test_text,
            tenant_id=self.test_tenant_id
        )

        # Assert
        self.mock_embedding_cache.get_embedding.assert_called_once_with(
            text=self.test_text,
            tenant_id=self.test_tenant_id,
            opts=None
        )
        self.mock_tracer.record_metric.assert_called_with(
            name="embedding_cache_hit",
            value=1.0,
            tenant_id=self.test_tenant_id
        )
        self.mock_genai.get_embedding_model.assert_not_called()
        self.assertEqual(result, self.test_embedding)

    def test_embed_with_cache_miss(self):
        """Test embedding generation with cache miss."""
        # Setup
        self.mock_embedding_cache.get_embedding.return_value = None

        mock_embedding_model = MagicMock()
        mock_result = MagicMock()
        mock_result.embedding = self.test_embedding
        mock_embedding_model.embed_content.return_value = mock_result
        self.mock_genai.get_embedding_model.return_value = mock_embedding_model

        # Execute
        result = self.adapter.embed(
            text=self.test_text,
            tenant_id=self.test_tenant_id
        )

        # Assert
        self.mock_embedding_cache.get_embedding.assert_called_once_with(
            text=self.test_text,
            tenant_id=self.test_tenant_id,
            opts=None
        )
        self.mock_genai.get_embedding_model.assert_called_once_with("text-embedding-004")
        mock_embedding_model.embed_content.assert_called_once_with(self.test_text)
        self.mock_embedding_cache.store_embedding.assert_called_once_with(
            text=self.test_text,
            embedding=self.test_embedding,
            tenant_id=self.test_tenant_id,
            opts=None
        )
        self.assertEqual(result, self.test_embedding)

    def test_embed_batch_with_cache_miss(self):
        """Test batch embedding generation with cache miss."""
        # Setup
        test_texts = ["Text 1", "Text 2", "Text 3"]
        test_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]

        self.mock_embedding_cache.get_embedding.return_value = None

        mock_embedding_model = MagicMock()
        mock_results = [MagicMock(), MagicMock(), MagicMock()]
        for i, mock_result in enumerate(mock_results):
            mock_result.embedding = test_embeddings[i]
        mock_embedding_model.batch_embed_content.return_value = mock_results
        self.mock_genai.get_embedding_model.return_value = mock_embedding_model

        # Execute
        result = self.adapter.embed(
            text=test_texts,
            tenant_id=self.test_tenant_id
        )

        # Assert
        self.mock_embedding_cache.get_embedding.assert_called_once_with(
            text=test_texts,
            tenant_id=self.test_tenant_id,
            opts=None
        )
        self.mock_genai.get_embedding_model.assert_called_once_with("text-embedding-004")
        mock_embedding_model.batch_embed_content.assert_called_once_with(test_texts)
        self.mock_embedding_cache.store_embedding.assert_called_once_with(
            text=test_texts,
            embedding=test_embeddings,
            tenant_id=self.test_tenant_id,
            opts=None
        )
        self.assertEqual(result, test_embeddings)

    def test_embed_with_quota_exceeded(self):
        """Test embedding generation with quota exceeded error."""
        # Setup
        self.mock_embedding_cache.get_embedding.return_value = None

        mock_embedding_model = MagicMock()
        mock_embedding_model.embed_content.side_effect = self.mock_genai.exceptions.ResourceExhausted("Quota exceeded")
        self.mock_genai.get_embedding_model.return_value = mock_embedding_model

        # Execute and Assert
        with self.assertRaises(QuotaExceededException):
            self.adapter.embed(
                text=self.test_text,
                tenant_id=self.test_tenant_id
            )

        self.mock_tracer.record_metric.assert_called_with(
            name="gemini_quota_exceeded",
            value=1.0,
            tenant_id=self.test_tenant_id,
            operation="embed"
        )

    def test_embed_with_general_error(self):
        """Test embedding generation with general error."""
        # Setup
        self.mock_embedding_cache.get_embedding.return_value = None

        mock_embedding_model = MagicMock()
        mock_embedding_model.embed_content.side_effect = Exception("General error")
        self.mock_genai.get_embedding_model.return_value = mock_embedding_model

        # Execute and Assert
        with self.assertRaises(LLMException):
            self.adapter.embed(
                text=self.test_text,
                tenant_id=self.test_tenant_id
            )

        self.mock_tracer.record_metric.assert_called_with(
            name="gemini_embedding_errors",
            value=1.0,
            tenant_id=self.test_tenant_id,
            error_type="Exception"
        )


if __name__ == '__main__':
    unittest.main()