"""Unit tests for QueryService using mock ports."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from typing import List, Dict, Any, Tuple

from domain.entities import Triple
from domain.services import QueryService, GraphRAGException, QueryExecutionService
from domain.query_translation import QueryTranslationService
from domain.exceptions import ValidationError, QueryProcessingError
from application.ports import (
    GraphRetrieverPort,
    QueryTranslatorPort,
    TracingPort,
    SparqlTranslatorPort,
    ShaclTranslatorPort,
)


class TestQueryService:
    """Test suite for QueryService domain service."""

    @pytest.fixture
    def mock_translator(self) -> Mock:
        """Mock QueryTranslatorPort for testing."""
        mock = Mock(spec=QueryTranslatorPort)
        return mock

    @pytest.fixture
    def mock_retriever(self) -> Mock:
        """Mock GraphRetrieverPort for testing."""
        mock = Mock(spec=GraphRetrieverPort)
        return mock

    @pytest.fixture
    def mock_tracer(self) -> Mock:
        """Mock TracingPort for testing."""
        mock = Mock(spec=TracingPort)
        mock.start_span.return_value = MagicMock()
        return mock

    @pytest.fixture
    def sample_triples(self) -> List[Triple]:
        """Sample triples for testing."""
        return [
            Triple("Alice", "worksAt", "TechCorp", "tenant1"),
            Triple("Alice", "hasRole", "SoftwareEngineer", "tenant1"),
            Triple("Bob", "manages", "EngineeringTeam", "tenant1"),
        ]

    @pytest.fixture
    def query_service(
        self, mock_translator: Mock, mock_retriever: Mock, mock_tracer: Mock
    ) -> QueryService:
        """QueryService instance with mocked dependencies."""
        mock_translator.translate.return_value = ("Q", "ex")
        return QueryService(
            translator=mock_translator, retriever=mock_retriever, tracer=mock_tracer
        )

    def test_successful_text_query_execution(
        self,
        query_service: QueryService,
        mock_translator: Mock,
        mock_retriever: Mock,
        mock_tracer: Mock,
    ):
        """Test successful natural language query with text results.

        Requirements tested:
        - 2.1: Natural language to graph query translation
        - 2.2: Query execution with contextual explanations
        - 2.3: Result formatting and disambiguation
        """
        # Arrange
        question = "Who works at TechCorp?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = (
            "MATCH (p:Person)-[:worksAt]->(c:Company {name: 'TechCorp'}) RETURN p.name",
            "Finding people who work at TechCorp by matching Person nodes connected to Company",
        )

        mock_retriever.run.return_value = "Alice works at TechCorp as a software engineer. Bob manages the engineering team at TechCorp."

        # Act
        result = query_service.execute_natural_language_query(
            question=question, kg_id=kg_id, tenant_id=tenant_id, user_id=user_id
        )

        # Assert
        assert "results" in result
        assert "explanation" in result
        assert "metadata" in result
        assert len(result["results"]) > 0
        assert result["metadata"]["error"] is False
        assert result["metadata"]["result_count"] > 0
        assert "execution_time_ms" in result["metadata"]

        # Verify port interactions
        mock_translator.translate.assert_called_once_with(
            natural_language=question, kg_id=kg_id, tenant_id=tenant_id
        )

        mock_retriever.run.assert_called_once()
        call_args = mock_retriever.run.call_args
        assert call_args[1]["question"] == question
        assert call_args[1]["kg_id"] == kg_id
        assert call_args[1]["tenant_id"] == tenant_id
        assert "opts" in call_args[1]

        # Verify tracing
        mock_tracer.start_span.assert_called_once()
        assert (
            mock_tracer.record_metric.call_count == 2
        )  # execution_time_ms and result_count

    def test_span_closed(self, query_service: QueryService, mock_tracer: Mock):
        """Ensure tracing span is closed."""
        span = MagicMock()
        mock_tracer.start_span.return_value = span

        query_service.execute_natural_language_query(
            question="q",
            kg_id="kg",
            tenant_id="t",
            user_id="u",
        )

        span.end.assert_called_once()

    def test_successful_triple_query_execution(
        self,
        query_service: QueryService,
        mock_translator: Mock,
        mock_retriever: Mock,
        sample_triples: List[Triple],
    ):
        """Test successful query execution with triple results."""
        # Arrange
        question = "What relationships exist for Alice?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = (
            "MATCH (alice:Person {name: 'Alice'})-[r]->(o) RETURN alice, r, o",
            "Finding all relationships for Alice",
        )

        mock_retriever.run.return_value = sample_triples

        # Act
        result = query_service.execute_natural_language_query(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            user_id=user_id,
            query_opts={"return_triples": True},
        )

        # Assert
        assert len(result["results"]) == 3
        for res in result["results"]:
            assert res["type"] == "triple"
            assert "subject" in res
            assert "predicate" in res
            assert "object" in res
            assert "relevance_score" in res

        # Verify first triple formatting
        first_result = result["results"][0]
        assert first_result["subject"] == "Alice"
        assert first_result["predicate"] == "worksAt"
        assert first_result["object"] == "TechCorp"

    def test_query_with_no_results(
        self, query_service: QueryService, mock_translator: Mock, mock_retriever: Mock
    ):
        """Test query execution when no results are found."""
        # Arrange
        question = "Who works at NonExistentCorp?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = (
            "MATCH (p:Person)-[:worksAt]->(c:Company {name: 'NonExistentCorp'}) RETURN p.name",
            "Finding people who work at NonExistentCorp",
        )

        mock_retriever.run.return_value = "No results found"

        # Act
        result = query_service.execute_natural_language_query(
            question=question, kg_id=kg_id, tenant_id=tenant_id, user_id=user_id
        )

        # Assert
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0
        # Check for general suggestions that should be present
        suggestions_text = " ".join(result["suggestions"])
        assert (
            "simpler" in suggestions_text
            or "specific" in suggestions_text
            or "terms" in suggestions_text
        )

    def test_query_parameter_validation(self, query_service: QueryService):
        """Test validation of query parameters."""
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        # Test empty question
        with pytest.raises(QueryProcessingError) as exc:
            query_service.execute_natural_language_query(
                question="",
                kg_id=kg_id,
                tenant_id=tenant_id,
                user_id=user_id,
            )
        assert isinstance(exc.value.__cause__, ValidationError)

        # Test very long question
        long_question = "x" * 10001
        with pytest.raises(QueryProcessingError) as exc:
            query_service.execute_natural_language_query(
                question=long_question,
                kg_id=kg_id,
                tenant_id=tenant_id,
                user_id=user_id,
            )
        assert isinstance(exc.value.__cause__, ValidationError)

        # Test empty kg_id
        with pytest.raises(QueryProcessingError) as exc:
            query_service.execute_natural_language_query(
                question="Valid question",
                kg_id="",
                tenant_id=tenant_id,
                user_id=user_id,
            )
        assert isinstance(exc.value.__cause__, ValidationError)

        # Test invalid max_results
        with pytest.raises(QueryProcessingError) as exc:
            query_service.execute_natural_language_query(
                question="Valid question",
                kg_id=kg_id,
                tenant_id=tenant_id,
                user_id=user_id,
                max_results=0,
            )
        assert isinstance(exc.value.__cause__, ValidationError)

    def test_translation_failure_with_fallback(
        self, query_service: QueryService, mock_translator: Mock, mock_retriever: Mock
    ):
        """Test query translation failure with fallback mechanism."""
        # Arrange
        question = "Complex query that fails translation"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        # Mock translator to fail all attempts
        mock_translator.translate.side_effect = Exception(
            "Translation service unavailable"
        )
        mock_retriever.run.return_value = "Fallback search results"

        # Act
        result = query_service.execute_natural_language_query(
            question=question, kg_id=kg_id, tenant_id=tenant_id, user_id=user_id
        )

        # Assert
        assert result["metadata"]["error"] is False  # Should succeed with fallback
        assert "Fallback query search" in result["explanation"]
        assert (
            mock_translator.translate.call_count == 3
        )  # 2 retries + 1 initial attempt

    def test_query_execution_failure(
        self,
        query_service: QueryService,
        mock_translator: Mock,
        mock_retriever: Mock,
        mock_tracer: Mock,
    ):
        """Test handling of query execution failures."""
        # Arrange
        question = "Who works at TechCorp?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = ("VALID QUERY", "Valid translation")

        mock_retriever.run.side_effect = Exception("GraphRAG service unavailable")

        # Act & Assert
        with pytest.raises(QueryProcessingError):
            query_service.execute_natural_language_query(
                question=question,
                kg_id=kg_id,
                tenant_id=tenant_id,
                user_id=user_id,
            )

        # Verify error metric was recorded
        error_calls = [
            call
            for call in mock_tracer.record_metric.call_args_list
            if call[1]["name"] == "query.processing_errors"
        ]
        assert len(error_calls) == 1

    def test_query_without_explanation(
        self, query_service: QueryService, mock_translator: Mock, mock_retriever: Mock
    ):
        """Test query execution without explanation."""
        # Arrange
        question = "Who works at TechCorp?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = (
            "MATCH (p:Person)-[:worksAt]->(c:Company) RETURN p.name",
            "Finding people who work at companies",
        )

        mock_retriever.run.return_value = "Alice works at TechCorp"

        # Act
        result = query_service.execute_natural_language_query(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            user_id=user_id,
            include_explanation=False,
        )

        # Assert
        assert "explanation" not in result
        assert "results" in result
        assert "metadata" in result

    def test_custom_query_options(
        self, query_service: QueryService, mock_translator: Mock, mock_retriever: Mock
    ):
        """Test query execution with custom options."""
        # Arrange
        question = "Who works at TechCorp?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"
        custom_opts = {"max_hops": 3, "context_tokens": 8192, "return_triples": True}

        mock_translator.translate.return_value = ("QUERY", "Explanation")
        mock_retriever.run.return_value = "Results"

        # Act
        query_service.execute_natural_language_query(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            user_id=user_id,
            query_opts=custom_opts,
        )

        # Assert
        call_args = mock_retriever.run.call_args
        passed_opts = call_args[1]["opts"]
        assert passed_opts["max_hops"] == 3
        assert passed_opts["context_tokens"] == 8192
        assert passed_opts["return_triples"] is True
        assert passed_opts["include_reasoning"] is True  # Default should be preserved

    def test_service_without_tracer(self, mock_translator: Mock, mock_retriever: Mock):
        """Test service operation without tracing capabilities."""
        # Arrange
        service = QueryService(
            translator=mock_translator,
            retriever=mock_retriever,
            tracer=None,  # No tracer
        )

        question = "Who works at TechCorp?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = ("QUERY", "Explanation")
        mock_retriever.run.return_value = "Alice works at TechCorp"

        # Act
        result = service.execute_natural_language_query(
            question=question, kg_id=kg_id, tenant_id=tenant_id, user_id=user_id
        )

        # Assert
        assert result["metadata"]["error"] is False
        assert len(result["results"]) > 0
        # Should work fine without tracer

    def test_key_term_extraction(self, query_service: QueryService):
        """Test key term extraction from natural language queries."""
        # Test the private method through query suggestions
        question = "What software engineers work at technology companies in California?"

        # Access private method for testing
        key_terms = query_service._extract_key_terms(question)

        # Assert
        assert "software" in key_terms
        assert "engineers" in key_terms
        assert "technology" in key_terms
        assert "companies" in key_terms
        assert (
            "california" in key_terms
        )  # lowercase because extraction converts to lowercase

        # Stop words should be filtered out
        assert "what" not in key_terms
        assert "at" not in key_terms
        assert "in" not in key_terms

    def test_text_result_formatting(
        self, query_service: QueryService, mock_translator: Mock, mock_retriever: Mock
    ):
        """Test formatting of text-based results."""
        # Arrange
        question = "Tell me about TechCorp"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = ("QUERY", "Explanation")
        mock_retriever.run.return_value = "TechCorp is a technology company. It was founded in 2010. The company has 500 employees."

        # Act
        result = query_service.execute_natural_language_query(
            question=question, kg_id=kg_id, tenant_id=tenant_id, user_id=user_id
        )

        # Assert
        assert len(result["results"]) == 3  # Three sentences
        for i, res in enumerate(result["results"]):
            assert res["type"] == "text"
            assert "content" in res
            assert "relevance_score" in res
            assert res["relevance_score"] == 1.0 - (i * 0.1)  # Decreasing relevance

    def test_max_results_limiting(
        self,
        query_service: QueryService,
        mock_translator: Mock,
        mock_retriever: Mock,
        sample_triples: List[Triple],
    ):
        """Test that results are properly limited by max_results parameter."""
        # Arrange
        question = "Show me all relationships"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"
        max_results = 2

        mock_translator.translate.return_value = ("QUERY", "Explanation")
        mock_retriever.run.return_value = sample_triples  # 3 triples

        # Act
        result = query_service.execute_natural_language_query(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            user_id=user_id,
            max_results=max_results,
        )

        # Assert
        assert len(result["results"]) == max_results
        assert result["metadata"]["result_count"] == max_results

    def test_ambiguous_query_detection(
        self, query_service: QueryService, mock_translator: Mock, mock_retriever: Mock
    ):
        """Test detection of ambiguous queries requiring clarification.

        Requirements tested:
        - 2.4: Request clarification for ambiguous queries
        """
        # Arrange - ambiguous query with pronouns
        question = "What does it do?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = ("QUERY", "Explanation")
        mock_retriever.run.return_value = (
            "Some general information about various things."
        )

        # Act
        result = query_service.execute_natural_language_query(
            question=question, kg_id=kg_id, tenant_id=tenant_id, user_id=user_id
        )

        # Assert
        assert "clarification_needed" in result
        assert result["clarification_needed"] is True
        assert "clarification_questions" in result
        assert len(result["clarification_questions"]) > 0

        # Check that clarification mentions the ambiguous term
        clarification_text = " ".join(result["clarification_questions"])
        assert "it" in clarification_text.lower()

    def test_short_vague_query_detection(
        self, query_service: QueryService, mock_translator: Mock, mock_retriever: Mock
    ):
        """Test detection of short, vague queries."""
        # Arrange - very short query
        question = "What?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = ("QUERY", "Explanation")
        mock_retriever.run.return_value = "Some information."

        # Act
        result = query_service.execute_natural_language_query(
            question=question, kg_id=kg_id, tenant_id=tenant_id, user_id=user_id
        )

        # Assert
        assert result["clarification_needed"] is True
        clarification_text = " ".join(result["clarification_questions"])
        assert (
            "brief" in clarification_text.lower()
            or "details" in clarification_text.lower()
        )

    def test_subgraph_extraction_from_triples(
        self,
        query_service: QueryService,
        mock_translator: Mock,
        mock_retriever: Mock,
        sample_triples: List[Triple],
    ):
        """Test subgraph extraction from triple results.

        Requirements tested:
        - 2.3: Highlight relevant subgraph in results
        """
        # Arrange
        question = "What relationships exist for Alice?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = ("QUERY", "Explanation")
        mock_retriever.run.return_value = sample_triples

        # Act
        result = query_service.execute_natural_language_query(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            user_id=user_id,
            include_subgraph=True,
        )

        # Assert
        assert "subgraph" in result
        subgraph = result["subgraph"]
        assert "nodes" in subgraph
        assert "edges" in subgraph
        assert subgraph["type"] == "triple_subgraph"
        assert subgraph["node_count"] > 0
        assert subgraph["edge_count"] > 0

        # Check that all nodes are marked for highlighting
        for node in subgraph["nodes"]:
            assert node["highlight"] is True
            assert "importance" in node

        # Check edge structure
        for edge in subgraph["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "relationship" in edge

    def test_subgraph_extraction_from_text(
        self, query_service: QueryService, mock_translator: Mock, mock_retriever: Mock
    ):
        """Test subgraph extraction from text results."""
        # Arrange
        question = "Tell me about TechCorp and Alice"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = ("QUERY", "Explanation")
        mock_retriever.run.return_value = (
            "Alice works at TechCorp as a Software Engineer. Bob also works there."
        )

        # Act
        result = query_service.execute_natural_language_query(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            user_id=user_id,
            include_subgraph=True,
        )

        # Assert
        assert "subgraph" in result
        subgraph = result["subgraph"]
        assert subgraph["type"] == "text_subgraph"
        assert len(subgraph["nodes"]) > 0

        # Check that entities like Alice, TechCorp, Bob are extracted
        node_ids = [node["id"] for node in subgraph["nodes"]]
        assert "Alice" in node_ids
        assert "TechCorp" in node_ids
        assert "Bob" in node_ids

    def test_subgraph_disabled(
        self,
        query_service: QueryService,
        mock_translator: Mock,
        mock_retriever: Mock,
        sample_triples: List[Triple],
    ):
        """Test that subgraph extraction can be disabled."""
        # Arrange
        question = "What relationships exist?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = ("QUERY", "Explanation")
        mock_retriever.run.return_value = sample_triples

        # Act
        result = query_service.execute_natural_language_query(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            user_id=user_id,
            include_subgraph=False,
        )

        # Assert
        assert "subgraph" not in result

    def test_multiple_question_words_ambiguity(
        self, query_service: QueryService, mock_translator: Mock, mock_retriever: Mock
    ):
        """Test detection of queries with multiple question words."""
        # Arrange
        question = "What, when, and where did Alice work?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = ("QUERY", "Explanation")
        mock_retriever.run.return_value = "Alice worked at various places."

        # Act
        result = query_service.execute_natural_language_query(
            question=question, kg_id=kg_id, tenant_id=tenant_id, user_id=user_id
        )

        # Assert
        assert result["clarification_needed"] is True
        clarification_text = " ".join(result["clarification_questions"])
        assert (
            "multiple aspects" in clarification_text.lower()
            or "one specific" in clarification_text.lower()
        )

    def test_clear_query_no_clarification(
        self, query_service: QueryService, mock_translator: Mock, mock_retriever: Mock
    ):
        """Test that clear, specific queries don't trigger clarification."""
        # Arrange - clear, specific query
        question = "What is Alice's job title at TechCorp?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"

        mock_translator.translate.return_value = ("QUERY", "Explanation")
        mock_retriever.run.return_value = "Alice is a Software Engineer at TechCorp."

        # Act
        result = query_service.execute_natural_language_query(
            question=question, kg_id=kg_id, tenant_id=tenant_id, user_id=user_id
        )

        # Assert
        assert (
            "clarification_needed" not in result
            or result.get("clarification_needed") is False
        )

    def test_ask_graphrag_executes_via_execution_service(
        self,
        mock_translator: Mock,
        mock_retriever: Mock,
    ):
        """ask_graphrag delegates directly to the execution service."""
        execution = Mock(spec=QueryExecutionService)
        service = QueryService(
            translator=mock_translator,
            retriever=mock_retriever,
            execution_service=execution,
        )

        execution.run_query.return_value = "ok"

        result = service.ask_graphrag(
            question="Q",
            kg_id="kg",
            tenant_id="t",
            opts={"foo": 1},
        )

        execution.run_query.assert_called_once_with(
            question="Q",
            kg_id="kg",
            tenant_id="t",
            query_opts={"foo": 1},
        )
        assert result == "ok"

    def test_translate_to_sparql_and_shacl(
        self,
        mock_translator: Mock,
        mock_retriever: Mock,
    ):
        """SPARQL and SHACL translation uses dedicated translators when provided."""
        sparql = Mock(spec=SparqlTranslatorPort)
        shacl = Mock(spec=ShaclTranslatorPort)

        sparql.translate.return_value = ("SPARQL", "ex")
        shacl.translate.return_value = ("SHACL", "ex")

        service = QueryService(
            translator=mock_translator,
            retriever=mock_retriever,
            sparql_translation_service=QueryTranslationService(sparql),
            shacl_translation_service=QueryTranslationService(shacl),
        )

        sp_query, sp_expl = service.translate_to_sparql(
            question="q",
            kg_id="kg",
            tenant_id="t",
        )
        sh_query, sh_expl = service.translate_to_shacl(
            question="q",
            kg_id="kg",
            tenant_id="t",
        )

        sparql.translate.assert_called_once_with(
            natural_language="q", kg_id="kg", tenant_id="t"
        )
        shacl.translate.assert_called_once_with(
            natural_language="q", kg_id="kg", tenant_id="t"
        )

        assert sp_query == "SPARQL"
        assert sh_query == "SHACL"
        assert sp_expl == "ex"
        assert sh_expl == "ex"

    def test_rdf_translation_falls_back_to_default(
        self, mock_translator: Mock, mock_retriever: Mock
    ):
        """Missing RDF translators fall back to default translation."""
        mock_translator.translate.return_value = ("DEFAULT", "expl")
        service = QueryService(
            translator=mock_translator,
            retriever=mock_retriever,
        )

        sp_query, _ = service.translate_to_sparql(
            question="q", kg_id="kg", tenant_id="t"
        )
        sh_query, _ = service.translate_to_shacl(
            question="q", kg_id="kg", tenant_id="t"
        )

        assert sp_query == "DEFAULT"
        assert sh_query == "DEFAULT"


if __name__ == "__main__":
    pytest.main([__file__])
