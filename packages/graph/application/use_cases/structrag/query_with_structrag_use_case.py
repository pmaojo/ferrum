"""Use case for processing queries with StructRAG multi-agent framework."""

import logging
from typing import Any, Dict, List, Optional

from application.ports import LLMPort, TracingPort
from domain.services import GraphRAGException
from domain.structrag.structrag_orchestrator import StructRAGOrchestrator

logger = logging.getLogger(__name__)


class QueryWithStructRAGUseCase:
    """Use case for processing knowledge-intensive queries using StructRAG framework."""

    def __init__(
        self,
        llm: LLMPort,
        tracer: Optional[TracingPort] = None,
        storage_path: str = "./structrag_storage",
    ):
        """Initialize StructRAG query use case.

        Args:
            llm: Language model port
            tracer: Optional tracing port
            storage_path: Path for StructRAG storage
        """
        self.llm = llm
        self.tracer = tracer
        self.orchestrator = StructRAGOrchestrator(
            llm=llm,
            tracer=tracer,
            storage_path=storage_path,
        )

    def execute(
        self,
        *,
        query: str,
        documents: List[str],
        tenant_id: str,
        kg_id: str = "default",
        return_metadata: bool = False,
        structure_type: Optional[str] = None,
        max_iterations: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute StructRAG query processing.

        Args:
            query: Natural language query
            documents: List of documents to process
            tenant_id: Tenant identifier
            kg_id: Knowledge graph identifier
            return_metadata: Whether to return detailed metadata
            structure_type: Force specific structure type (optional)
            max_iterations: Override max iterations (optional)

        Returns:
            Dictionary containing answer and optional metadata

        Raises:
            GraphRAGException: When query processing fails
        """
        if not query.strip():
            raise GraphRAGException(
                message="Query cannot be empty",
                error_code="INVALID_QUERY",
                context={"tenant_id": tenant_id, "kg_id": kg_id},
            )

        if not documents:
            raise GraphRAGException(
                message="No documents provided for processing",
                error_code="NO_DOCUMENTS",
                context={"tenant_id": tenant_id, "kg_id": kg_id},
            )

        try:
            # Prepare options
            opts = {}
            if structure_type:
                opts["structure_type"] = structure_type
            if max_iterations:
                opts["max_iterations"] = max_iterations

            # Process query using StructRAG
            result = self.orchestrator.process_query(
                query=query,
                documents=documents,
                tenant_id=tenant_id,
                kg_id=kg_id,
                opts=opts,
            )

            # Format response based on requested level of detail
            if return_metadata:
                return {
                    "answer": result["answer"],
                    "success": result["success"],
                    "structure_type": result["structure_type"],
                    "subqueries": result["subqueries"],
                    "metadata": result["metadata"],
                    "processing_details": {
                        "document_count": len(documents),
                        "query_length": len(query),
                        "structure_chosen": result["structure_type"],
                    },
                }
            else:
                return {
                    "answer": result["answer"],
                    "success": result["success"],
                    "structure_type": result["structure_type"],
                }

        except GraphRAGException:
            # Re-raise GraphRAG exceptions
            raise
        except Exception as e:
            logger.error(f"StructRAG query processing failed: {str(e)}", exc_info=True)
            raise GraphRAGException(
                message=f"StructRAG query processing failed: {str(e)}",
                error_code="STRUCTRAG_PROCESSING_FAILED",
                context={
                    "tenant_id": tenant_id,
                    "kg_id": kg_id,
                    "query": query[:100],
                    "document_count": len(documents),
                },
            ) from e


class IndexDocumentsWithStructRAGUseCase:
    """Use case for indexing documents with StructRAG (preparation for future queries)."""

    def __init__(
        self,
        llm: LLMPort,
        tracer: Optional[TracingPort] = None,
        storage_path: str = "./structrag_storage",
    ):
        """Initialize StructRAG indexing use case."""
        self.llm = llm
        self.tracer = tracer
        self.orchestrator = StructRAGOrchestrator(
            llm=llm,
            tracer=tracer,
            storage_path=storage_path,
        )

    def execute(
        self,
        *,
        documents: List[str],
        tenant_id: str,
        kg_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Index documents for future StructRAG processing.

        Args:
            documents: List of documents to index
            tenant_id: Tenant identifier
            kg_id: Knowledge graph identifier
            metadata: Optional metadata to store

        Returns:
            Dictionary containing indexing results

        Raises:
            GraphRAGException: When indexing fails
        """
        if not documents:
            raise GraphRAGException(
                message="No documents provided for indexing",
                error_code="NO_DOCUMENTS",
                context={"tenant_id": tenant_id, "kg_id": kg_id},
            )

        try:
            # Store documents in StructRAG storage for future processing
            data_id = f"{tenant_id}_{kg_id}_indexed"

            import json
            from pathlib import Path

            storage_path = Path(self.orchestrator.storage_path)
            chunk_kb_path = storage_path / "chunk_kb"
            chunk_kb_path.mkdir(parents=True, exist_ok=True)

            # Process documents into chunks
            chunks = []
            for i, doc in enumerate(documents):
                if "\n\n" in doc:
                    title = doc.split("\n\n")[0].strip()
                    content = "\n\n".join(doc.split("\n\n")[1:])
                else:
                    title = f"Document {i+1}"
                    content = doc
                chunks.append(f"{title}: {content}")

            # Save chunks
            output_path = chunk_kb_path / f"data_{data_id}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)

            # Save metadata if provided
            if metadata:
                metadata_path = chunk_kb_path / f"metadata_{data_id}.json"
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)

            logger.info(f"Indexed {len(documents)} documents for StructRAG processing")

            return {
                "success": True,
                "document_count": len(documents),
                "chunks_created": len(chunks),
                "data_id": data_id,
                "storage_path": str(output_path),
                "metadata": {
                    "tenant_id": tenant_id,
                    "kg_id": kg_id,
                    "indexed_at": str(Path().cwd()),
                },
            }

        except Exception as e:
            logger.error(f"StructRAG document indexing failed: {str(e)}", exc_info=True)
            raise GraphRAGException(
                message=f"StructRAG document indexing failed: {str(e)}",
                error_code="STRUCTRAG_INDEXING_FAILED",
                context={
                    "tenant_id": tenant_id,
                    "kg_id": kg_id,
                    "document_count": len(documents),
                },
            ) from e
