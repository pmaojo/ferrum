"""Unit tests for ExportKnowledgeGraphUseCase."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from domain.entities import KnowledgeGraph, ScientificDomain
from application.exceptions import ValidationError, NotFoundError, AuthorizationError, ApplicationError
from application.use_cases.knowledge_graph.export_knowledge_graph_use_case import (
    ExportKnowledgeGraphUseCase,
    ExportKnowledgeGraphRequest,
    ExportKnowledgeGraphResponse,
    ExportFormat
)


class TestExportKnowledgeGraphUseCase:
    """Test cases for ExportKnowledgeGraphUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.kg_repository = Mock()
        self.graph_export_adapter = Mock()
        self.authorization_service = Mock()
        self.tracer = Mock()

        # Mock tracer span
        self.mock_span = Mock()
        self.tracer.start_span.return_value.__enter__ = Mock(return_value=self.mock_span)
        self.tracer.start_span.return_value.__exit__ = Mock(return_value=None)

        self.use_case = ExportKnowledgeGraphUseCase(
            kg_repository=self.kg_repository,
            graph_export_adapter=self.graph_export_adapter,
            authorization_service=self.authorization_service,
            tracer=self.tracer
        )

        # Create a sample knowledge graph
        self.sample_kg = KnowledgeGraph.create(
            name="Test KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123"
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_rdf_turtle_export(self):
        """Test successful RDF Turtle export."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.RDF_TURTLE,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        expected_rdf = """@prefix ex: <http://example.org/> .
ex:subject1 ex:predicate1 ex:object1 .
ex:subject2 ex:predicate2 ex:object2 ."""

        # Mock repository and adapter responses
        self.kg_repository.get_by_id.return_value = self.sample_kg
        self.graph_export_adapter.export_to_rdf.return_value = expected_rdf

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.exported_data == expected_rdf
        assert response.format == "rdf_turtle"
        assert response.size_bytes == len(expected_rdf.encode('utf-8'))

        # Verify calls
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-123",
            resource_id="kg-123",
            action="read"
        )
        self.kg_repository.get_by_id.assert_called_once_with("kg-123", "tenant-123")
        self.graph_export_adapter.export_to_rdf.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123",
            format="turtle"
        )

        # Verify metrics
        self.tracer.record_metric.assert_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_rdf_xml_export(self):
        """Test successful RDF XML export."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.RDF_XML,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        expected_rdf = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="http://example.org/subject1">
    <ex:predicate1 xmlns:ex="http://example.org/">object1</ex:predicate1>
  </rdf:Description>
</rdf:RDF>"""

        # Mock repository and adapter responses
        self.kg_repository.get_by_id.return_value = self.sample_kg
        self.graph_export_adapter.export_to_rdf.return_value = expected_rdf

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.exported_data == expected_rdf
        assert response.format == "rdf_xml"

        # Verify adapter call
        self.graph_export_adapter.export_to_rdf.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123",
            format="xml"
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_rdf_n_triples_export(self):
        """Test successful RDF N-Triples export."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.RDF_N_TRIPLES,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        expected_rdf = """<http://example.org/subject1> <http://example.org/predicate1> <http://example.org/object1> .
<http://example.org/subject2> <http://example.org/predicate2> <http://example.org/object2> ."""

        # Mock repository and adapter responses
        self.kg_repository.get_by_id.return_value = self.sample_kg
        self.graph_export_adapter.export_to_rdf.return_value = expected_rdf

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.exported_data == expected_rdf
        assert response.format == "rdf_n_triples"

        # Verify adapter call
        self.graph_export_adapter.export_to_rdf.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123",
            format="n-triples"
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_rdf_json_ld_export(self):
        """Test successful RDF JSON-LD export."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.RDF_JSON_LD,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        expected_rdf = """{
  "@context": {
    "ex": "http://example.org/"
  },
  "@graph": [
    {
      "@id": "ex:subject1",
      "ex:predicate1": "object1"
    }
  ]
}"""

        # Mock repository and adapter responses
        self.kg_repository.get_by_id.return_value = self.sample_kg
        self.graph_export_adapter.export_to_rdf.return_value = expected_rdf

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.exported_data == expected_rdf
        assert response.format == "rdf_json_ld"

        # Verify adapter call
        self.graph_export_adapter.export_to_rdf.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123",
            format="json-ld"
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_owl_manchester_export(self):
        """Test successful OWL Manchester export."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.OWL_MANCHESTER,
            ontology_version_id="onto-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        expected_owl = """Prefix: ex: <http://example.org/>

Class: ex:Person
Class: ex:Animal

Individual: ex:john
  Types: ex:Person"""

        # Mock repository and adapter responses
        self.kg_repository.get_by_id.return_value = self.sample_kg
        self.graph_export_adapter.export_to_owl.return_value = expected_owl

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.exported_data == expected_owl
        assert response.format == "owl_manchester"

        # Verify adapter call
        self.graph_export_adapter.export_to_owl.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123",
            ontology_version_id="onto-123",
            format="manchester"
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_owl_xml_export(self):
        """Test successful OWL XML export."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.OWL_XML,
            ontology_version_id="onto-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        expected_owl = """<?xml version="1.0"?>
<Ontology xmlns="http://www.w3.org/2002/07/owl#">
  <Declaration>
    <Class IRI="http://example.org/Person"/>
  </Declaration>
</Ontology>"""

        # Mock repository and adapter responses
        self.kg_repository.get_by_id.return_value = self.sample_kg
        self.graph_export_adapter.export_to_owl.return_value = expected_owl

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.exported_data == expected_owl
        assert response.format == "owl_xml"

        # Verify adapter call
        self.graph_export_adapter.export_to_owl.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123",
            ontology_version_id="onto-123",
            format="xml"
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_owl_functional_export(self):
        """Test successful OWL Functional export."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.OWL_FUNCTIONAL,
            ontology_version_id="onto-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        expected_owl = """Prefix(:=<http://example.org/>)
Declaration(Class(:Person))
Declaration(Class(:Animal))
ClassAssertion(:Person :john)"""

        # Mock repository and adapter responses
        self.kg_repository.get_by_id.return_value = self.sample_kg
        self.graph_export_adapter.export_to_owl.return_value = expected_owl

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.exported_data == expected_owl
        assert response.format == "owl_functional"

        # Verify adapter call
        self.graph_export_adapter.export_to_owl.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123",
            ontology_version_id="onto-123",
            format="functional"
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_json_export(self):
        """Test successful JSON export."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.JSON,
            include_metadata=True,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        expected_json = """{
  "metadata": {
    "id": "kg-123",
    "name": "Test KG",
    "domain": "biology",
    "node_count": 100,
    "edge_count": 150
  },
  "nodes": [
    {"id": "node1", "type": "Person", "properties": {"name": "John"}}
  ],
  "edges": [
    {"source": "node1", "target": "node2", "type": "knows"}
  ]
}"""

        # Mock repository and adapter responses
        self.kg_repository.get_by_id.return_value = self.sample_kg
        self.graph_export_adapter.export_to_json.return_value = expected_json

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.exported_data == expected_json
        assert response.format == "json"

        # Verify adapter call
        self.graph_export_adapter.export_to_json.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123",
            include_metadata=True
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_cypher_export(self):
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.CYPHER,
            tenant_id="tenant-123",
            user_id="user-123",
        )

        expected_cypher = "CREATE (n)"

        self.kg_repository.get_by_id.return_value = self.sample_kg
        self.graph_export_adapter.export_to_cypher.return_value = expected_cypher

        response = await self.use_case.execute(request)

        assert response.success is True
        assert response.exported_data == expected_cypher
        assert response.format == "cypher"
        self.graph_export_adapter.export_to_cypher.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123",
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_json_export_without_metadata(self):
        """Test JSON export without metadata."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.JSON,
            include_metadata=False,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        expected_json = """{
  "nodes": [
    {"id": "node1", "type": "Person", "properties": {"name": "John"}}
  ],
  "edges": [
    {"source": "node1", "target": "node2", "type": "knows"}
  ]
}"""

        # Mock repository and adapter responses
        self.kg_repository.get_by_id.return_value = self.sample_kg
        self.graph_export_adapter.export_to_json.return_value = expected_json

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.exported_data == expected_json

        # Verify adapter call
        self.graph_export_adapter.export_to_json.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123",
            include_metadata=False
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_kg_id(self):
        """Test validation error when kg_id is empty."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="",
            format=ExportFormat.JSON,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "Knowledge graph ID is required" in str(exc_info.value)
        assert exc_info.value.field == "kg_id"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_tenant_id(self):
        """Test validation error when tenant_id is empty."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.JSON,
            tenant_id="",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "Tenant ID is required" in str(exc_info.value)
        assert exc_info.value.field == "tenant_id"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_user_id(self):
        """Test validation error when user_id is empty."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.JSON,
            tenant_id="tenant-123",
            user_id=""
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "User ID is required" in str(exc_info.value)
        assert exc_info.value.field == "user_id"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_owl_without_ontology_version(self):
        """Test validation error when OWL format is requested without ontology version."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.OWL_MANCHESTER,
            ontology_version_id=None,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "Ontology version ID is required for OWL export formats" in str(exc_info.value)
        assert exc_info.value.field == "ontology_version_id"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_authorization_error(self):
        """Test authorization error when user doesn't have permission."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.JSON,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock authorization service to raise error
        self.authorization_service.check_permission.side_effect = AuthorizationError(
            message="User does not have read permission",
            user_id="user-123",
            resource_id="kg-123",
            required_permission="read"
        )

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "does not have read permission" in response.error_message

        # Verify authorization was checked
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-123",
            resource_id="kg-123",
            action="read"
        )

        # Verify repository was not called
        self.kg_repository.get_by_id.assert_not_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_knowledge_graph_not_found(self):
        """Test error when knowledge graph is not found."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-nonexistent",
            format=ExportFormat.JSON,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository to return None
        self.kg_repository.get_by_id.return_value = None

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "not found" in response.error_message

        # Verify repository was called
        self.kg_repository.get_by_id.assert_called_once_with("kg-nonexistent", "tenant-123")

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_export_adapter_error(self):
        """Test error when export adapter fails."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.JSON,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository response
        self.kg_repository.get_by_id.return_value = self.sample_kg

        # Mock adapter to raise error
        self.graph_export_adapter.export_to_json.side_effect = Exception("Export failed")

        # Act & Assert
        with pytest.raises(ApplicationError) as exc_info:
            await self.use_case.execute(request)

        assert "Export failed for format json" in str(exc_info.value)
        assert exc_info.value.error_code == "KNOWLEDGE_GRAPH_EXPORT_FAILED"

        # Verify error metrics were recorded
        self.tracer.record_metric.assert_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_all_owl_formats_require_ontology_version(self):
        """Test that all OWL formats require ontology version ID."""
        owl_formats = [
            ExportFormat.OWL_MANCHESTER,
            ExportFormat.OWL_XML,
            ExportFormat.OWL_FUNCTIONAL
        ]

        for format in owl_formats:
            # Arrange
            request = ExportKnowledgeGraphRequest(
                kg_id="kg-123",
                format=format,
                ontology_version_id="",  # Empty ontology version
                tenant_id="tenant-123",
                user_id="user-123"
            )

            # Act & Assert
            with pytest.raises(ValidationError) as exc_info:
                await self.use_case.execute(request)

            assert "Ontology version ID is required for OWL export formats" in str(exc_info.value)
            assert exc_info.value.field == "ontology_version_id"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_metrics_recorded_on_success(self):
        """Test that metrics are recorded on successful export."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.JSON,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        expected_json = '{"test": "data"}'

        # Mock repository and adapter responses
        self.kg_repository.get_by_id.return_value = self.sample_kg
        self.graph_export_adapter.export_to_json.return_value = expected_json

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True

        # Verify metrics were recorded
        self.tracer.record_metric.assert_called_with(
            name="knowledge_graph_exported",
            value=1,
            tenant_id="tenant-123",
            format="json",
            size_bytes=len(expected_json.encode('utf-8'))
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_error_metrics_recorded_on_failure(self):
        """Test that error metrics are recorded on export failure."""
        # Arrange
        request = ExportKnowledgeGraphRequest(
            kg_id="kg-123",
            format=ExportFormat.JSON,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository response
        self.kg_repository.get_by_id.return_value = self.sample_kg

        # Mock adapter to raise error
        self.graph_export_adapter.export_to_json.side_effect = Exception("Export failed")

        # Act & Assert
        with pytest.raises(ApplicationError):
            await self.use_case.execute(request)

        # Verify error metrics were recorded
        self.tracer.record_metric.assert_called_with(
            name="knowledge_graph_export_errors",
            value=1,
            tenant_id="tenant-123",
            error_type="ApplicationError",
            format="json"
        )