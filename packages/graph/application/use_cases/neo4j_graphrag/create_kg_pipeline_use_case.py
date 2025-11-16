"""Use case for creating Neo4j GraphRAG pipelines."""

from datetime import datetime

from application.exceptions import ApplicationError, ValidationError
from application.ports.neo4j_graphrag import KGPipelineConfig, Neo4jGraphRAGPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    BaseResponseDTO,
    CreateKGPipelineRequestDTO,
    KGPipelineDTO,
)


class CreateKGPipelineUseCase(BaseUseCase):
    """Use case for creating Neo4j GraphRAG knowledge graph pipelines."""

    def __init__(self, neo4j_graphrag_port: Neo4jGraphRAGPort):
        """Initialize the use case with required ports.

        Args:
            neo4j_graphrag_port: Port for Neo4j GraphRAG operations
        """
        self.neo4j_graphrag_port = neo4j_graphrag_port

    def execute(self, request: CreateKGPipelineRequestDTO) -> BaseResponseDTO:
        """Execute the create KG pipeline use case.

        Args:
            request: Request containing pipeline configuration

        Returns:
            Response containing created pipeline information

        Raises:
            ValidationError: When request validation fails
            ApplicationError: When pipeline creation fails
        """
        start_time = datetime.now()

        try:
            # Validate input
            self._validate_request(request)

            # Create pipeline configuration
            config = KGPipelineConfig(
                node_types=request.node_types,
                relationship_types=request.relationship_types,
                patterns=request.patterns,
                llm_config=request.llm_config,
                embedder_config=request.embedder_config,
                from_pdf=request.from_pdf,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
            )

            # Create pipeline using Neo4j GraphRAG port
            pipeline_id = self.neo4j_graphrag_port.create_kg_pipeline(
                config=config, tenant_id=request.tenant_id
            )

            # Create response DTO
            pipeline_dto = KGPipelineDTO(
                id=pipeline_id,
                name=request.name,
                description=request.description,
                tenant_id=request.tenant_id,
                node_types=request.node_types,
                relationship_types=request.relationship_types,
                patterns=request.patterns,
                llm_config=request.llm_config,
                embedder_config=request.embedder_config,
                from_pdf=request.from_pdf,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                is_active=True,
            )

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            return BaseResponseDTO(
                success=True,
                processing_time_ms=processing_time,
                timestamp=datetime.now(),
            )

        except ValidationError:
            raise
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            raise ApplicationError(
                f"Failed to create KG pipeline: {str(e)}",
                details={"processing_time_ms": processing_time},
            )

    def _validate_request(self, request: CreateKGPipelineRequestDTO) -> None:
        """Validate the create pipeline request.

        Args:
            request: Request to validate

        Raises:
            ValidationError: When validation fails
        """
        if not request.name or not request.name.strip():
            raise ValidationError("Pipeline name is required")

        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError("Tenant ID is required")

        if not request.user_id or not request.user_id.strip():
            raise ValidationError("User ID is required")

        if not request.node_types:
            raise ValidationError("At least one node type is required")

        if not request.relationship_types:
            raise ValidationError("At least one relationship type is required")

        if not request.llm_config:
            raise ValidationError("LLM configuration is required")

        if not request.embedder_config:
            raise ValidationError("Embedder configuration is required")

        if request.chunk_size <= 0:
            raise ValidationError("Chunk size must be positive")

        if request.chunk_overlap < 0:
            raise ValidationError("Chunk overlap cannot be negative")

        if request.chunk_overlap >= request.chunk_size:
            raise ValidationError("Chunk overlap must be less than chunk size")

        # Validate LLM config has required fields
        required_llm_fields = ["model", "temperature", "max_tokens"]
        for field in required_llm_fields:
            if field not in request.llm_config:
                raise ValidationError(
                    f"LLM configuration missing required field: {field}"
                )

        # Validate embedder config has required fields
        required_embedder_fields = ["provider", "model"]
        for field in required_embedder_fields:
            if field not in request.embedder_config:
                raise ValidationError(
                    f"Embedder configuration missing required field: {field}"
                )
