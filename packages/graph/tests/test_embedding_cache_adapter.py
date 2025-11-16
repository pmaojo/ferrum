"""Tests for the EmbeddingCacheAdapter."""

import pytest
pytest.importorskip("redis")
import unittest
from unittest.mock import MagicMock, patch
import json
import time
from datetime import datetime

from adapters.llm.embedding_cache_adapter import EmbeddingCacheAdapter, EmbeddingCacheException


class TestEmbeddingCacheAdapter(unittest.TestCase):
    """Test cases for the EmbeddingCacheAdapter."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock Redis client
        self.redis_patcher = patch('redis.from_url')
        self.mock_redis_from_url = self.redis_patcher.start()
        self.mock_redis_client = MagicMock()
        self.mock_redis_from_url.return_value = self.mock_redis_client

        # Mock Redis search index
        self.mock_ft = MagicMock()
        self.mock_redis_client.ft.return_value = self.mock_ft

        # Create adapter with mocked Redis
        self.adapter = EmbeddingCacheAdapter(
            redis_url="redis://localhost:6379",
            index_name="test_embedding_cache",
            vector_dim=768,
            cache_ttl=86400
        )

        # Test data
        self.test_text = "This is a test text for embedding"
        self.test_tenant_id = "test_tenant_123"
        self.test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5] * 153  # 765 dimensions
        self.test_hash = "test_hash_123"

        # Mock hash generation
        self.adapter._generate_hash = MagicMock(return_value=self.test_hash)

    def tearDown(self):
        """Tear down test fixtures."""
        self.redis_patcher.stop()

    def test_init_creates_index_if_not_exists(self):
        """Test that the adapter creates a vector search index if it doesn't exist."""
        # Setup
        self.mock_ft.info.side_effect = Exception("Index doesn't exist")

        # Execute
        adapter = EmbeddingCacheAdapter(
            redis_url="redis://localhost:6379",
            index_name="test_embedding_cache"
        )

        # Assert
        self.mock_ft.create_index.assert_called_once()

    def test_init_skips_index_creation_if_exists(self):
        """Test that the adapter skips index creation if it already exists."""
        # Setup
        self.mock_ft.info.return_value = {"num_docs": 0}

        # Execute
        adapter = EmbeddingCacheAdapter(
            redis_url="redis://localhost:6379",
            index_name="test_embedding_cache"
        )

        # Assert
        self.mock_ft.create_index.assert_not_called()

    def test_get_embedding_cache_hit(self):
        """Test retrieving an embedding from cache when it exists."""
        # Setup
        cache_key = f"{self.test_tenant_id}:embedding:{self.test_hash}"
        self.mock_redis_client.exists.return_value = True
        self.mock_redis_client.hgetall.return_value = {
            b"vector": json.dumps(self.test_embedding).encode(),
            b"metadata": json.dumps({"tenant_id": self.test_tenant_id}).encode()
        }

        # Execute
        result = self.adapter.get_embedding(
            text=self.test_text,
            tenant_id=self.test_tenant_id
        )

        # Assert
        self.mock_redis_client.exists.assert_called_once_with(cache_key)
        self.mock_redis_client.hgetall.assert_called_once_with(cache_key)
        self.assertEqual(result, self.test_embedding)

    def test_get_embedding_cache_miss(self):
        """Test retrieving an embedding from cache when it doesn't exist."""
        # Setup
        cache_key = f"{self.test_tenant_id}:embedding:{self.test_hash}"
        self.mock_redis_client.exists.return_value = False

        # Execute
        result = self.adapter.get_embedding(
            text=self.test_text,
            tenant_id=self.test_tenant_id
        )

        # Assert
        self.mock_redis_client.exists.assert_called_once_with(cache_key)
        self.mock_redis_client.hgetall.assert_not_called()
        self.assertIsNone(result)

    def test_store_embedding(self):
        """Test storing an embedding in the cache."""
        # Setup
        cache_key = f"{self.test_tenant_id}:embedding:{self.test_hash}"
        tenant_index_key = f"{self.test_tenant_id}:embeddings"
        mock_pipeline = MagicMock()
        self.mock_redis_client.pipeline.return_value = mock_pipeline

        # Execute
        result = self.adapter.store_embedding(
            text=self.test_text,
            embedding=self.test_embedding,
            tenant_id=self.test_tenant_id
        )

        # Assert
        self.mock_redis_client.pipeline.assert_called_once()
        mock_pipeline.hset.assert_called_once()
        mock_pipeline.expire.assert_called_once_with(cache_key, 86400)
        mock_pipeline.sadd.assert_called_once_with(tenant_index_key, cache_key)
        mock_pipeline.execute.assert_called_once()
        self.assertTrue(result)

    def test_find_similar(self):
        """Test finding similar embeddings using vector search."""
        # Setup
        mock_doc = MagicMock()
        mock_doc.id = "test_doc_id"
        mock_doc.vector_score = 0.2  # Distance, will be converted to similarity score 0.8
        mock_doc.metadata = json.dumps({"text_sample": "Similar text"})
        mock_doc.created_at = str(int(time.time()))

        mock_results = MagicMock()
        mock_results.docs = [mock_doc]
        self.mock_ft.search.return_value = mock_results

        # Execute
        results = self.adapter.find_similar(
            embedding=self.test_embedding,
            tenant_id=self.test_tenant_id,
            top_k=5,
            score_threshold=0.75
        )

        # Assert
        self.mock_ft.search.assert_called_once()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["key"], "test_doc_id")
        self.assertEqual(results[0]["score"], 0.8)  # 1 - 0.2 = 0.8

    def test_clear_tenant_cache(self):
        """Test clearing cached embeddings for a tenant."""
        # Setup
        tenant_index_key = f"{self.test_tenant_id}:embeddings"
        cache_keys = [b"key1", b"key2", b"key3"]
        self.mock_redis_client.smembers.return_value = cache_keys
        self.mock_redis_client.exists.return_value = True
        mock_pipeline = MagicMock()
        self.mock_redis_client.pipeline.return_value = mock_pipeline

        # Execute
        result = self.adapter.clear_tenant_cache(
            tenant_id=self.test_tenant_id
        )

        # Assert
        self.mock_redis_client.smembers.assert_called_once_with(tenant_index_key)
        self.assertEqual(mock_pipeline.delete.call_count, 3)
        self.assertEqual(mock_pipeline.srem.call_count, 3)
        mock_pipeline.execute.assert_called_once()
        self.assertEqual(result, 3)

    def test_generate_hash(self):
        """Test hash generation for text and options."""
        # Restore original method for this test
        self.adapter._generate_hash = EmbeddingCacheAdapter._generate_hash

        # Execute
        hash1 = self.adapter._generate_hash(
            text=self.test_text,
            tenant_id=self.test_tenant_id
        )

        hash2 = self.adapter._generate_hash(
            text=self.test_text,
            tenant_id=self.test_tenant_id
        )

        hash3 = self.adapter._generate_hash(
            text=self.test_text + " different",
            tenant_id=self.test_tenant_id
        )

        # Assert
        self.assertEqual(hash1, hash2)  # Same inputs should produce same hash
        self.assertNotEqual(hash1, hash3)  # Different inputs should produce different hash


if __name__ == '__main__':
    unittest.main()