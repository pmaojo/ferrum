import pytest
from unittest.mock import Mock

from domain.unified_agent_coordinator import (
    UnifiedAgentCoordinator,
    UnifiedAgentRequest,
    AgentSystemType,
    UnifiedAgentResponse,
    HierarchicalCoordinationStrategy,
    CollaborativeCoordinationStrategy,
)
from domain.entities import CoordinationStrategy, JobStatus
from application.ports.messaging import MessageBusPort


class TestUnifiedAgentCoordinator:
    @pytest.fixture
    def coordinator(self) -> UnifiedAgentCoordinator:
        return UnifiedAgentCoordinator(message_bus=Mock(spec=MessageBusPort))

    def test_delegates_to_registered_strategy(self, coordinator: UnifiedAgentCoordinator, monkeypatch: pytest.MonkeyPatch):
        called = {}

        def fake_execute(session_context, _):
            called["session_id"] = session_context["session_id"]
            return "sid"

        monkeypatch.setattr(
            coordinator.strategies[CoordinationStrategy.HIERARCHICAL],
            "execute",
            fake_execute,
        )

        request = UnifiedAgentRequest(
            system_type=AgentSystemType.GRAPHRAG,
            operation="coordinate_query",
            parameters={},
            tenant_id="t1",
            workflow_id="wf1",
        )

        session_id = coordinator.coordinate_unified_workflow(
            workflow_type="demo",
            primary_system=AgentSystemType.GRAPHRAG,
            fallback_systems=[],
            request=request,
            coordination_strategy=CoordinationStrategy.HIERARCHICAL,
        )

        assert session_id == "sid"
        assert called["session_id"].startswith("unified_")

    def test_collaborative_strategy_synthesizes_results(self, coordinator: UnifiedAgentCoordinator, monkeypatch: pytest.MonkeyPatch):
        responses = [
            UnifiedAgentResponse(
                system_type=AgentSystemType.GRAPHRAG,
                operation="op",
                success=True,
                result={"r": 1},
            ),
            UnifiedAgentResponse(
                system_type=AgentSystemType.WORKFLOW,
                operation="op",
                success=True,
                result={"r": 2},
            ),
        ]
        iterator = iter(responses)
        monkeypatch.setattr(coordinator, "_execute_on_system", lambda *args, **kwargs: next(iterator))
        synthesized_called = {}

        def fake_synthesize(resps):
            synthesized_called["called"] = True
            return UnifiedAgentResponse(
                system_type=AgentSystemType.WORKFLOW,
                operation="syn",
                success=True,
                result={"syn": True},
            )

        monkeypatch.setattr(coordinator, "_synthesize_collaborative_results", fake_synthesize)

        request = UnifiedAgentRequest(
            system_type=AgentSystemType.GRAPHRAG,
            operation="op",
            parameters={},
            tenant_id="t1",
            workflow_id="wf1",
        )

        session_id = coordinator.coordinate_unified_workflow(
            workflow_type="demo",
            primary_system=AgentSystemType.GRAPHRAG,
            fallback_systems=[AgentSystemType.WORKFLOW],
            request=request,
            coordination_strategy=CoordinationStrategy.COLLABORATIVE,
        )

        session = coordinator.active_sessions[session_id]
        assert session["status"] == JobStatus.COMPLETED
        assert synthesized_called["called"]
