import pytest
from typing import Dict, Any, List

from domain.entities import Triple
from adapters.inmemory_message_bus_adapter import InMemoryMessageBusAdapter
from ui_adapters.autogen.graphrag_tool import GraphRAGToolRegistry, register_with_autogen


class DummyGraphRetriever:
    """Simple retriever for testing."""

    def __init__(self) -> None:
        self.run_calls: List[Dict[str, Any]] = []

    def index(self, *, docs: List[str], kg_id: str, tenant_id: str) -> List[Triple]:
        return [Triple(subject="s", predicate="p", object="o", tenant_id=tenant_id)]

    def run(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Dict[str, Any] | None = None,
    ) -> str:
        self.run_calls.append(
            {
                "question": question,
                "kg_id": kg_id,
                "tenant_id": tenant_id,
                "opts": opts or {},
            }
        )
        return f"answer:{question}"


def test_registered_tools_execute():
    retriever = DummyGraphRetriever()
    message_bus = InMemoryMessageBusAdapter()
    registry = GraphRAGToolRegistry(retriever=retriever, message_bus=message_bus)

    tools = register_with_autogen(registry)

    result = tools["ask_graphrag"](
        question="What is AI?", kg_id="kg1", tenant_id="tenant1"
    )
    assert result == "answer:What is AI?"

    adv_result = tools["research_entity_deeply"](
        entity_name="GPT", kg_id="kg1", tenant_id="tenant1", depth=2, include_related=False
    )
    assert adv_result == "answer:Research entity GPT"

    assert retriever.run_calls[0]["question"] == "What is AI?"
    assert retriever.run_calls[1]["opts"] == {"depth": 2, "include_related": False}
