"""StructRAG adapter implementing the GraphRetrieverPort interface."""

import logging
from typing import Any, Dict, List, Optional, Union

from application.ports import GraphRetrieverPort, TracingPort
from domain.entities import Triple
from domain.services import GraphRAGException
from domain.structrag.structrag_orchestrator import StructRAGOrchestrator

logger = logging.getLogger(__name__)


class StructRAGAdapter(GraphRetrieverPort):
    """StructRAG adapter implementing hybrid information structurization for knowledge-intensive reasoning."""

    def __init__(
        self,
        llm_adapter,
        tracer: Optional[TracingPort] = None,
        storage_path: str = "./structrag_storage",
        max_iterations: int = 3,
    ):
        """Initialize StructRAG adapter.

        Args:
            llm_adapter: LLM adapter instance
            tracer: Optional tracing port
            storage_path: Path for storing structured knowledge
            max_iterations: Maximum iterations for multi-agent loops
        """
        self.llm = llm_adapter
        self.tracer = tracer
        self.orchestrator = StructRAGOrchestrator(
            llm=llm_adapter,
            tracer=tracer,
            storage_path=storage_path,
            max_iterations=max_iterations,
        )

        logger.info("Initialized StructRAG adapter")

    def index(
        self,
        *,
        docs: List[str],
        kg_id: str,
        tenant_id: str,
        ontology_file: Optional[str] = None,
    ) -> List[Triple]:
        """Index documents using StructRAG's multi-agent structurization.

        This method processes documents but doesn't create traditional triples.
        Instead, it creates structured knowledge representations that are stored
        internally and can be queried later.

        Args:
            docs: List of document content strings to process
            kg_id: Knowledge graph identifier for storage context
            tenant_id: Tenant identifier for multi-tenant isolation
            ontology_file: Optional ontology file (not used in StructRAG)

        Returns:
            Empty list (StructRAG doesn't produce traditional triples during indexing)
        """
        try:
            logger.info(
                f"Indexing {len(docs)} documents with StructRAG for tenant {tenant_id}"
            )

            # StructRAG doesn't pre-index documents like traditional GraphRAG
            # Instead, it performs document structurization during query time
            # For compatibility, we store the documents for later use

            data_id = f"{tenant_id}_{kg_id}_indexed"

            # Store documents in chunk format for later structurization
            from pathlib import Path

            storage_path = Path(self.orchestrator.storage_path)
            chunk_kb_path = storage_path / "chunk_kb"
            chunk_kb_path.mkdir(parents=True, exist_ok=True)

            import json

            chunks = []
            for i, doc in enumerate(docs):
                if "\n\n" in doc:
                    title = doc.split("\n\n")[0].strip()
                    content = "\n\n".join(doc.split("\n\n")[1:])
                else:
                    title = f"Document {i+1}"
                    content = doc
                chunks.append(f"{title}: {content}")

            output_path = chunk_kb_path / f"data_{data_id}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)

            logger.info(f"Stored {len(docs)} documents for future StructRAG processing")

            # Return empty list as StructRAG doesn't produce traditional triples
            return []

        except Exception as e:
            logger.error(f"StructRAG indexing failed: {str(e)}", exc_info=True)
            raise GraphRAGException(
                message=f"StructRAG document indexing failed: {str(e)}",
                error_code="STRUCTRAG_INDEXING_FAILED",
                context={
                    "tenant_id": tenant_id,
                    "kg_id": kg_id,
                    "document_count": len(docs),
                },
            ) from e

    def run(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, List[Triple], Dict[str, Any]]:
        """Execute StructRAG query processing with multi-agent structurization.

        Args:
            question: Natural language question
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            opts: Optional parameters including:
                - return_metadata: Whether to return full metadata (default: False)
                - max_iterations: Override max iterations
                - structure_type: Force specific structure type

        Returns:
            Answer string or full result dictionary if return_metadata=True
        """
        try:
            opts = opts or {}

            # Load documents for this kg_id/tenant_id
            documents = self._load_documents(kg_id, tenant_id)
            if not documents:
                logger.warning(
                    f"No documents found for kg_id={kg_id}, tenant_id={tenant_id}"
                )
                return "No documents available for this knowledge graph."

            # Process query using StructRAG orchestrator
            result = self.orchestrator.process_query(
                query=question,
                documents=documents,
                tenant_id=tenant_id,
                kg_id=kg_id,
                opts=opts,
            )

            # Return based on requested format
            if opts.get("return_metadata", False):
                return result
            else:
                return result["answer"]

        except Exception as e:
            logger.error(f"StructRAG query processing failed: {str(e)}", exc_info=True)
            raise GraphRAGException(
                message=f"StructRAG query execution failed: {str(e)}",
                error_code="STRUCTRAG_QUERY_FAILED",
                context={
                    "tenant_id": tenant_id,
                    "kg_id": kg_id,
                    "question": question[:100],
                },
            ) from e

    def translate(
        self,
        *,
        natural_language: str,
        kg_id: str,
        tenant_id: str,
        target_format: str = "cypher",
    ) -> tuple[str, str]:
        """Translate natural language to structured query.

        StructRAG doesn't use traditional graph query languages, so this
        returns a description of the structurization approach.

        Args:
            natural_language: Natural language query
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            target_format: Target query format (ignored in StructRAG)

        Returns:
            Tuple of (query_description, explanation)
        """
        try:
            # Use analysis agent to determine structure type
            from domain.structrag.structrag_orchestrator import AnalysisAgent

            analysis_agent = AnalysisAgent(self.llm, self.tracer)

            # Get basic kb_info
            documents = self._load_documents(kg_id, tenant_id)
            kb_info = "Available documents for structurization."
            if documents:
                titles = []
                for doc in documents:
                    if ":" in doc:
                        titles.append(doc.split(":")[0])
                kb_info = "The titles of the docs are:\n" + "\n".join(set(titles))

            # Analyze query to determine structure type and subqueries
            subqueries, chosen_structure = analysis_agent.analyze(
                query=natural_language,
                kb_info=kb_info,
                data_id=f"{tenant_id}_{kg_id}",
                tenant_id=tenant_id,
            )

            query_description = f"StructRAG {chosen_structure} structurization with subqueries: {subqueries}"
            explanation = (
                f"StructRAG will structure the documents as {chosen_structure} format "
                f"and process the following subqueries: {', '.join(subqueries)}"
            )

            return query_description, explanation

        except Exception as e:
            logger.error(f"StructRAG translation failed: {str(e)}")
            fallback_query = (
                f"StructRAG hybrid structurization for: {natural_language[:50]}..."
            )
            fallback_explanation = f"StructRAG will analyze and structure documents optimally for: {natural_language}"
            return fallback_query, fallback_explanation

    def _load_documents(self, kg_id: str, tenant_id: str) -> List[str]:
        """Load documents from storage."""
        try:
            import json
            from pathlib import Path

            data_id = f"{tenant_id}_{kg_id}_indexed"
            storage_path = Path(self.orchestrator.storage_path)
            chunk_kb_path = storage_path / "chunk_kb" / f"data_{data_id}.json"

            if not chunk_kb_path.exists():
                return []

            with open(chunk_kb_path, "r", encoding="utf-8") as f:
                chunks = json.load(f)

            # Convert back to document format
            documents = []
            for chunk in chunks:
                if ":" in chunk:
                    title, content = chunk.split(":", 1)
                    documents.append(f"{title.strip()}\n\n{content.strip()}")
                else:
                    documents.append(chunk)

            return documents

        except Exception as e:
            logger.error(f"Failed to load documents: {e}")
            return []

    def create_ontology_file(
        self,
        entities: List[str],
        relationships: List[str],
        output_file: str = "ontology.json",
    ) -> str:
        """Create ontology file for StructRAG.

        StructRAG doesn't use traditional ontologies, but this method creates
        a structure type preference file.

        Args:
            entities: List of entity types (mapped to structure preferences)
            relationships: List of relationship types (mapped to structure preferences)
            output_file: Output file path

        Returns:
            Path to created file
        """
        try:
            import json
            from pathlib import Path

            # Map entity/relationship types to structure preferences
            structure_preferences = {
                "chunk": [],
                "graph": [],
                "table": [],
                "algorithm": [],
                "catalogue": [],
            }

            # Heuristic mapping based on entity/relationship names
            for entity in entities:
                entity_lower = entity.lower()
                if any(
                    keyword in entity_lower
                    for keyword in ["process", "step", "method", "procedure"]
                ):
                    structure_preferences["algorithm"].append(entity)
                elif any(
                    keyword in entity_lower
                    for keyword in ["category", "type", "class", "group"]
                ):
                    structure_preferences["catalogue"].append(entity)
                elif any(
                    keyword in entity_lower
                    for keyword in ["data", "value", "number", "count"]
                ):
                    structure_preferences["table"].append(entity)
                else:
                    structure_preferences["graph"].append(entity)

            for relationship in relationships:
                rel_lower = relationship.lower()
                if any(
                    keyword in rel_lower for keyword in ["connects", "relates", "links"]
                ):
                    structure_preferences["graph"].append(relationship)
                elif any(
                    keyword in rel_lower for keyword in ["contains", "includes", "has"]
                ):
                    structure_preferences["catalogue"].append(relationship)
                else:
                    structure_preferences["graph"].append(relationship)

            # Save structure preferences
            output_path = Path(output_file)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(structure_preferences, f, ensure_ascii=False, indent=2)

            logger.info(f"Created StructRAG structure preferences file: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to create StructRAG ontology file: {e}")
            return output_file

    def get_status(self) -> Dict[str, Any]:
        """Get StructRAG adapter status and statistics."""
        try:
            from pathlib import Path

            storage_path = Path(self.orchestrator.storage_path)
            status = {
                "adapter_type": "StructRAG",
                "storage_path": str(storage_path),
                "max_iterations": self.orchestrator.max_iterations,
                "knowledge_bases": {},
            }

            # Count files in each knowledge base
            kb_types = ["chunk", "graph", "table", "algorithm", "catalogue"]
            for kb_type in kb_types:
                kb_path = storage_path / f"{kb_type}_kb"
                if kb_path.exists():
                    file_count = len(list(kb_path.glob("*.json")))
                    status["knowledge_bases"][kb_type] = file_count
                else:
                    status["knowledge_bases"][kb_type] = 0

            return status

        except Exception as e:
            logger.error(f"Failed to get StructRAG status: {e}")
            return {
                "adapter_type": "StructRAG",
                "error": str(e),
            }

    def clear_storage(
        self, *, kg_id: Optional[str] = None, tenant_id: Optional[str] = None
    ):
        """Clear StructRAG storage."""
        try:
            if kg_id and tenant_id:
                data_id = f"{tenant_id}_{kg_id}_indexed"
                self.orchestrator.clear_storage(data_id=data_id)
            else:
                self.orchestrator.clear_storage()

            logger.info("StructRAG storage cleared")

        except Exception as e:
            logger.error(f"Failed to clear StructRAG storage: {e}")
