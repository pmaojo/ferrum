"""Tests for LouvainClusteringAdapter implementation."""

import json
import logging
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from adapters.retrievers.falkordb_graph_adapter import FalkorGraphAdapter
from adapters.louvain_clustering_adapter import (
    ClusteringException,
    LouvainClusteringAdapter,
)
from domain.entities import Community, Triple


@pytest.fixture
def mock_falkordb_adapter():
    """Create a mock FalkorDB adapter for testing."""
    mock_adapter = MagicMock(spec=FalkorGraphAdapter)

    # Mock query method to return test data
    def mock_query(**kwargs):
        cypher = kwargs.get("cypher", "")
        kg_id = kwargs.get("kg_id", "")
        tenant_id = kwargs.get("tenant_id", "")
        params = kwargs.get("params", {})

        # Mock node query results
        if "MATCH (n)" in cypher:
            return {
                "results": [
                    {
                        "id": f"node{i}",
                        "labels": ["Entity"],
                        "properties": {"value": i * 10},
                    }
                    for i in range(1, 21)
                ],
                "execution_time_ms": 5.0,
                "metrics": {},
                "result_count": 20,
            }

        # Mock edge query results
        elif "MATCH (s)-[r]->(o)" in cypher and "WHERE s.id IN" not in cypher:
            return {
                "results": [
                    {
                        "source": f"node{i}",
                        "target": f"node{i+1}",
                        "type": "RELATED_TO",
                        "properties": {"weight": 1.0},
                    }
                    for i in range(1, 20)
                ],
                "execution_time_ms": 5.0,
                "metrics": {},
                "result_count": 19,
            }

        # Mock community query results
        elif "MATCH (c:Community" in cypher:
            community_id = params.get("community_id", "")
            if community_id == "test_kg:1":
                return {
                    "results": [
                        {
                            "c": {
                                "id": "test_kg:1",
                                "kg_id": "test_kg",
                                "tenant_id": "test_tenant",
                                "size": 10,
                                "node_ids": [f"node{i}" for i in range(1, 11)],
                                "centroid_embedding": [0.1, 0.2, 0.3, 0.4],
                            }
                        }
                    ],
                    "execution_time_ms": 5.0,
                    "metrics": {},
                    "result_count": 1,
                }
            else:
                return {
                    "results": [],
                    "execution_time_ms": 5.0,
                    "metrics": {},
                    "result_count": 0,
                }

        # Mock subgraph query results
        elif "MATCH (s)-[r]->(o)" in cypher and "WHERE s.id IN" in cypher:
            node_ids = params.get("node_ids", [])
            results = []

            for i in range(len(node_ids) - 1):
                if node_ids[i] in node_ids and node_ids[i + 1] in node_ids:
                    results.append(
                        {
                            "subject": node_ids[i],
                            "predicate": "RELATED_TO",
                            "object": node_ids[i + 1],
                        }
                    )

            return {
                "results": results,
                "execution_time_ms": 5.0,
                "metrics": {},
                "result_count": len(results),
            }

        # Default empty response
        return {
            "results": [],
            "execution_time_ms": 5.0,
            "metrics": {},
            "result_count": 0,
        }

    mock_adapter.query = MagicMock(side_effect=mock_query)
    return mock_adapter


@pytest.fixture
def clustering_adapter(mock_falkordb_adapter):
    """Create a LouvainClusteringAdapter with mocked dependencies."""
    adapter = LouvainClusteringAdapter(
        falkordb_adapter=mock_falkordb_adapter,
        executor_threads=2,
        cache_ttl_seconds=60,
        min_community_size=3,
        embedding_dimensions=4,
    )

    # Mock NetworkX and community modules
    adapter.nx = MagicMock()
    adapter.louvain_community = MagicMock()
    adapter.pca = MagicMock()

    # Mock graph construction
    mock_graph = MagicMock()
    mock_graph.number_of_nodes.return_value = 20
    mock_graph.number_of_edges.return_value = 19
    mock_graph.nodes.return_value = [f"node{i}" for i in range(1, 21)]
    adapter._build_networkx_graph = MagicMock(return_value=mock_graph)

    # Mock Louvain algorithm
    mock_communities = {f"node{i}": i % 2 for i in range(1, 21)}
    adapter._apply_louvain_clustering = MagicMock(return_value=mock_communities)

    # Mock centroid embedding generation
    adapter._generate_centroid_embedding = MagicMock(return_value=[0.1, 0.2, 0.3, 0.4])

    return adapter


class TestLouvainClusteringAdapter:
    """Test suite for LouvainClusteringAdapter."""

    def test_compute_communities(self, clustering_adapter, mock_falkordb_adapter):
        """Test computing communities with Louvain algorithm."""
        # Call the method
        communities = clustering_adapter.compute_communities(
            kg_id="test_kg", tenant_id="test_tenant", algorithm="louvain"
        )

        # Verify results
        assert len(communities) == 2  # Two communities (0 and 1)
        assert all(isinstance(c, Community) for c in communities)
        assert all(c.tenant_id == "test_tenant" for c in communities)
        assert all(len(c.centroid_embedding) == 4 for c in communities)

        # Verify method calls
        mock_falkordb_adapter.query.assert_called()
        clustering_adapter._build_networkx_graph.assert_called_once()
        clustering_adapter._apply_louvain_clustering.assert_called_once()

    def test_get_community_subgraph(self, clustering_adapter, mock_falkordb_adapter):
        """Test retrieving community subgraph."""
        # Call the method
        triples = clustering_adapter.get_community_subgraph(
            community_id="test_kg:1", tenant_id="test_tenant"
        )

        # Verify results
        assert isinstance(triples, list)
        assert all(isinstance(t, Triple) for t in triples)
        assert all(t.tenant_id == "test_tenant" for t in triples)

        # Verify method calls
        mock_falkordb_adapter.query.assert_called()

    def test_get_community_subgraph_not_found(self, clustering_adapter):
        """Test retrieving non-existent community subgraph."""
        # Call the method with non-existent community ID
        with pytest.raises(ValueError):
            clustering_adapter.get_community_subgraph(
                community_id="test_kg:999", tenant_id="test_tenant"
            )

    def test_invalid_algorithm(self, clustering_adapter):
        """Test computing communities with invalid algorithm."""
        # Call the method with invalid algorithm
        with pytest.raises(ValueError):
            clustering_adapter.compute_communities(
                kg_id="test_kg", tenant_id="test_tenant", algorithm="invalid_algorithm"
            )

    def test_community_caching(self, clustering_adapter):
        """Test community caching functionality."""
        # First call should compute communities
        communities1 = clustering_adapter.compute_communities(
            kg_id="test_kg", tenant_id="test_tenant", algorithm="louvain"
        )

        # Reset mock to verify second call doesn't recompute
        clustering_adapter._build_networkx_graph.reset_mock()
        clustering_adapter._apply_louvain_clustering.reset_mock()

        # Second call should use cache
        communities2 = clustering_adapter.compute_communities(
            kg_id="test_kg", tenant_id="test_tenant", algorithm="louvain"
        )

        # Verify results are the same
        assert len(communities1) == len(communities2)
        assert all(c1.id == c2.id for c1, c2 in zip(communities1, communities2))

        # Verify methods were not called again
        clustering_adapter._build_networkx_graph.assert_not_called()
        clustering_adapter._apply_louvain_clustering.assert_not_called()

    def test_cache_expiration(self, clustering_adapter):
        """Test community cache expiration."""
        # Set very short cache TTL
        clustering_adapter.cache_ttl = 0.1

        # First call should compute communities
        communities1 = clustering_adapter.compute_communities(
            kg_id="test_kg", tenant_id="test_tenant", algorithm="louvain"
        )

        # Reset mock to verify second call recomputes after cache expires
        clustering_adapter._build_networkx_graph.reset_mock()
        clustering_adapter._apply_louvain_clustering.reset_mock()

        # Wait for cache to expire
        time.sleep(0.2)

        # Second call should recompute
        communities2 = clustering_adapter.compute_communities(
            kg_id="test_kg", tenant_id="test_tenant", algorithm="louvain"
        )

        # Verify methods were called again
        clustering_adapter._build_networkx_graph.assert_called_once()
        clustering_adapter._apply_louvain_clustering.assert_called_once()

    @pytest.mark.skip(reason="Async test requires pytest-asyncio")
    def test_compute_communities_async(self, clustering_adapter):
        """Test asynchronous community computation."""
        # This test is skipped because it requires pytest-asyncio
        pass

    def test_error_handling(self, clustering_adapter, mock_falkordb_adapter):
        """Test error handling during community computation."""
        # Make FalkorDB adapter raise an exception
        mock_falkordb_adapter.query.side_effect = Exception("Database error")

        # Call the method
        with pytest.raises(ClusteringException) as excinfo:
            clustering_adapter.compute_communities(
                kg_id="test_kg", tenant_id="test_tenant", algorithm="louvain"
            )

        # Verify exception details
        assert "Community computation failed" in str(excinfo.value)
        assert excinfo.value.error_code == "CLUSTERING_COMPUTATION_ERROR"
        assert "test_kg" in excinfo.value.context["kg_id"]
        assert "test_tenant" in excinfo.value.context["tenant_id"]


class TestPerformance:
    """Performance tests for LouvainClusteringAdapter."""

    @pytest.mark.skip(reason="Performance test - run manually")
    def test_large_graph_performance(self, mock_falkordb_adapter):
        """Test performance with large graphs (>50k nodes)."""
        # This test is marked as skipped by default since it's a performance test
        # that would be run manually or in a dedicated performance testing environment

        # Create a large graph adapter with real dependencies
        adapter = LouvainClusteringAdapter(
            falkordb_adapter=mock_falkordb_adapter,
            executor_threads=8,  # More threads for parallel processing
            cache_ttl_seconds=3600,
            min_community_size=10,
            embedding_dimensions=64,
        )

        # Mock large graph data
        node_count = 50000
        edge_count = 100000

        # Mock query method for large graph
        def mock_large_query(**kwargs):
            cypher = kwargs.get("cypher", "")

            # Mock node query results for large graph
            if "MATCH (n)" in cypher:
                return {
                    "results": [
                        {
                            "id": f"node{i}",
                            "labels": ["Entity"],
                            "properties": {"value": i % 1000},
                        }
                        for i in range(1, 101)  # Return first 100 nodes for testing
                    ],
                    "execution_time_ms": 500.0,
                    "metrics": {"total_nodes": node_count},
                    "result_count": node_count,
                }

            # Mock edge query results for large graph
            elif "MATCH (s)-[r]->(o)" in cypher:
                return {
                    "results": [
                        {
                            "source": f"node{i}",
                            "target": f"node{(i*17) % node_count + 1}",
                            "type": "RELATED_TO",
                            "properties": {"weight": 1.0},
                        }
                        for i in range(1, 101)  # Return first 100 edges for testing
                    ],
                    "execution_time_ms": 800.0,
                    "metrics": {"total_edges": edge_count},
                    "result_count": edge_count,
                }

            # Default empty response
            return {
                "results": [],
                "execution_time_ms": 5.0,
                "metrics": {},
                "result_count": 0,
            }

        mock_falkordb_adapter.query = MagicMock(side_effect=mock_large_query)

        # Measure performance
        start_time = time.time()

        # Use async method for large graphs
        import asyncio

        communities = asyncio.run(
            adapter.compute_communities_async(
                kg_id="large_test_kg", tenant_id="test_tenant", algorithm="louvain"
            )
        )

        end_time = time.time()
        execution_time = end_time - start_time

        # Log performance metrics
        logger = logging.getLogger(__name__)
        logger.info("Large graph clustering performance:")
        logger.info("- Node count: %s", node_count)
        logger.info("- Edge count: %s", edge_count)
        logger.info("- Community count: %s", len(communities))
        logger.info("- Execution time: %.2f seconds", execution_time)

        # Assert performance requirements
        assert execution_time < 60, "Clustering should complete in under 60 seconds"
        assert len(communities) > 0, "Should detect at least one community"
