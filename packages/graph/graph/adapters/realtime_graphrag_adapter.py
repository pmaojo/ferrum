"""Real-time GraphRAG adapter with streaming updates and live ontology evolution."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from adapters.graphrag_sdk_adapter import GraphRAGSDKAdapter
from application.ports.messaging import MessageBusPort

logger = logging.getLogger(__name__)


@dataclass
class GraphUpdate:
    """Real-time graph update event."""

    kg_id: str
    tenant_id: str
    update_type: str  # "entity_added", "relationship_created", "ontology_updated"
    data: Dict[str, Any]
    timestamp: datetime
    source: str


class RealTimeGraphRAGAdapter:
    """GraphRAG adapter with real-time updates and streaming capabilities."""

    def __init__(
        self,
        base_adapter: GraphRAGSDKAdapter,
        message_bus: MessageBusPort,
        update_interval_seconds: float = 1.0,
    ):
        self.base_adapter = base_adapter
        self.message_bus = message_bus
        self.update_interval = update_interval_seconds
        self.active_streams: Dict[str, bool] = {}
        self.update_handlers: Dict[str, List[Callable]] = {}

    async def stream_query_results(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream query results as they become available."""

        stream_id = f"{tenant_id}_{kg_id}_{hash(question)}"
        self.active_streams[stream_id] = True

        try:
            # Initial query
            initial_result = self.base_adapter.run(
                question=question, kg_id=kg_id, tenant_id=tenant_id, opts=opts
            )

            yield {
                "type": "initial_result",
                "data": initial_result,
                "timestamp": datetime.now().isoformat(),
            }

            # Stream updates
            while self.active_streams.get(stream_id, False):
                await asyncio.sleep(self.update_interval)

                # Check for graph updates that might affect this query
                updates = await self._get_relevant_updates(question, kg_id, tenant_id)

                if updates:
                    # Re-execute query if relevant updates found
                    updated_result = self.base_adapter.run(
                        question=question, kg_id=kg_id, tenant_id=tenant_id, opts=opts
                    )

                    yield {
                        "type": "updated_result",
                        "data": updated_result,
                        "updates": updates,
                        "timestamp": datetime.now().isoformat(),
                    }

        finally:
            self.active_streams.pop(stream_id, None)

    async def live_ontology_evolution(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        document_stream: AsyncGenerator[str, None],
        confidence_threshold: float = 0.8,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Evolve ontology in real-time as new documents arrive."""

        await self._get_current_ontology(kg_id, tenant_id)
        entity_candidates = {}
        relationship_candidates = {}

        async for document in document_stream:
            # Extract entities and relationships from new document
            extractions = await self._extract_from_document(document, kg_id, tenant_id)

            # Update candidates
            for entity in extractions.get("entities", []):
                entity_name = entity["name"]
                if entity_name not in entity_candidates:
                    entity_candidates[entity_name] = []
                entity_candidates[entity_name].append(entity)

            for rel in extractions.get("relationships", []):
                rel_type = rel["type"]
                if rel_type not in relationship_candidates:
                    relationship_candidates[rel_type] = []
                relationship_candidates[rel_type].append(rel)

            # Check if any candidates meet confidence threshold
            new_entities = self._evaluate_entity_candidates(
                entity_candidates, confidence_threshold
            )
            new_relationships = self._evaluate_relationship_candidates(
                relationship_candidates, confidence_threshold
            )

            if new_entities or new_relationships:
                # Propose ontology update
                ontology_update = {
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "new_entities": new_entities,
                    "new_relationships": new_relationships,
                    "confidence_scores": self._calculate_confidence_scores(
                        new_entities,
                        new_relationships,
                        entity_candidates,
                        relationship_candidates,
                    ),
                }

                yield {
                    "type": "ontology_update_proposal",
                    "data": ontology_update,
                    "timestamp": datetime.now().isoformat(),
                }

                # Clear accepted candidates
                for entity in new_entities:
                    entity_candidates.pop(entity["name"], None)
                for rel in new_relationships:
                    relationship_candidates.pop(rel["type"], None)

    async def register_graph_change_handler(
        self, kg_id: str, tenant_id: str, handler: Callable[[GraphUpdate], None]
    ) -> None:
        """Register handler for graph change events."""

        handler_key = f"{tenant_id}_{kg_id}"
        if handler_key not in self.update_handlers:
            self.update_handlers[handler_key] = []

        self.update_handlers[handler_key].append(handler)

        # Subscribe to graph change events
        await self.message_bus.subscribe(
            topic=f"graph.changes.{kg_id}",
            handler=lambda msg: self._handle_graph_change(msg, handler_key),
            tenant_id=tenant_id,
        )

    async def create_intelligent_agent_swarm(
        self,
        *,
        research_topic: str,
        knowledge_graphs: List[str],
        tenant_id: str,
        swarm_size: int = 3,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Create a swarm of intelligent agents for collaborative research."""

        # Define agent roles
        agent_roles = [
            {"name": "explorer", "focus": "finding_new_connections"},
            {"name": "validator", "focus": "fact_checking"},
            {"name": "synthesizer", "focus": "combining_insights"},
        ]

        # Create agents
        agents = []
        for i in range(min(swarm_size, len(agent_roles))):
            role = agent_roles[i % len(agent_roles)]
            agent_id = f"agent_{role['name']}_{i}"

            agents.append(
                {
                    "id": agent_id,
                    "role": role,
                    "assigned_kgs": knowledge_graphs[i::swarm_size],  # Distribute KGs
                    "status": "active",
                }
            )

        yield {
            "type": "swarm_initialized",
            "data": {"agents": agents, "topic": research_topic},
            "timestamp": datetime.now().isoformat(),
        }

        # Coordinate agents
        tasks = []
        for agent in agents:
            task = asyncio.create_task(
                self._run_research_agent(agent, research_topic, tenant_id)
            )
            tasks.append(task)

        # Stream results as they come in
        while tasks:
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                result = await task
                yield {
                    "type": "agent_result",
                    "data": result,
                    "timestamp": datetime.now().isoformat(),
                }

            tasks = list(pending)

            # Add small delay to prevent overwhelming
            await asyncio.sleep(0.1)

    async def _get_relevant_updates(
        self, question: str, kg_id: str, tenant_id: str
    ) -> List[GraphUpdate]:
        """Get graph updates relevant to a specific question."""

        # Extract key entities from question
        await self._extract_entities_from_text(question)

        # Query for recent updates involving these entities
        # This would typically query a change log or event stream
        return []  # Simplified for now

    async def _get_current_ontology(self, kg_id: str, tenant_id: str) -> Dict[str, Any]:
        """Get current ontology for a knowledge graph."""

        # This would typically call the GraphRAG SDK to get ontology
        return {"entities": [], "relationships": []}

    async def _extract_from_document(
        self, document: str, kg_id: str, tenant_id: str
    ) -> Dict[str, Any]:
        """Extract entities and relationships from a document."""

        # Use the base adapter for extraction
        triples = self.base_adapter.index(
            docs=[document], kg_id=f"temp_{kg_id}", tenant_id=tenant_id
        )

        entities = []
        relationships = []

        for triple in triples:
            entities.append(
                {
                    "name": triple.subject,
                    "type": "extracted",
                    "confidence": 0.8,  # Would be calculated properly
                }
            )

            relationships.append(
                {
                    "type": triple.predicate,
                    "source": triple.subject,
                    "target": triple.object,
                    "confidence": 0.8,
                }
            )

        return {"entities": entities, "relationships": relationships}

    def _evaluate_entity_candidates(
        self, candidates: Dict[str, List[Dict[str, Any]]], threshold: float
    ) -> List[Dict[str, Any]]:
        """Evaluate entity candidates against confidence threshold."""

        accepted = []
        for entity_name, instances in candidates.items():
            if len(instances) >= 3:  # Seen in multiple documents
                avg_confidence = sum(
                    inst.get("confidence", 0) for inst in instances
                ) / len(instances)
                if avg_confidence >= threshold:
                    accepted.append(
                        {
                            "name": entity_name,
                            "type": instances[0].get("type", "unknown"),
                            "confidence": avg_confidence,
                            "instances": len(instances),
                        }
                    )

        return accepted

    def _evaluate_relationship_candidates(
        self, candidates: Dict[str, List[Dict[str, Any]]], threshold: float
    ) -> List[Dict[str, Any]]:
        """Evaluate relationship candidates against confidence threshold."""

        accepted = []
        for rel_type, instances in candidates.items():
            if len(instances) >= 2:  # Seen multiple times
                avg_confidence = sum(
                    inst.get("confidence", 0) for inst in instances
                ) / len(instances)
                if avg_confidence >= threshold:
                    accepted.append(
                        {
                            "type": rel_type,
                            "confidence": avg_confidence,
                            "instances": len(instances),
                        }
                    )

        return accepted

    def _calculate_confidence_scores(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        entity_candidates: Dict[str, List[Dict[str, Any]]],
        rel_candidates: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, float]:
        """Calculate confidence scores for ontology updates."""

        scores = {}

        for entity in entities:
            entity_candidates.get(entity["name"], [])
            scores[f"entity_{entity['name']}"] = entity["confidence"]

        for rel in relationships:
            rel_candidates.get(rel["type"], [])
            scores[f"relationship_{rel['type']}"] = rel["confidence"]

        return scores

    async def _extract_entities_from_text(self, text: str) -> List[str]:
        """Extract key entities from text."""

        # Simplified entity extraction
        # In practice, would use NLP libraries or LLM
        words = text.lower().split()
        return [word for word in words if len(word) > 3]

    async def _handle_graph_change(
        self, message: Dict[str, Any], handler_key: str
    ) -> None:
        """Handle graph change event."""

        update = GraphUpdate(
            kg_id=message.get("kg_id"),
            tenant_id=message.get("tenant_id"),
            update_type=message.get("type"),
            data=message.get("data"),
            timestamp=datetime.fromisoformat(message.get("timestamp")),
            source=message.get("source", "unknown"),
        )

        # Notify all handlers
        for handler in self.update_handlers.get(handler_key, []):
            try:
                handler(update)
            except Exception as e:
                logger.error(f"Handler failed for graph update: {e}")

    async def _run_research_agent(
        self, agent: Dict[str, Any], topic: str, tenant_id: str
    ) -> Dict[str, Any]:
        """Run a research agent with specific role and KGs."""

        results = []

        for kg_id in agent["assigned_kgs"]:
            # Tailor query based on agent role
            if agent["role"]["name"] == "explorer":
                query = f"Find unexpected connections related to {topic}"
            elif agent["role"]["name"] == "validator":
                query = f"Verify facts and claims about {topic}"
            else:  # synthesizer
                query = f"Summarize key insights about {topic}"

            try:
                result = self.base_adapter.run(
                    question=query, kg_id=kg_id, tenant_id=tenant_id
                )
                results.append({"kg_id": kg_id, "query": query, "result": result})

            except Exception as e:
                logger.error(f"Agent {agent['id']} failed on KG {kg_id}: {e}")

        return {
            "agent_id": agent["id"],
            "role": agent["role"]["name"],
            "results": results,
            "completion_time": datetime.now().isoformat(),
        }
