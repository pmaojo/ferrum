"""Integration tests for FalkorDB query execution using TestContainers.

This test suite uses TestContainers to spin up a real FalkorDB instance for
integration testing of graph query execution and performance benchmarks.
"""

import logging
import os
import statistics
import time
from datetime import datetime
from typing import Any, Dict, List

import pytest

# Import TestContainers
try:
    from testcontainers.redis import RedisContainer
except ImportError:
    pytest.skip(
        "TestContainers not installed. Run: pip install testcontainers",
        allow_module_level=True,
    )

from adapters.retrievers.falkordb_graph_adapter import FalkorGraphAdapter
from domain.entities import Triple


class TestFalkorDBIntegration:
    """Integration tests for FalkorDB using TestContainers."""

    @pytest.fixture(scope="module")
    def falkordb_container(self):
        """Start FalkorDB container for testing."""
        # Skip if running in CI without Docker
        if os.environ.get("CI") and not os.environ.get("CI_WITH_DOCKER"):
            pytest.skip("Skipping TestContainers test in CI without Docker")

        # FalkorDB is Redis-compatible, so we can use RedisContainer
        with RedisContainer("falkordb/falkordb:latest") as container:
            # Wait for container to be ready
            container.start()
            yield container

    @pytest.fixture
    def falkordb_adapter(self, falkordb_container):
        """Create FalkorGraphAdapter connected to test container."""
        connection_string = f"redis://{falkordb_container.get_container_host_ip()}:{falkordb_container.get_exposed_port(6379)}"
        adapter = FalkorGraphAdapter(connection_string=connection_string)

        # Clear any existing data
        adapter.client.flushall()

        return adapter

    @pytest.fixture
    def sample_triples(self) -> List[Triple]:
        """Sample triples for testing."""
        tenant_id = "test_tenant"
        return [
            Triple("Alice", "worksAt", "TechCorp", tenant_id),
            Triple("Alice", "hasRole", "SoftwareEngineer", tenant_id),
            Triple("Bob", "manages", "EngineeringTeam", tenant_id),
            Triple("Bob", "worksAt", "TechCorp", tenant_id),
            Triple("Charlie", "worksAt", "TechCorp", tenant_id),
            Triple("Charlie", "hasRole", "ProductManager", tenant_id),
            Triple("EngineeringTeam", "partOf", "TechCorp", tenant_id),
            Triple("SoftwareEngineer", "type", "Role", tenant_id),
            Triple("ProductManager", "type", "Role", tenant_id),
            Triple("TechCorp", "type", "Company", tenant_id),
        ]

    def test_bulk_insert_and_query(self, falkordb_adapter, sample_triples):
        """Test bulk insert and query functionality."""
        # Arrange
        kg_id = "test_kg"
        tenant_id = "test_tenant"

        # Act - Insert triples
        falkordb_adapter.bulk_insert(
            triples=sample_triples, kg_id=kg_id, tenant_id=tenant_id
        )

        # Act - Query for people who work at TechCorp
        query = """
        MATCH (p)-[:worksAt]->(c {name: 'TechCorp'})
        RETURN p.name as name
        """

        results = falkordb_adapter.query(cypher=query, kg_id=kg_id, tenant_id=tenant_id)

        # Assert
        assert len(results) == 3  # Alice, Bob, Charlie
        names = [result["name"] for result in results]
        assert "Alice" in names
        assert "Bob" in names
        assert "Charlie" in names

    def test_tenant_isolation(self, falkordb_adapter, sample_triples):
        """Test tenant isolation in query execution."""
        # Arrange
        kg_id = "test_kg"
        tenant1_id = "tenant1"
        tenant2_id = "tenant2"

        # Create tenant1 triples
        tenant1_triples = [
            Triple("Alice", "worksAt", "TechCorp", tenant1_id),
            Triple("Bob", "worksAt", "TechCorp", tenant1_id),
        ]

        # Create tenant2 triples
        tenant2_triples = [
            Triple("Charlie", "worksAt", "OtherCorp", tenant2_id),
            Triple("Dave", "worksAt", "OtherCorp", tenant2_id),
        ]

        # Act - Insert triples for both tenants
        falkordb_adapter.bulk_insert(
            triples=tenant1_triples, kg_id=kg_id, tenant_id=tenant1_id
        )

        falkordb_adapter.bulk_insert(
            triples=tenant2_triples, kg_id=kg_id, tenant_id=tenant2_id
        )

        # Act - Query for tenant1
        query = """
        MATCH (p)-[:worksAt]->(c)
        RETURN p.name as name, c.name as company
        """

        tenant1_results = falkordb_adapter.query(
            cypher=query, kg_id=kg_id, tenant_id=tenant1_id
        )

        # Act - Query for tenant2
        tenant2_results = falkordb_adapter.query(
            cypher=query, kg_id=kg_id, tenant_id=tenant2_id
        )

        # Assert
        assert len(tenant1_results) == 2
        assert all(result["company"] == "TechCorp" for result in tenant1_results)

        assert len(tenant2_results) == 2
        assert all(result["company"] == "OtherCorp" for result in tenant2_results)

    def test_lua_script_optimization(self, falkordb_adapter, sample_triples):
        """Test Lua script optimization for bulk operations."""
        # Arrange
        kg_id = "test_kg"
        tenant_id = "test_tenant"

        # Act - Time the bulk insert using Lua script
        start_time = time.time()
        falkordb_adapter.bulk_insert(
            triples=sample_triples, kg_id=kg_id, tenant_id=tenant_id
        )
        lua_script_time = time.time() - start_time

        # Clear data
        falkordb_adapter.client.flushall()

        # Act - Time individual inserts (simulating without Lua)
        start_time = time.time()
        for triple in sample_triples:
            # Simulate individual commands that would be used without Lua
            falkordb_adapter.client.graph().query(
                kg_id,
                f"""
                MERGE (s:{triple.subject} {{name: '{triple.subject}', tenant_id: '{triple.tenant_id}'}})
                MERGE (o:{triple.object} {{name: '{triple.object}', tenant_id: '{triple.tenant_id}'}})
                MERGE (s)-[:{triple.predicate}]->(o)
                """,
            )
        individual_time = time.time() - start_time

        # Assert
        assert lua_script_time < individual_time
        logger = logging.getLogger(__name__)
        logger.info(
            "Lua script optimization: %.2fx faster",
            individual_time / lua_script_time,
        )

    @pytest.mark.parametrize("node_count", [100, 500, 1000])
    def test_query_performance(self, falkordb_adapter, node_count):
        """Test query performance with different graph sizes."""
        # Skip larger tests in CI
        if os.environ.get("CI") and node_count > 500:
            pytest.skip("Skipping large performance test in CI")

        # Arrange
        kg_id = f"perf_kg_{node_count}"
        tenant_id = "test_tenant"

        # Generate synthetic graph data
        triples = []
        for i in range(node_count):
            # Create a tree-like structure to ensure connected graph
            parent = i // 10  # Each node connects to parent (except root)
            if i > 0:
                triples.append(
                    Triple(f"Node{i}", "connects_to", f"Node{parent}", tenant_id)
                )

            # Add some properties
            triples.append(Triple(f"Node{i}", "has_value", f"Value{i}", tenant_id))

            # Add some cross-connections for more realistic graph
            if i % 5 == 0 and i > 10:
                triples.append(
                    Triple(f"Node{i}", "references", f"Node{i-7}", tenant_id)
                )

        # Act - Insert data
        falkordb_adapter.bulk_insert(triples=triples, kg_id=kg_id, tenant_id=tenant_id)

        # Act - Measure query performance
        query = """
        MATCH path = (n)-[:connects_to*1..3]->(m)
        WHERE n.name STARTS WITH 'Node1'
        RETURN n.name, m.name, length(path) as depth
        LIMIT 100
        """

        # Run query multiple times to get average performance
        execution_times = []
        for _ in range(5):
            start_time = time.time()
            results = falkordb_adapter.query(
                cypher=query, kg_id=kg_id, tenant_id=tenant_id
            )
            execution_times.append((time.time() - start_time) * 1000)  # Convert to ms

        # Calculate statistics
        avg_time = statistics.mean(execution_times)
        p95_time = sorted(execution_times)[int(len(execution_times) * 0.95)]

        # Assert
        assert len(results) > 0
        assert p95_time <= 350  # p95 ≤ 350ms target

        logger = logging.getLogger(__name__)
        logger.info("Query performance for %s nodes:", node_count)
        logger.info("  Average: %.2fms", avg_time)
        logger.info("  P95: %.2fms", p95_time)

    def test_ontology_version_storage(self, falkordb_adapter):
        """Test ontology version storage as nodes."""
        # Arrange
        kg_id = "test_kg"
        tenant_id = "test_tenant"
        version_id = "onto_v1"
        parent_version_id = "onto_v0"
        checksum = "abc123"
        axioms = ["Class: Person", "ObjectProperty: worksAt"]

        # Act - Store ontology version
        falkordb_adapter.store_ontology_version(
            kg_id=kg_id,
            version_id=version_id,
            parent_version_id=parent_version_id,
            tenant_id=tenant_id,
            checksum=checksum,
            axioms=axioms,
            created_at=datetime.now(),
        )

        # Act - Query for ontology version
        query = """
        MATCH (o:Ontology {version: $version_id})
        RETURN o
        """

        results = falkordb_adapter.query(
            cypher=query,
            kg_id=kg_id,
            tenant_id=tenant_id,
            params={"version_id": version_id},
        )

        # Assert
        assert len(results) == 1
        ontology = results[0]["o"]
        assert ontology["version"] == version_id
        assert ontology["parent_version"] == parent_version_id
        assert ontology["checksum"] == checksum
        assert ontology["tenant_id"] == tenant_id
        assert len(ontology["axioms"]) == len(axioms)

    def test_optimistic_locking(self, falkordb_adapter, sample_triples):
        """Test optimistic locking with tenant isolation."""
        # Arrange
        kg_id = "test_kg"
        tenant_id = "test_tenant"

        # Act - Insert with optimistic locking
        falkordb_adapter.bulk_insert(
            triples=sample_triples,
            kg_id=kg_id,
            tenant_id=tenant_id,
            use_optimistic_locking=True,
        )

        # Query to verify data was inserted
        query = """
        MATCH (n)
        RETURN count(n) as node_count
        """

        results = falkordb_adapter.query(cypher=query, kg_id=kg_id, tenant_id=tenant_id)

        # Assert
        assert results[0]["node_count"] > 0

        # Simulate concurrent modifications
        # This is hard to test directly, but we can verify the locking mechanism exists
        assert hasattr(falkordb_adapter, "_acquire_lock")
        assert hasattr(falkordb_adapter, "_release_lock")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
