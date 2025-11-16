"""Integration tests for GraphRAG adapter with performance benchmarks.

This test suite tests the GraphRAG adapter integration with performance benchmarks
for document processing and query execution.
"""

import logging
import os
import statistics
import time
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from adapters.retrievers.graphrag_adapter import GraphRAGAdapter
from domain.entities import Document, Triple


class TestGraphRAGIntegration:
    """Integration tests for GraphRAG adapter."""

    @pytest.fixture
    def graphrag_adapter(self):
        """Create GraphRAG adapter for testing."""
        # Skip if GraphRAG is not installed or configured
        try:
            adapter = GraphRAGAdapter(
                config={
                    "api_key": os.environ.get("GRAPHRAG_API_KEY", "test_key"),
                    "endpoint": os.environ.get(
                        "GRAPHRAG_ENDPOINT", "http://localhost:8000"
                    ),
                    "model": "gpt-4",
                    "embedding_model": "text-embedding-ada-002",
                }
            )
            # Test connection
            if not adapter.is_available() and not os.environ.get("MOCK_GRAPHRAG"):
                pytest.skip("GraphRAG service not available")
            return adapter
        except ImportError:
            pytest.skip("GraphRAG package not installed")

    @pytest.fixture
    def sample_documents(self) -> List[Document]:
        """Sample documents for testing."""
        return [
            Document(
                id="doc1",
                content="""
                TechCorp is a technology company founded in 2010.
                Alice works at TechCorp as a software engineer.
                Bob manages the engineering team at TechCorp.
                Charlie is a product manager at TechCorp.
                The engineering team is part of TechCorp's R&D division.
                """,
                metadata={"source": "company_profile"},
                processed_at=None,
                extraction_status="pending",
                tenant_id="test_tenant",
            ),
            Document(
                id="doc2",
                content="""
                TechCorp's main products include:
                - CloudSuite: A cloud computing platform
                - DataAnalyzer: A data analysis tool
                - SecureConnect: An enterprise security solution

                The CloudSuite product was developed by Alice's team.
                """,
                metadata={"source": "product_catalog"},
                processed_at=None,
                extraction_status="pending",
                tenant_id="test_tenant",
            ),
        ]

    @pytest.mark.skipif(
        not os.environ.get("GRAPHRAG_API_KEY"), reason="Requires GraphRAG API key"
    )
    def test_document_indexing(self, graphrag_adapter, sample_documents):
        """Test document indexing with GraphRAG."""
        # Arrange
        kg_id = "test_kg"
        tenant_id = "test_tenant"
        doc_contents = [doc.content for doc in sample_documents]

        # Act
        triples = graphrag_adapter.index(
            docs=doc_contents, kg_id=kg_id, tenant_id=tenant_id
        )

        # Assert
        assert len(triples) > 0
        for triple in triples:
            assert isinstance(triple, Triple)
            assert triple.tenant_id == tenant_id

        # Verify expected entities are extracted
        subjects = {t.subject for t in triples}
        predicates = {t.predicate for t in triples}
        objects = {t.object for t in triples}

        assert "Alice" in subjects
        assert "TechCorp" in subjects.union(objects)
        assert "worksAt" in predicates or "works_at" in predicates

    @pytest.mark.skipif(
        not os.environ.get("GRAPHRAG_API_KEY"), reason="Requires GraphRAG API key"
    )
    def test_natural_language_query(self, graphrag_adapter, sample_documents):
        """Test natural language query execution."""
        # Arrange
        kg_id = "test_kg"
        tenant_id = "test_tenant"
        doc_contents = [doc.content for doc in sample_documents]

        # Index documents first
        graphrag_adapter.index(docs=doc_contents, kg_id=kg_id, tenant_id=tenant_id)

        # Act
        question = "Who works at TechCorp?"
        result = graphrag_adapter.run(
            question=question, kg_id=kg_id, tenant_id=tenant_id
        )

        # Assert
        assert result is not None
        assert isinstance(result, str)
        assert "Alice" in result
        assert "software engineer" in result.lower()

    @pytest.mark.skipif(
        not os.environ.get("GRAPHRAG_API_KEY"), reason="Requires GraphRAG API key"
    )
    def test_query_with_triple_return(self, graphrag_adapter, sample_documents):
        """Test query with triple return format."""
        # Arrange
        kg_id = "test_kg"
        tenant_id = "test_tenant"
        doc_contents = [doc.content for doc in sample_documents]

        # Index documents first
        graphrag_adapter.index(docs=doc_contents, kg_id=kg_id, tenant_id=tenant_id)

        # Act
        question = "What products does TechCorp have?"
        result = graphrag_adapter.run(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            opts={"return_triples": True},
        )

        # Assert
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(t, Triple) for t in result)

        # Check for product information
        product_triples = [
            t for t in result if "CloudSuite" in t.subject or "CloudSuite" in t.object
        ]
        assert len(product_triples) > 0

    @pytest.mark.skipif(
        not os.environ.get("GRAPHRAG_API_KEY"), reason="Requires GraphRAG API key"
    )
    def test_indexing_performance(self, graphrag_adapter):
        """Test indexing performance with different document sizes."""
        # Arrange
        kg_id = "perf_kg"
        tenant_id = "test_tenant"

        # Generate synthetic documents of different sizes
        small_doc = Document(
            id="small",
            content="TechCorp is a company. Alice works there.",
            metadata={"size": "small"},
            processed_at=None,
            extraction_status="pending",
            tenant_id=tenant_id,
        )

        medium_doc = Document(
            id="medium",
            content="\n".join(
                ["TechCorp is a technology company."] * 10
                + ["Alice works at TechCorp as an engineer."] * 10
            ),
            metadata={"size": "medium"},
            processed_at=None,
            extraction_status="pending",
            tenant_id=tenant_id,
        )

        large_doc = Document(
            id="large",
            content="\n".join(
                ["TechCorp is a global technology company."] * 50
                + ["Alice works at TechCorp as a software engineer."] * 50
            ),
            metadata={"size": "large"},
            processed_at=None,
            extraction_status="pending",
            tenant_id=tenant_id,
        )

        documents = [small_doc, medium_doc, large_doc]

        # Act & Assert
        for doc in documents:
            start_time = time.time()
            triples = graphrag_adapter.index(
                docs=[doc.content], kg_id=f"{kg_id}_{doc.id}", tenant_id=tenant_id
            )
            elapsed_time = time.time() - start_time

            # Assert
            assert len(triples) > 0
            logger = logging.getLogger(__name__)
            logger.info(
                "%s document (%d chars):",
                doc.metadata["size"],
                len(doc.content),
            )
            logger.info("  Processing time: %.2fs", elapsed_time)
            logger.info("  Triples extracted: %d", len(triples))
            logger.info(
                "  Extraction rate: %.2f triples/second",
                len(triples) / elapsed_time,
            )

    @pytest.mark.skipif(
        not os.environ.get("GRAPHRAG_API_KEY"), reason="Requires GraphRAG API key"
    )
    def test_query_performance(self, graphrag_adapter, sample_documents):
        """Test query performance with different complexity levels."""
        # Arrange
        kg_id = "perf_kg_query"
        tenant_id = "test_tenant"
        doc_contents = [doc.content for doc in sample_documents]

        # Index documents first
        graphrag_adapter.index(docs=doc_contents, kg_id=kg_id, tenant_id=tenant_id)

        # Define queries of different complexity
        queries = [
            {"text": "Who is Alice?", "complexity": "simple"},
            {"text": "What products does TechCorp have?", "complexity": "medium"},
            {
                "text": "What is the relationship between Alice, the engineering team, and CloudSuite?",
                "complexity": "complex",
            },
        ]

        # Act & Assert
        for query in queries:
            # Run query multiple times to get average performance
            execution_times = []
            for _ in range(3):
                start_time = time.time()
                result = graphrag_adapter.run(
                    question=query["text"], kg_id=kg_id, tenant_id=tenant_id
                )
                execution_times.append(
                    (time.time() - start_time) * 1000
                )  # Convert to ms

            # Calculate statistics
            avg_time = statistics.mean(execution_times)
            p95_time = sorted(execution_times)[int(len(execution_times) * 0.95)]

            # Assert
            assert result is not None
            assert p95_time <= 350  # p95 ≤ 350ms target

            logger = logging.getLogger(__name__)
            logger.info("%s query:", query["complexity"])
            logger.info("  Average: %.2fms", avg_time)
            logger.info("  P95: %.2fms", p95_time)

    @pytest.mark.skipif(
        os.environ.get("GRAPHRAG_API_KEY"), reason="Using real GraphRAG service"
    )
    def test_with_mock_graphrag(self):
        """Test with mocked GraphRAG service for CI environments."""
        # This test uses mocking to simulate GraphRAG in CI environments
        with patch("adapters.graphrag_adapter.GraphRAGClient") as mock_client:
            # Setup mock responses
            mock_instance = mock_client.return_value
            mock_instance.index.return_value = [
                {"subject": "Alice", "predicate": "worksAt", "object": "TechCorp"},
                {"subject": "Bob", "predicate": "manages", "object": "EngineeringTeam"},
            ]
            mock_instance.query.return_value = (
                "Alice works at TechCorp as a software engineer."
            )

            # Create adapter with mock
            adapter = GraphRAGAdapter(config={"api_key": "mock_key"})

            # Test indexing
            triples = adapter.index(
                docs=["Test document"], kg_id="mock_kg", tenant_id="mock_tenant"
            )

            assert len(triples) == 2
            assert triples[0].subject == "Alice"
            assert triples[0].predicate == "worksAt"
            assert triples[0].object == "TechCorp"

            # Test querying
            result = adapter.run(
                question="Who works at TechCorp?",
                kg_id="mock_kg",
                tenant_id="mock_tenant",
            )

            assert "Alice" in result
            assert "software engineer" in result


if __name__ == "__main__":
    pytest.main(["-v", __file__])
