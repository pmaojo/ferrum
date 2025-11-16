"""Chainlit tool implementation for GraphRAG Ontology Application."""

import logging
import json
from typing import Any, Dict, List, Optional, Union
import os
from pathlib import Path
import tempfile
import asyncio

try:  # Optional dependency
    import chainlit as cl
    from chainlit.playground.config import PlaygroundConfig
    from chainlit.playground.providers.openai import ChatOpenAI
except Exception:  # pragma: no cover - fallback stubs
    from infrastructure.stubs import chainlit as cl

    PlaygroundConfig = object  # type: ignore
    ChatOpenAI = object  # type: ignore

from domain.entities import Triple
from application.ports import (
    GraphRetrieverPort,
    QueryTranslatorPort,
    CrossModalRetrievalPort,
    EmbeddingCachePort,
)
from application.use_cases.multimodal.cross_modal_retrieval_use_case import (
    CrossModalRetrievalUseCase,
    CrossModalRetrievalRequestDTO,
)
from domain.graph_visualizer import GraphVisualizer
from domain.services import QueryService
from domain.exceptions import GraphRAGException
from domain.multimodal_response_generator import MultimodalResponseGenerator
from ui_adapters.chainlit.graph_visualization import ChainlitGraphVisualizer

# Configure logging
logger = logging.getLogger(__name__)


class ChainlitGraphRAGAdapter:
    """Chainlit adapter for GraphRAG Ontology Application.

    This adapter provides a Chainlit interface for interacting with the GraphRAG
    Ontology Application, including natural language queries and visualization.
    """

    def __init__(
        self,
        query_service: QueryService,
        graph_retriever: GraphRetrieverPort,
        query_translator: QueryTranslatorPort,
        graph_visualizer: GraphVisualizer,
        response_generator: MultimodalResponseGenerator,
        cross_modal_port: Optional[CrossModalRetrievalPort] = None,
        embedding_cache_port: Optional[EmbeddingCachePort] = None,
        default_kg_id: str = "default",
        default_tenant_id: str = "default",
        streaming_enabled: bool = True,
        interactive_mode: bool = True,
    ):
        """Initialize Chainlit GraphRAG adapter.

        Args:
            query_service: Domain service for query processing
            graph_retriever: Port for GraphRAG operations
            query_translator: Port for query translation
            graph_visualizer: Service for graph visualization
            default_kg_id: Default knowledge graph ID
            default_tenant_id: Default tenant ID
            streaming_enabled: Flag to enable real-time streaming
            interactive_mode: Flag to enable interactive exploration
        """
        self.query_service = query_service
        self.graph_retriever = graph_retriever
        self.query_translator = query_translator
        self.graph_visualizer = graph_visualizer
        self.response_generator = response_generator
        self.cross_modal_use_case = None
        if cross_modal_port:
            self.cross_modal_use_case = CrossModalRetrievalUseCase(
                retrieval_port=cross_modal_port,
                embedding_cache_port=embedding_cache_port or cross_modal_port,  # type: ignore[arg-type]
            )
        self.default_kg_id = default_kg_id
        self.default_tenant_id = default_tenant_id
        self.streaming_enabled = streaming_enabled
        self.interactive_mode = interactive_mode

        # Initialize visualization component
        self.chainlit_visualizer = ChainlitGraphVisualizer(
            graph_visualizer, cl_module=cl
        )

        # Initialize streaming components
        if streaming_enabled:
            self.stream_manager = GraphStreamManager()
            self.websocket_clients = set()

        # Register Chainlit tool
        self._register_tool()

    @cl.action_callback("explore_entity")
    async def explore_entity_callback(self, action: cl.Action):
        """Interactive entity exploration with real-time updates."""
        entity_id = action.value

        try:
            # Get entity details and relationships
            entity_data = await self.graph_retriever.get_entity_details(
                entity_id=entity_id, include_relationships=True, depth=2
            )

            # Create interactive visualization
            viz_data = await self.graph_visualizer.create_interactive_subgraph(
                center_entity=entity_id, max_nodes=50
            )

            # Send real-time update
            await cl.Message(
                content=f"🔍 **Entity Analysis: {entity_data['name']}**\n\n"
                f"**Type:** {entity_data['type']}\n"
                f"**Relationships:** {len(entity_data['relationships'])}\n"
                f"**Centrality Score:** {entity_data.get('centrality', 'N/A')}",
                elements=[
                    cl.Plotly(
                        name="entity_graph",
                        figure=viz_data["plotly_figure"],
                        display="inline",
                    )
                ],
            ).send()

            # Add exploration actions
            actions = []
            for rel in entity_data["relationships"][:5]:  # Top 5 relationships
                actions.append(
                    cl.Action(
                        name="explore_entity",
                        value=rel["target_id"],
                        label=f"Explore {rel['target_name']} ({rel['relationship_type']})",
                    )
                )

            if actions:
                await cl.Message(
                    content="🎯 **Continue exploring:**", actions=actions
                ).send()

        except Exception as e:
            await cl.Message(content=f"❌ Error exploring entity: {str(e)}").send()

    @cl.step(type="tool", name="Multi-Modal Query Processing")
    async def process_multimodal_query(
        self, query: str, files: List[cl.File] = None
    ) -> str:
        """Process queries with text, images, and audio inputs."""
        try:
            processed_inputs = {
                "text": query,
                "images": [],
                "audio": [],
                "documents": [],
            }

            # Process uploaded files
            if files:
                for file in files:
                    file_path = file.path
                    file_type = file.type

                    if file_type.startswith("image/"):
                        # Process image
                        image_embedding = await self.graph_retriever.embed_image(
                            file_path
                        )
                        processed_inputs["images"].append(
                            {
                                "path": file_path,
                                "embedding": image_embedding,
                                "description": await self.graph_retriever.describe_image(
                                    file_path
                                ),
                            }
                        )

                    elif file_type.startswith("audio/"):
                        # Process audio
                        transcription = await self.graph_retriever.transcribe_audio(
                            file_path
                        )
                        processed_inputs["audio"].append(
                            {
                                "path": file_path,
                                "transcription": transcription,
                                "features": await self.graph_retriever.extract_audio_features(
                                    file_path
                                ),
                            }
                        )

                    elif file_type in ["text/plain", "application/pdf"]:
                        # Process document
                        content = await self.graph_retriever.extract_document_content(
                            file_path
                        )
                        processed_inputs["documents"].append(
                            {
                                "path": file_path,
                                "content": content,
                                "entities": await self.graph_retriever.extract_entities(
                                    content
                                ),
                            }
                        )

            # Compose unified response from processed inputs
            response = await self.response_generator.generate(processed_inputs)

            # Create rich response with visualizations
            response_elements = []

            if response.get("graph_data"):
                # Add graph visualization
                viz = await self.graph_visualizer.create_response_visualization(
                    response["graph_data"]
                )
                response_elements.append(
                    cl.Plotly(
                        name="response_graph", figure=viz["figure"], display="inline"
                    )
                )

            if response.get("images"):
                # Add image gallery
                for i, path in enumerate(response["images"]):
                    response_elements.append(
                        cl.Image(name=f"result_image_{i}", path=path, display="inline")
                    )

            # Send comprehensive response
            await cl.Message(
                content=response["text"], elements=response_elements
            ).send()

            return response["text"]

        except Exception as e:
            error_msg = f"Error processing multimodal query: {str(e)}"
            await cl.Message(content=f"❌ {error_msg}").send()
            return error_msg

    async def start_real_time_monitoring(self, kg_id: str, tenant_id: str):
        """Start real-time graph monitoring and updates."""
        if not self.streaming_enabled:
            return

        try:
            # Initialize monitoring
            monitor = GraphMonitor(
                kg_id=kg_id,
                tenant_id=tenant_id,
                update_callback=self.handle_graph_update,
            )

            await monitor.start()

            await cl.Message(
                content="🔄 **Real-time monitoring active**\n"
                "You'll receive live updates when the knowledge graph changes."
            ).send()

        except Exception as e:
            await cl.Message(
                content=f"⚠️ Could not start real-time monitoring: {str(e)}"
            ).send()

    @cl.step(type="tool", name="Cross-Modal Retrieval")
    async def cross_modal_retrieve(
        self, query: str, files: List[cl.File] | None = None
    ) -> str:
        """Retrieve similar items across modalities."""
        if not self.cross_modal_use_case:
            return "Cross-modal retrieval not available"

        image = files[0].path if files else None
        request = CrossModalRetrievalRequestDTO(
            tenant_id=self.default_tenant_id,
            user_id="chainlit_user",
            kg_id=self.default_kg_id,
            text_query=query,
            image_path=image,
        )
        response = await self.cross_modal_use_case.execute(request)
        return f"Found {response.total_results} results"

    async def handle_graph_update(self, update_data: Dict[str, Any]):
        """Handle real-time graph updates."""
        try:
            update_type = update_data["type"]

            if update_type == "node_added":
                await cl.Message(
                    content=f"➕ **New entity added:** {update_data['node']['name']}"
                ).send()

            elif update_type == "relationship_added":
                await cl.Message(
                    content=f"🔗 **New relationship:** {update_data['source']} → {update_data['target']}"
                ).send()

            elif update_type == "community_detected":
                await cl.Message(
                    content=f"👥 **New community detected:** {update_data['community_size']} entities"
                ).send()

        except Exception as e:
            logger.error(f"Error handling graph update: {e}")

    def _register_tool(self) -> None:
        """Register GraphRAG tool with Chainlit."""

        @cl.tool(name="graphrag")
        def graphrag_tool(
            question: str, kg_id: Optional[str] = None, tenant_id: Optional[str] = None
        ) -> str:
            """Query the GraphRAG knowledge graph using natural language.

            Args:
                question: Natural language query
                kg_id: Knowledge graph ID (optional)
                tenant_id: Tenant ID (optional)

            Returns:
                Query results as formatted text
            """
            # Use default values if not provided
            kg_id = kg_id or self.default_kg_id
            tenant_id = tenant_id or self.default_tenant_id

            try:
                # Log query
                logger.info(
                    f"Processing GraphRAG query: '{question}' "
                    f"(kg_id={kg_id}, tenant_id={tenant_id})"
                )

                # Execute query using query service
                result = self.query_service.execute_natural_language_query(
                    question=question,
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    user_id="chainlit_user",  # Could be enhanced with actual user ID
                    include_explanation=True,
                )

                # Generate visualization if results are available
                if result.get("results"):
                    self._generate_visualization(result, question, kg_id, tenant_id)

                # Format response
                response = self._format_response(result, question)

                return response

            except GraphRAGException as e:
                logger.error("Error processing GraphRAG query: %s", e, exc_info=True)
                return f"Error processing query: {e.message}"
            except Exception as e:
                logger.error("Error processing GraphRAG query: %s", e, exc_info=True)
                return f"Error processing query: {str(e)}"

    def _generate_visualization(
        self, result: Dict[str, Any], question: str, kg_id: str, tenant_id: str
    ) -> None:
        """Generate and display graph visualization for query results.

        Args:
            result: Query result dictionary
            question: Original natural language query
            kg_id: Knowledge graph ID
            tenant_id: Tenant ID
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=".html", delete=True):
                pass

            loop = asyncio.get_event_loop()
            coro = self.chainlit_visualizer.visualize_query_results(
                results=result,
                question=question,
                kg_id=kg_id,
                tenant_id=tenant_id,
            )
            if loop.is_running():
                loop.create_task(coro)
            else:
                loop.run_until_complete(coro)

        except Exception as e:
            logger.error(f"Error generating visualization: {str(e)}", exc_info=True)

    # Methods moved to ChainlitGraphVisualizer

    def _format_response(self, result: Dict[str, Any], question: str) -> str:
        """Format query results for Chainlit display.

        Args:
            result: Query result dictionary
            question: Original natural language query

        Returns:
            Formatted response text
        """
        # Extract components
        results = result.get("results", [])
        explanation = result.get("explanation", "")
        metadata = result.get("metadata", {})
        suggestions = result.get("suggestions", [])

        # Format response
        response_parts = [f"## Results for: '{question}'"]

        # Add explanation if available
        if explanation:
            response_parts.append(f"\n### Explanation\n{explanation}")

        # Add results
        response_parts.append("\n### Results")

        if isinstance(results, list):
            # Handle structured results
            if results:
                for i, item in enumerate(results, 1):
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            response_parts.append(f"{i}. {item.get('content', '')}")
                        elif item.get("type") == "triple":
                            subj = item.get("subject", "")
                            pred = item.get("predicate", "")
                            obj = item.get("object", "")
                            response_parts.append(f"{i}. {subj} → {pred} → {obj}")
            else:
                response_parts.append("No results found.")
        elif isinstance(results, str):
            # Handle text results
            response_parts.append(results)

        # Add suggestions if no results
        if suggestions and (not results or (isinstance(results, list) and not results)):
            response_parts.append("\n### Suggestions")
            for suggestion in suggestions:
                response_parts.append(f"- {suggestion}")

        # Add metadata
        if metadata:
            execution_time = metadata.get("execution_time_ms", 0)
            result_count = metadata.get("result_count", 0)
            response_parts.append(
                f"\n*Query executed in {execution_time:.2f}ms with {result_count} results.*"
            )

        return "\n".join(response_parts)


# Chainlit setup hooks
@cl.on_chat_start
async def on_chat_start():
    """Initialize Chainlit chat session."""
    await cl.Message(
        content="Welcome to GraphRAG Ontology Application! Ask me questions about your knowledge graph."
    ).send()


@cl.on_settings_update
async def on_settings_update(settings):
    """Handle settings updates."""
    await cl.Message(content=f"Settings updated: {settings}").send()


class GraphStreamManager:
    """Manages real-time streaming of graph updates."""

    def __init__(self):
        self.clients = set()
        self.queue = asyncio.Queue()

    async def add_client(self, websocket):
        """Add a new client to receive updates."""
        self.clients.add(websocket)
        print(f"Client connected. Total clients: {len(self.clients)}")

    async def remove_client(self, websocket):
        """Remove a client when they disconnect."""
        self.clients.discard(websocket)
        print(f"Client disconnected. Total clients: {len(self.clients)}")

    async def enqueue_update(self, update: Dict[str, Any]):
        """Enqueue a new graph update."""
        await self.queue.put(update)

    async def broadcast_updates(self):
        """Broadcast updates to all connected clients."""
        while True:
            update = await self.queue.get()
            if not self.clients:
                print("No clients connected. Skipping update.")
                continue

            for client in list(self.clients):
                try:
                    await client.send_text(json.dumps(update))
                except Exception as e:
                    print(f"Error sending update to client: {e}")
                    await self.remove_client(client)
