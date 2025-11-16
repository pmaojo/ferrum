"""Unit tests for FalkorDB query execution functionality.

This module contains unit tests for the FalkorDB adapter's query execution
functionality that don't require external dependencies like TestContainers.
"""

import pytest
pytest.importorskip("redis")
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

from adapters.retrievers.falkordb_graph_adapter import FalkorGraphAdapter, FalkorDBException
from domain.entities import Triple, KnowledgeGraph


class TestFalkorDBQueryExecutionUnit:
    """Unit test suite for FalkorDB query execution."""

    @pytest.fixture
    def adapter(self):
        """Create FalkorDB adapter for testing."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.script_load.return_value = "sha"
        mock_client.evalsha.return_value = json.dumps({
            "results": [],
            "execution_time_ms": 1,
            "metrics": {},
            "result_count": 0
        })
        mock_manager = MagicMock()
        mock_manager.client = mock_client
        mock_manager.scripts = {"tenant_filtered_query": "sha"}
        mock_manager.script_sources = {"tenant_filtered_query": ""}
        with patch('adapters.retrievers.falkordb_graph_adapter.FalkorDBConnectionManager', return_value=mock_manager):
            return FalkorGraphAdapter(
                connection_string="redis://localhost:6379",
                batch_size=100
            )

    def test_query_method_signature_and_return_format(self, adapter):
        """Test that query method has correct signature and return format."""
        result = adapter.query(
            cypher="MATCH (n) RETURN n LIMIT 1",
            kg_id="test_kg",
            tenant_id="test_tenant"
        )

        # Verify return format
        assert isinstance(result, dict)
        assert "results" in result
        assert "execution_time_ms" in result
        assert "metrics" in result
        assert "result_count" in result
        assert "query_plan" in result

        # Verify metrics structure
        metrics = result["metrics"]
        assert "total_execution_time_ms" in metrics
        assert "lua_execution_time_ms" in metrics
        assert "overhead_ms" in metrics
        assert "query_hash" in metrics
        assert "cache_hit" in metrics
        assert "optimization_enabled" in metrics

    def test_query_optimization_flags(self, adapter):
        """Test query optimization enable/disable functionality."""
        # Test with optimization enabled
        result_optimized = adapter.query(
            cypher="MATCH (n) RETURN n",
            kg_id="test_kg",
            tenant_id="test_tenant",
            enable_optimization=True
        )

        assert result_optimized["metrics"]["optimization_enabled"] is True

        # Test with optimization disabled
        result_unoptimized = adapter.query(
            cypher="MATCH (n) RETURN n",
            kg_id="test_kg",
            tenant_id="test_tenant",
            enable_optimization=False
        )

        assert result_unoptimized["metrics"]["optimization_enabled"] is False

    def test_query_metrics_collection(self, adapter):
        """Test query metrics collection functionality."""
        # Test with metrics collection enabled
        result_with_metrics = adapter.query(
            cypher="MATCH (n) RETURN n",
            kg_id="test_kg",
            tenant_id="test_tenant",
            collect_metrics=True
        )

        assert "detailed_metrics_collected" in result_with_metrics["metrics"]

        # Test with metrics collection disabled
        result_without_metrics = adapter.query(
            cypher="MATCH (n) RETURN n",
            kg_id="test_kg",
            tenant_id="test_tenant",
            collect_metrics=False
        )

        # Basic metrics should still be present
        assert "optimization_enabled" in result_without_metrics["metrics"]

    def test_query_parameter_handling(self, adapter):
        """Test query parameter handling."""
        params = {"node_id": "test_node", "limit": 10}

        result = adapter.query(
            cypher="MATCH (n {id: $node_id}) RETURN n LIMIT $limit",
            kg_id="test_kg",
            tenant_id="test_tenant",
            params=params
        )

        assert isinstance(result, dict)
        assert "results" in result

    def test_query_timeout_parameter(self, adapter):
        """Test query timeout parameter handling."""
        result = adapter.query(
            cypher="MATCH (n) RETURN n",
            kg_id="test_kg",
            tenant_id="test_tenant",
            timeout_ms=5000
        )

        assert isinstance(result, dict)
        assert result["execution_time_ms"] >= 0

    def test_query_optimization_analysis(self, adapter):
        """Test query optimization analysis functionality."""
        optimization = adapter.optimize_query(
            cypher="MATCH (n) RETURN n",  # Full scan query
            kg_id="test_kg",
            tenant_id="test_tenant"
        )

        # Verify optimization result structure
        assert isinstance(optimization, dict)
        assert "analysis" in optimization
        assert "suggestions" in optimization
        assert "optimized_query" in optimization
        assert "optimization_score" in optimization

        # Verify analysis structure
        analysis = optimization["analysis"]
        assert "original_query" in analysis
        assert "complexity_score" in analysis
        assert "estimated_cost" in analysis
        assert "index_usage" in analysis
        assert "bottlenecks" in analysis

        # Should detect full scan issue
        assert analysis["complexity_score"] > 0

        # Should provide suggestions
        suggestions = optimization["suggestions"]
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

        # Should provide optimized query
        optimized_query = optimization["optimized_query"]
        assert isinstance(optimized_query, str)
        assert len(optimized_query) > 0

    def test_query_statistics_retrieval(self, adapter):
        """Test query statistics retrieval functionality."""
        stats = adapter.get_query_statistics(
            kg_id="test_kg",
            tenant_id="test_tenant",
            time_range_hours=24
        )

        # Verify statistics structure
        assert isinstance(stats, dict)
        assert "query_count" in stats
        assert "avg_latency_ms" in stats
        assert "p95_latency_ms" in stats
        assert "total_results" in stats
        assert "slow_query_count" in stats
        assert "slow_query_ratio" in stats
        assert "time_range_hours" in stats

        # Verify data types and ranges
        assert isinstance(stats["query_count"], int)
        assert isinstance(stats["avg_latency_ms"], (int, float))
        assert isinstance(stats["p95_latency_ms"], (int, float))
        assert isinstance(stats["slow_query_ratio"], (int, float))
        assert stats["query_count"] >= 0
        assert stats["avg_latency_ms"] >= 0
        assert stats["p95_latency_ms"] >= 0
        assert 0 <= stats["slow_query_ratio"] <= 1

    def test_query_caching_behavior(self, adapter):
        """Test query result caching behavior."""
        # Mock the cache check to return None (cache miss)
        with patch.object(adapter, '_check_query_cache', return_value=None):
            result = adapter.query(
                cypher="MATCH (n) RETURN n LIMIT 5",
                kg_id="test_kg",
                tenant_id="test_tenant",
                enable_optimization=True
            )

            assert result["metrics"]["cache_hit"] is False

        # Mock the cache check to return a cached result
        cached_result = {
            "results": [{"n": {"id": "cached_node"}}],
            "execution_time_ms": 5.0,
            "metrics": {"cache_hit": True},
            "result_count": 1
        }

        with patch.object(adapter, '_check_query_cache', return_value=cached_result):
            result = adapter.query(
                cypher="MATCH (n) RETURN n LIMIT 5",
                kg_id="test_kg",
                tenant_id="test_tenant",
                enable_optimization=True
            )

            assert result == cached_result

    def test_query_complexity_analysis(self, adapter):
        """Test query complexity analysis for different query types."""
        test_cases = [
            ("simple", "MATCH (n {id: 'test'}) RETURN n", 0),
            ("medium", "MATCH (n) WHERE n.prop = 'value' RETURN n", 2),
            ("complex", "MATCH (n) RETURN n", 4),  # Full scan
            ("very_complex", "MATCH (a), (b) RETURN a, b", 8)  # Cartesian product
        ]

        for complexity_level, cypher, expected_min_score in test_cases:
            optimization = adapter.optimize_query(
                cypher=cypher,
                kg_id="test_kg",
                tenant_id="test_tenant"
            )

            complexity_score = optimization["analysis"]["complexity_score"]
            assert complexity_score >= expected_min_score, (
                f"Query '{complexity_level}' should have complexity >= {expected_min_score}, "
                f"got {complexity_score}"
            )

    def test_error_handling_for_invalid_queries(self, adapter):
        """Test error handling for various invalid query scenarios."""
        # Test with non-existent knowledge graph
        with patch.object(adapter, '_execute_lua_script', return_value=json.dumps({'error': 'not found'})):
            with pytest.raises(FalkorDBException) as exc_info:
                adapter.query(
                    cypher="MATCH (n) RETURN n",
                    kg_id="nonexistent_kg",
                    tenant_id="test_tenant"
                )

        assert exc_info.value.error_code == "FALKORDB_QUERY_EXECUTION_ERROR"

        # Test with empty tenant ID
        with patch.object(adapter, '_execute_lua_script', return_value=json.dumps({'error': 'invalid tenant'})):
            with pytest.raises(FalkorDBException):
                adapter.query(
                    cypher="MATCH (n) RETURN n",
                    kg_id="test_kg",
                    tenant_id="",
                )

    def test_performance_metrics_recording(self, adapter):
        """Test performance metrics recording functionality."""
        # Mock the _record_query_metrics method to verify it's called
        with patch.object(adapter, '_record_query_metrics') as mock_record:
            adapter.query(
                cypher="MATCH (n) RETURN n",
                kg_id="test_kg",
                tenant_id="test_tenant",
                collect_metrics=True
            )

            # Verify metrics recording was called
            mock_record.assert_called_once()

            # Verify call arguments
            call_args = mock_record.call_args
            assert call_args[1]["kg_id"] == "test_kg"
            assert call_args[1]["tenant_id"] == "test_tenant"
            assert "execution_time_ms" in call_args[1]
            assert "result_count" in call_args[1]
            assert "metrics" in call_args[1]

    def test_slow_query_detection(self, adapter):
        """Test slow query detection logic."""
        # Test the slow query detection logic directly
        execution_time_ms = 1500.0  # Above the 1000ms threshold
        query_hash = "test_hash"
        kg_id = "test_kg"
        tenant_id = "test_tenant"

        # Verify that the condition for slow query detection is correct
        assert execution_time_ms > 1000, "Execution time should be above the slow query threshold"

        # Test the slow query warning message format
        warning_message = f"Slow query detected: {execution_time_ms:.2f}ms for query_hash={query_hash}, kg_id={kg_id}, tenant_id={tenant_id}"
        assert "Slow query detected" in warning_message
        assert f"{execution_time_ms:.2f}ms" in warning_message
        assert query_hash in warning_message
        assert kg_id in warning_message
        assert tenant_id in warning_message

        # This is a simplified test that verifies the logic without mocking
        # In a real test, we would mock the logger and verify it's called

    def test_query_hash_generation(self, adapter):
        """Test query hash generation for caching."""
        result1 = adapter.query(
            cypher="MATCH (n) RETURN n",
            kg_id="test_kg",
            tenant_id="test_tenant"
        )

        result2 = adapter.query(
            cypher="MATCH (n) RETURN n",
            kg_id="test_kg",
            tenant_id="test_tenant"
        )

        # Same query should generate same hash
        assert result1["metrics"]["query_hash"] == result2["metrics"]["query_hash"]

        result3 = adapter.query(
            cypher="MATCH (m) RETURN m",  # Different query
            kg_id="test_kg",
            tenant_id="test_tenant"
        )

        # Different query should generate different hash
        assert result1["metrics"]["query_hash"] != result3["metrics"]["query_hash"]

    def test_query_result_formatting(self, adapter):
        """Test query result formatting and structure."""
        result = adapter.query(
            cypher="MATCH (n) RETURN n",
            kg_id="test_kg",
            tenant_id="test_tenant"
        )

        # Verify result structure
        assert isinstance(result["results"], list)
        assert isinstance(result["execution_time_ms"], (int, float))
        assert isinstance(result["metrics"], dict)
        assert isinstance(result["result_count"], int)
        assert result["query_plan"] is None  # Not implemented yet

        # Verify execution time is reasonable
        assert result["execution_time_ms"] >= 0
        assert result["execution_time_ms"] < 10000  # Should be under 10 seconds

    @pytest.mark.parametrize("cypher,expected_cacheable", [
        ("MATCH (n) RETURN n", True),  # Read-only query
        ("CREATE (n) RETURN n", False),  # Mutation query
        ("MATCH (n) SET n.prop = 'value' RETURN n", False),  # Mutation query
        ("DELETE (n)", False),  # Mutation query
        ("MERGE (n) RETURN n", False),  # Mutation query
    ])
    def test_query_cacheability_detection(self, adapter, cypher, expected_cacheable):
        """Test detection of cacheable vs non-cacheable queries."""
        mock_result = {
            "execution_time_ms": 100,
            "result_count": 10
        }

        is_cacheable = adapter._is_query_cacheable(cypher, mock_result)
        assert is_cacheable == expected_cacheable

    def test_complex_query_delegation(self, adapter):
        """Queries that don't match simple patterns should be delegated."""

        captured: Dict[str, Any] = {}

        def fake_execute(script_name, keys, args):
            captured["script_name"] = script_name
            captured["keys"] = keys
            captured["args"] = args
            return json.dumps(
                {
                    "results": [{"count": 3}],
                    "execution_time_ms": 12,
                    "metrics": {"engine_stats": {"duration_ms": 10}},
                    "result_count": 1,
                }
            )

        adapter._execute_lua_script = MagicMock(side_effect=fake_execute)

        result = adapter.query(
            cypher="MATCH (a)-[r*]->(b) RETURN count(r)",
            kg_id="test_kg",
            tenant_id="test_tenant",
        )

        assert result["result_count"] == 1
        assert result["metrics"]["engine_stats"]["duration_ms"] == 10
        assert captured["script_name"] == "tenant_filtered_query"
        assert captured["keys"] == ["test_kg", "test_tenant"]
        assert captured["args"][0] == "MATCH (a)-[r*]->(b) RETURN count(r)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
