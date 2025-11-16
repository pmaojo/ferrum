
"""StructRAG: Boosting Knowledge Intensive Reasoning via Inference-time Hybrid Information Structurization.

This module implements the StructRAG framework that constructs raw documents into
hybrid structured knowledge formats (graphs, tables, algorithms, catalogues, chunks)
to enhance knowledge-intensive reasoning tasks.

Based on the paper: "StructRAG: Boosting Knowledge Intensive Reasoning of LLMs via 
Inference-time Hybrid Information Structurization" by Li et al., 2025.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

from application.ports import LLMPort, TracingPort
from domain.entities import Triple
from domain.services import GraphRAGException
from domain.utils.tracing import tracing_span

logger = logging.getLogger(__name__)


class StructRAGOrchestrator:
    """Main orchestrator for StructRAG framework implementing multi-agent coordination."""

    def __init__(
        self,
        llm: LLMPort,
        tracer: Optional[TracingPort] = None,
        storage_path: str = "./structrag_storage",
        max_iterations: int = 3,
    ):
        """Initialize StructRAG orchestrator.

        Args:
            llm: Language model port for all agents
            tracer: Optional tracing port for observability
            storage_path: Base path for storing structured knowledge
            max_iterations: Maximum iterations for analysis-construction loop
        """
        self.llm = llm
        self.tracer = tracer
        self.storage_path = Path(storage_path)
        self.max_iterations = max_iterations

        # Initialize storage directories
        self._init_storage_directories()

        # Initialize agents
        self.analysis_agent = AnalysisAgent(llm, tracer)
        self.construction_agent = ConstructionAgent(llm, self.storage_path, tracer)
        self.retrieval_agent = RetrievalAgent(llm, self.storage_path, tracer)
        self.merging_agent = MergingAgent(llm, tracer)

        logger.info(f"Initialized StructRAG orchestrator with storage at {storage_path}")

    def _init_storage_directories(self):
        """Initialize storage directories for different knowledge types."""
        knowledge_types = ["chunk", "graph", "table", "algorithm", "catalogue"]
        for kb_type in knowledge_types:
            kb_path = self.storage_path / f"{kb_type}_kb"
            kb_path.mkdir(parents=True, exist_ok=True)

    def process_query(
        self,
        *,
        query: str,
        documents: List[str],
        tenant_id: str,
        kg_id: str = "default",
        opts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process a query using StructRAG framework.

        Args:
            query: Natural language query
            documents: List of raw documents
            tenant_id: Tenant identifier
            kg_id: Knowledge graph identifier
            opts: Optional parameters

        Returns:
            Dictionary containing answer and metadata
        """
        opts = opts or {}
        data_id = f"{tenant_id}_{kg_id}_{hash(query)}"

        with tracing_span(
            self.tracer,
            name="structrag.process_query",
            tenant_id=tenant_id,
            kg_id=kg_id,
            query_length=len(query),
            document_count=len(documents),
        ):
            try:
                # Extract document titles for knowledge base info
                kb_info = self._extract_kb_info(documents)

                # Phase 1: Analysis-Construction Loop
                subqueries, chosen_structure = self._analysis_construction_loop(
                    query=query,
                    documents=documents,
                    kb_info=kb_info,
                    data_id=data_id,
                    tenant_id=tenant_id,
                )

                # Phase 2: Retrieval-Merging Loop
                answer = self._retrieval_merging_loop(
                    query=query,
                    subqueries=subqueries,
                    chosen_structure=chosen_structure,
                    data_id=data_id,
                    tenant_id=tenant_id,
                )

                # Record success metrics
                if self.tracer:
                    self.tracer.record_metric(
                        name="structrag.query_success",
                        value=1.0,
                        tenant_id=tenant_id,
                        structure_type=chosen_structure,
                    )

                return {
                    "answer": answer,
                    "structure_type": chosen_structure,
                    "subqueries": subqueries,
                    "success": True,
                    "metadata": {
                        "data_id": data_id,
                        "document_count": len(documents),
                        "structure_chosen": chosen_structure,
                    },
                }

            except Exception as e:
                logger.error(f"StructRAG processing failed: {str(e)}", exc_info=True)

                # Record error metrics
                if self.tracer:
                    self.tracer.record_metric(
                        name="structrag.query_error",
                        value=1.0,
                        tenant_id=tenant_id,
                        error_type=type(e).__name__,
                    )

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

    def _extract_kb_info(self, documents: List[str]) -> str:
        """Extract knowledge base information from documents."""
        titles = []
        for doc in documents:
            # Extract title (first line before double newline)
            if "\n\n" in doc:
                title = doc.split("\n\n")[0].strip()
            else:
                # Fallback: use first line
                title = doc.split("\n")[0].strip()[:100]
            titles.append(title)

        return "The titles of the docs are:\n" + "\n".join(set(titles))

    def _analysis_construction_loop(
        self,
        *,
        query: str,
        documents: List[str],
        kb_info: str,
        data_id: str,
        tenant_id: str,
    ) -> Tuple[List[str], str]:
        """Execute analysis-construction loop to determine optimal structure."""
        iteration = 0
        subqueries = []
        chosen_structure = "chunk"  # Default fallback

        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"Analysis-construction iteration {iteration}")

            try:
                # Analysis phase: decompose query and choose structure
                subqueries, chosen_structure = self.analysis_agent.analyze(
                    query=query, kb_info=kb_info, data_id=data_id, tenant_id=tenant_id
                )

                # Construction phase: build structured knowledge
                instruction, kb_info_updated = self.construction_agent.construct(
                    subqueries=subqueries,
                    chosen_structure=chosen_structure,
                    documents=documents,
                    data_id=data_id,
                    tenant_id=tenant_id,
                )

                # Update kb_info for next iteration if needed
                if kb_info_updated:
                    kb_info = kb_info_updated

                # For now, we break after first successful iteration
                # In practice, this could be enhanced with convergence criteria
                break

            except Exception as e:
                logger.warning(f"Analysis-construction iteration {iteration} failed: {e}")
                if iteration >= self.max_iterations:
                    raise

        return subqueries, chosen_structure

    def _retrieval_merging_loop(
        self,
        *,
        query: str,
        subqueries: List[str],
        chosen_structure: str,
        data_id: str,
        tenant_id: str,
    ) -> str:
        """Execute retrieval-merging loop to generate final answer."""
        iteration = 0
        extra_instruction = None
        final_answer = ""

        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"Retrieval-merging iteration {iteration}")

            try:
                # Retrieval phase: extract relevant knowledge
                subknowledges = self.retrieval_agent.retrieve(
                    query=query,
                    subqueries=subqueries,
                    chosen_structure=chosen_structure,
                    data_id=data_id,
                    extra_instruction=extra_instruction,
                    tenant_id=tenant_id,
                )

                # Merging phase: synthesize final answer
                answer, continue_flag, new_extra_instruction = self.merging_agent.merge(
                    query=query,
                    subqueries=subqueries,
                    subknowledges=subknowledges,
                    chosen_structure=chosen_structure,
                    data_id=data_id,
                    tenant_id=tenant_id,
                )

                final_answer = answer

                # Check if we should continue
                if continue_flag != "CONTINUE":
                    break

                extra_instruction = new_extra_instruction

            except Exception as e:
                logger.warning(f"Retrieval-merging iteration {iteration} failed: {e}")
                if iteration >= self.max_iterations:
                    raise

        return final_answer

    def get_structured_knowledge(
        self, *, data_id: str, structure_type: str
    ) -> Optional[List[str]]:
        """Retrieve structured knowledge for inspection."""
        kb_path = self.storage_path / f"{structure_type}_kb" / f"data_{data_id}.json"
        
        if not kb_path.exists():
            return None
            
        try:
            with open(kb_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load structured knowledge: {e}")
            return None

    def clear_storage(self, *, data_id: Optional[str] = None):
        """Clear stored structured knowledge."""
        knowledge_types = ["chunk", "graph", "table", "algorithm", "catalogue"]
        
        if data_id:
            # Clear specific data_id
            for kb_type in knowledge_types:
                kb_file = self.storage_path / f"{kb_type}_kb" / f"data_{data_id}.json"
                if kb_file.exists():
                    kb_file.unlink()
        else:
            # Clear all storage
            for kb_type in knowledge_types:
                kb_dir = self.storage_path / f"{kb_type}_kb"
                if kb_dir.exists():
                    for file in kb_dir.glob("*.json"):
                        file.unlink()


class AnalysisAgent:
    """Agent responsible for query analysis and structure type selection."""

    def __init__(
        self,
        llm: LLMPort,
        tracer: Optional[TracingPort] = None,
        structure_types: Optional[List[str]] = None,
    ):
        """Initialize analysis agent."""
        self.llm = llm
        self.tracer = tracer
        self.structure_types = structure_types or [
            "chunk", "graph", "table", "algorithm", "catalogue"
        ]

    def analyze(
        self, *, query: str, kb_info: str, data_id: str, tenant_id: str
    ) -> Tuple[List[str], str]:
        """Analyze query to determine subqueries and optimal structure type."""
        # First, decompose the query into subqueries
        subqueries = self._decompose_query(
            query=query, kb_info=kb_info, tenant_id=tenant_id
        )

        # Then, route to determine optimal structure type
        chosen_structure = self._route_structure(
            query=query, kb_info=kb_info, tenant_id=tenant_id
        )

        logger.debug(
            f"Analysis complete: {len(subqueries)} subqueries, "
            f"structure: {chosen_structure}"
        )

        return subqueries, chosen_structure

    def _decompose_query(
        self, *, query: str, kb_info: str, tenant_id: str
    ) -> List[str]:
        """Decompose complex query into simpler subqueries."""
        prompt = f"""Given the following query and knowledge base information, decompose the query into simpler subqueries that can be answered independently.

Query: {query}

Knowledge Base Information:
{kb_info}

Please break down this query into 2-5 specific subqueries that together would help answer the main query. Each subquery should be focused and answerable from the available documents.

Output each subquery on a separate line:"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                tenant_id=tenant_id,
                opts={"max_tokens": 512, "temperature": 0.1},
            )

            # Parse subqueries from response
            subqueries = [
                line.strip()
                for line in response.split("\n")
                if line.strip() and not line.strip().startswith(("Query:", "Subqueries:"))
            ]

            # Ensure we have at least one subquery
            if not subqueries:
                subqueries = [query]

            return subqueries[:5]  # Limit to 5 subqueries

        except Exception as e:
            logger.warning(f"Query decomposition failed: {e}, using original query")
            return [query]

    def _route_structure(
        self, *, query: str, kb_info: str, tenant_id: str
    ) -> str:
        """Determine optimal structure type for the query."""
        prompt = f"""Given the following query and knowledge base information, determine the best structure type for organizing and retrieving relevant information.

Query: {query}

Knowledge Base Information:
{kb_info}

Available structure types:
- graph: Best for queries about relationships, connections, networks, dependencies
- table: Best for queries requiring structured data comparison, statistics, tabular information
- algorithm: Best for queries about processes, procedures, step-by-step methods
- catalogue: Best for queries about classifications, hierarchies, taxonomies, lists
- chunk: Best for general queries that don't fit other categories

Choose the most appropriate structure type based on the query's characteristics and respond with just the structure type name (graph, table, algorithm, catalogue, or chunk):"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                tenant_id=tenant_id,
                opts={"max_tokens": 50, "temperature": 0.1},
            )

            # Extract structure type from response
            response_lower = response.strip().lower()
            for structure_type in self.structure_types:
                if structure_type in response_lower:
                    return structure_type

            # Default fallback
            return "chunk"

        except Exception as e:
            logger.warning(f"Structure routing failed: {e}, using default 'chunk'")
            return "chunk"


class ConstructionAgent:
    """Agent responsible for constructing structured knowledge representations."""

    def __init__(
        self,
        llm: LLMPort,
        storage_path: Path,
        tracer: Optional[TracingPort] = None,
    ):
        """Initialize construction agent."""
        self.llm = llm
        self.storage_path = storage_path
        self.tracer = tracer

    def construct(
        self,
        *,
        subqueries: List[str],
        chosen_structure: str,
        documents: List[str],
        data_id: str,
        tenant_id: str,
    ) -> Tuple[str, str]:
        """Construct structured knowledge based on chosen structure type."""
        instruction = self._get_construction_instruction(subqueries, chosen_structure)

        if chosen_structure == "graph":
            kb_info = self._construct_graph(
                instruction=instruction,
                documents=documents,
                data_id=data_id,
                tenant_id=tenant_id,
            )
        elif chosen_structure == "table":
            kb_info = self._construct_table(
                instruction=instruction,
                documents=documents,
                data_id=data_id,
                tenant_id=tenant_id,
            )
        elif chosen_structure == "algorithm":
            kb_info = self._construct_algorithm(
                instruction=instruction,
                documents=documents,
                data_id=data_id,
                tenant_id=tenant_id,
            )
        elif chosen_structure == "catalogue":
            kb_info = self._construct_catalogue(
                instruction=instruction,
                documents=documents,
                data_id=data_id,
                tenant_id=tenant_id,
            )
        else:  # chunk
            kb_info = self._construct_chunk(
                instruction=instruction,
                documents=documents,
                data_id=data_id,
                tenant_id=tenant_id,
            )

        return instruction, kb_info

    def _get_construction_instruction(
        self, subqueries: List[str], chosen_structure: str
    ) -> str:
        """Generate construction instruction based on subqueries and structure type."""
        composed_query = "\n".join(subqueries)

        if chosen_structure == "graph":
            return "Extract entities and relationships to build a knowledge graph structure."
        elif chosen_structure == "table":
            return f"Query is {composed_query}, please extract relevant complete tables from the document based on the attributes and keywords mentioned in the Query."
        elif chosen_structure == "algorithm":
            return f"Query is {composed_query}, please extract relevant algorithms from the document based on the Query."
        elif chosen_structure == "catalogue":
            return f"Query is {composed_query}, please extract relevant catalogues from the document based on the Query."
        else:  # chunk
            return "construct chunk"

    def _split_content_and_title(self, documents: List[str]) -> Tuple[List[Dict], List[str]]:
        """Split documents into title and content pairs."""
        docs = []
        titles = []

        for doc in documents:
            if "\n\n" in doc:
                title = doc.split("\n\n")[0].strip()
                content = "\n\n".join(doc.split("\n\n")[1:])
            else:
                # Fallback: use first 100 chars as title
                title = doc[:100].strip()
                content = doc

            docs.append({"title": title, "document": content})
            titles.append(title)

        return docs, titles

    def _construct_graph(
        self, *, instruction: str, documents: List[str], data_id: str, tenant_id: str
    ) -> str:
        """Construct graph knowledge representation."""
        docs, titles = self._split_content_and_title(documents)
        graphs = []

        for i, doc in enumerate(docs):
            title = doc["title"]
            content = doc["document"]

            prompt = f"""Extract entities and relationships from the following document to create a knowledge graph representation.

Instruction: {instruction}

Document Title: {title}

Document Content:
{content}

Context (Other Document Titles):
{chr(10).join(titles)}

Please extract:
1. Key entities (people, places, concepts, objects)
2. Relationships between entities
3. Important attributes/properties

Format as: Entity1 -> Relationship -> Entity2

Output:"""

            try:
                response = self.llm.generate(
                    prompt=prompt,
                    tenant_id=tenant_id,
                    opts={"max_tokens": 1024, "temperature": 0.2},
                )
                graphs.append(f"{title}: {response}")

            except Exception as e:
                logger.warning(f"Graph construction failed for doc {i}: {e}")
                graphs.append(f"{title}: [Construction failed]")

        # Save to storage
        output_path = self.storage_path / "graph_kb" / f"data_{data_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(graphs, f, ensure_ascii=False, indent=2)

        return f"Constructed {len(graphs)} graph representations"

    def _construct_table(
        self, *, instruction: str, documents: List[str], data_id: str, tenant_id: str
    ) -> str:
        """Construct table knowledge representation."""
        docs, _ = self._split_content_and_title(documents)
        tables = []

        for i, doc in enumerate(docs):
            title = doc["title"]
            content = doc["document"]

            prompt = f"""Extract and structure tabular information from the following document.

Instruction: {instruction}

Document Content:
{content}

Please extract any tabular data, structured information, or data that can be organized into tables. Format as structured tables with headers and rows.

Output:"""

            try:
                response = self.llm.generate(
                    prompt=prompt,
                    tenant_id=tenant_id,
                    opts={"max_tokens": 1024, "temperature": 0.2},
                )
                tables.append(f"{title}: {response}")

            except Exception as e:
                logger.warning(f"Table construction failed for doc {i}: {e}")
                tables.append(f"{title}: [Construction failed]")

        # Save to storage
        output_path = self.storage_path / "table_kb" / f"data_{data_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(tables, f, ensure_ascii=False, indent=2)

        return f"Constructed {len(tables)} table representations"

    def _construct_algorithm(
        self, *, instruction: str, documents: List[str], data_id: str, tenant_id: str
    ) -> str:
        """Construct algorithm knowledge representation."""
        docs, _ = self._split_content_and_title(documents)
        algorithms = []

        for i, doc in enumerate(docs):
            title = doc["title"]
            content = doc["document"]

            prompt = f"""Extract algorithmic information, procedures, and step-by-step processes from the following document.

Instruction: {instruction}

Document Content:
{content}

Please extract:
1. Algorithms and their steps
2. Procedures and workflows
3. Process descriptions
4. Method explanations

Format as structured, step-by-step procedures.

Output:"""

            try:
                response = self.llm.generate(
                    prompt=prompt,
                    tenant_id=tenant_id,
                    opts={"max_tokens": 1024, "temperature": 0.2},
                )
                algorithms.append(f"{title}: {response}")

            except Exception as e:
                logger.warning(f"Algorithm construction failed for doc {i}: {e}")
                algorithms.append(f"{title}: [Construction failed]")

        # Save to storage
        output_path = self.storage_path / "algorithm_kb" / f"data_{data_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(algorithms, f, ensure_ascii=False, indent=2)

        return f"Constructed {len(algorithms)} algorithm representations"

    def _construct_catalogue(
        self, *, instruction: str, documents: List[str], data_id: str, tenant_id: str
    ) -> str:
        """Construct catalogue knowledge representation."""
        docs, _ = self._split_content_and_title(documents)
        catalogues = []

        for i, doc in enumerate(docs):
            title = doc["title"]
            content = doc["document"]

            prompt = f"""Extract categorical and hierarchical information from the following document.

Instruction: {instruction}

Document Content:
{content}

Please extract:
1. Categories and classifications
2. Hierarchical structures
3. Lists and taxonomies
4. Organized groupings

Format as structured lists and hierarchies.

Output:"""

            try:
                response = self.llm.generate(
                    prompt=prompt,
                    tenant_id=tenant_id,
                    opts={"max_tokens": 1024, "temperature": 0.2},
                )
                catalogues.append(f"\n\n{title}: {response}")

            except Exception as e:
                logger.warning(f"Catalogue construction failed for doc {i}: {e}")
                catalogues.append(f"\n\n{title}: [Construction failed]")

        # Save to storage
        output_path = self.storage_path / "catalogue_kb" / f"data_{data_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(catalogues, f, ensure_ascii=False, indent=2)

        return f"Constructed {len(catalogues)} catalogue representations"

    def _construct_chunk(
        self, *, instruction: str, documents: List[str], data_id: str, tenant_id: str
    ) -> str:
        """Construct chunk knowledge representation (simple document storage)."""
        docs, _ = self._split_content_and_title(documents)
        chunks = []

        for doc in docs:
            title = doc["title"]
            content = doc["document"]
            chunks.append(f"{title}: {content}")

        # Save to storage
        output_path = self.storage_path / "chunk_kb" / f"data_{data_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        return f"Constructed {len(chunks)} chunk representations"


class RetrievalAgent:
    """Agent responsible for retrieving relevant structured knowledge."""

    def __init__(
        self,
        llm: LLMPort,
        storage_path: Path,
        tracer: Optional[TracingPort] = None,
    ):
        """Initialize retrieval agent."""
        self.llm = llm
        self.storage_path = storage_path
        self.tracer = tracer

    def retrieve(
        self,
        *,
        query: str,
        subqueries: List[str],
        chosen_structure: str,
        data_id: str,
        extra_instruction: Optional[str] = None,
        tenant_id: str,
    ) -> List[str]:
        """Retrieve relevant knowledge from structured representations."""
        # Apply extra instruction if provided
        if extra_instruction:
            subqueries = [sq + " " + extra_instruction for sq in subqueries]

        if chosen_structure == "chunk":
            return self._retrieve_chunk(query, subqueries, data_id, tenant_id)
        elif chosen_structure == "table":
            return self._retrieve_table(query, subqueries, data_id, tenant_id)
        elif chosen_structure == "graph":
            return self._retrieve_graph(query, subqueries, data_id, tenant_id)
        elif chosen_structure == "algorithm":
            return self._retrieve_algorithm(query, subqueries, data_id, tenant_id)
        elif chosen_structure == "catalogue":
            return self._retrieve_catalogue(query, subqueries, data_id, tenant_id)
        else:
            raise ValueError(f"Unknown structure type: {chosen_structure}")

    def _load_knowledge(self, structure_type: str, data_id: str) -> List[str]:
        """Load structured knowledge from storage."""
        kb_path = self.storage_path / f"{structure_type}_kb" / f"data_{data_id}.json"
        
        if not kb_path.exists():
            logger.warning(f"Knowledge file not found: {kb_path}")
            return []

        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load knowledge from {kb_path}: {e}")
            return []

    def _retrieve_chunk(
        self, query: str, subqueries: List[str], data_id: str, tenant_id: str
    ) -> List[str]:
        """Retrieve from chunk knowledge."""
        chunks = self._load_knowledge("chunk", data_id)
        composed_query = "\n".join(subqueries)
        subknowledges = []

        for chunk in chunks:
            prompt = f"Query:\n{composed_query}\n\nDocument:\n{chunk}\n\nOutput:"
            
            try:
                response = self.llm.generate(
                    prompt=prompt,
                    tenant_id=tenant_id,
                    opts={"max_tokens": 512, "temperature": 0.1},
                )
                title = chunk.split(":")[0] if ":" in chunk else "Document"
                subknowledges.append(f"{title}: {response}")
            except Exception as e:
                logger.warning(f"Chunk retrieval failed: {e}")
                subknowledges.append(f"Retrieval failed: {str(e)}")

        return subknowledges

    def _retrieve_table(
        self, query: str, subqueries: List[str], data_id: str, tenant_id: str
    ) -> List[str]:
        """Retrieve from table knowledge."""
        tables = self._load_knowledge("table", data_id)
        tables_content = ""
        
        for i, table in enumerate(tables):
            tables_content += f"Table {i+1}:\n{table}\n\n"

        subknowledges = []
        for subquery in subqueries:
            prompt = f"Query: {subquery}\n\nTables:\n{tables_content}\n\nExtract relevant information:"
            
            try:
                response = self.llm.generate(
                    prompt=prompt,
                    tenant_id=tenant_id,
                    opts={"max_tokens": 512, "temperature": 0.1},
                )
                subknowledges.append(response)
            except Exception as e:
                logger.warning(f"Table retrieval failed: {e}")
                subknowledges.append(f"Retrieval failed: {str(e)}")

        return subknowledges

    def _retrieve_graph(
        self, query: str, subqueries: List[str], data_id: str, tenant_id: str
    ) -> List[str]:
        """Retrieve from graph knowledge."""
        graphs = self._load_knowledge("graph", data_id)
        graphs_content = "\n\n".join(graphs)

        subknowledges = []
        for subquery in subqueries:
            prompt = f"Query: {subquery}\n\nGraph Knowledge:\n{graphs_content}\n\nExtract relevant information:"
            
            try:
                response = self.llm.generate(
                    prompt=prompt,
                    tenant_id=tenant_id,
                    opts={"max_tokens": 512, "temperature": 0.1},
                )
                subknowledges.append(response)
            except Exception as e:
                logger.warning(f"Graph retrieval failed: {e}")
                subknowledges.append(f"Retrieval failed: {str(e)}")

        return subknowledges

    def _retrieve_algorithm(
        self, query: str, subqueries: List[str], data_id: str, tenant_id: str
    ) -> List[str]:
        """Retrieve from algorithm knowledge."""
        algorithms = self._load_knowledge("algorithm", data_id)
        algorithms_content = "\n\n".join(algorithms)

        subknowledges = []
        for subquery in subqueries:
            prompt = f"Query: {subquery}\n\nAlgorithms:\n{algorithms_content}\n\nExtract relevant information:"
            
            try:
                response = self.llm.generate(
                    prompt=prompt,
                    tenant_id=tenant_id,
                    opts={"max_tokens": 512, "temperature": 0.1},
                )
                subknowledges.append(response)
            except Exception as e:
                logger.warning(f"Algorithm retrieval failed: {e}")
                subknowledges.append(f"Retrieval failed: {str(e)}")

        return subknowledges

    def _retrieve_catalogue(
        self, query: str, subqueries: List[str], data_id: str, tenant_id: str
    ) -> List[str]:
        """Retrieve from catalogue knowledge."""
        catalogues = self._load_knowledge("catalogue", data_id)
        catalogues_content = "\n\n".join(catalogues)

        subknowledges = []
        for subquery in subqueries:
            prompt = f"Query: {subquery}\n\nCatalogues:\n{catalogues_content}\n\nExtract relevant information:"
            
            try:
                response = self.llm.generate(
                    prompt=prompt,
                    tenant_id=tenant_id,
                    opts={"max_tokens": 512, "temperature": 0.1},
                )
                subknowledges.append(response)
            except Exception as e:
                logger.warning(f"Catalogue retrieval failed: {e}")
                subknowledges.append(f"Retrieval failed: {str(e)}")

        return subknowledges


class MergingAgent:
    """Agent responsible for merging retrieved knowledge into final answers."""

    def __init__(
        self,
        llm: LLMPort,
        tracer: Optional[TracingPort] = None,
        use_complex_merging: bool = False,
    ):
        """Initialize merging agent."""
        self.llm = llm
        self.tracer = tracer
        self.use_complex_merging = use_complex_merging

    def merge(
        self,
        *,
        query: str,
        subqueries: List[str],
        subknowledges: List[str],
        chosen_structure: str,
        data_id: str,
        tenant_id: str,
    ) -> Tuple[str, str, str]:
        """Merge retrieved knowledge into final answer."""
        # Organize retrieval results by structure type
        retrieval_sections = {
            "chunk": "",
            "graph": "",
            "table": "",
            "algorithm": "",
            "catalogue": "",
        }

        if chosen_structure == "chunk":
            subknowledges_text = "\n".join(subknowledges)
            retrieval_sections["chunk"] = f"Subquery: {query}\nRetrieval results:\n{subknowledges_text}\n\n"
        elif chosen_structure in ["table", "graph", "algorithm"]:
            for subquery, subknowledge in zip(subqueries, subknowledges):
                retrieval_sections[chosen_structure] += f"Subquery: {subquery}\nRetrieval results:\n{subknowledge}\n\n"
        elif chosen_structure == "catalogue":
            subknowledges_text = "\n".join(subknowledges)
            retrieval_sections["catalogue"] = f"Subquery: {query}\nRetrieval results:\n{subknowledges_text}\n\n"

        if self.use_complex_merging:
            return self._complex_merge(query, retrieval_sections, tenant_id)
        else:
            return self._simple_merge(query, retrieval_sections, tenant_id)

    def _simple_merge(
        self, query: str, retrieval_sections: Dict[str, str], tenant_id: str
    ) -> Tuple[str, str, str]:
        """Simple merging approach - generate final answer directly."""
        instruction = (
            "1. Answer the Question based on retrieval results.\n"
            "2. Find the relevant information from given retrieval results and output as detailed, specific, and lengthy as possible.\n"
            "3. The output must be a coherent and smooth piece of text."
        )

        retrieval_text = "".join(retrieval_sections.values())
        prompt = f"Instruction:\n{instruction}\n\nQuestion:\n{query}\n\nRetrieval:\n{retrieval_text}"

        try:
            answer = self.llm.generate(
                prompt=prompt,
                tenant_id=tenant_id,
                opts={"max_tokens": 1024, "temperature": 0.2},
            )
            return answer, "No", "No"
        except Exception as e:
            logger.error(f"Simple merge failed: {e}")
            return f"Failed to generate answer: {str(e)}", "No", "No"

    def _complex_merge(
        self, query: str, retrieval_sections: Dict[str, str], tenant_id: str
    ) -> Tuple[str, str, str]:
        """Complex merging approach with continuation logic."""
        prompt = f"""Based on the retrieval results from different knowledge structures, provide a comprehensive answer and determine if additional retrieval is needed.

Query: {query}

Retrieval Results:
Chunk: {retrieval_sections['chunk']}
Graph: {retrieval_sections['graph']}
Table: {retrieval_sections['table']}
Algorithm: {retrieval_sections['algorithm']}
Catalogue: {retrieval_sections['catalogue']}

Please provide:
1. A comprehensive answer based on the available information
2. Decision: "CONTINUE" if more information is needed, "COMPLETE" if sufficient
3. New query: If continuing, provide a refined query for additional retrieval

Format your response as JSON:
{{
    "answer": "Your comprehensive answer here",
    "decision": "CONTINUE or COMPLETE",
    "new_query": "Refined query if continuing, otherwise null"
}}"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                tenant_id=tenant_id,
                opts={"max_tokens": 1024, "temperature": 0.2},
            )

            # Parse JSON response
            try:
                result = json.loads(response.strip("```json").strip("```").strip())
                answer = result.get("answer", "No answer provided")
                decision = result.get("decision", "COMPLETE")
                new_query = result.get("new_query", "No")
                
                if "CONTINUE" in decision:
                    decision = "CONTINUE"
                else:
                    decision = "COMPLETE"
                    
                return answer, decision, new_query or "No"
                
            except json.JSONDecodeError:
                # Fallback parsing
                lines = response.split("\n")
                answer = response  # Use full response as answer
                decision = "COMPLETE"
                new_query = "No"
                
                for line in lines:
                    if "CONTINUE" in line.upper():
                        decision = "CONTINUE"
                        
                return answer, decision, new_query

        except Exception as e:
            logger.error(f"Complex merge failed: {e}")
            return f"Failed to generate answer: {str(e)}", "COMPLETE", "No"
