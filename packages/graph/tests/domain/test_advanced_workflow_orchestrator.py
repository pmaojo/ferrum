import pytest
from unittest.mock import Mock, call

from domain.advanced_workflow_orchestrator import (
    AdvancedWorkflowOrchestrator,
    WorkflowDefinition,
    WorkflowPattern,
    WorkflowStep,
)
from domain.agent_coordinator import AgentCoordinator
from application.ports import TracingPort
from application.ports.messaging import MessageBusPort
from domain.entities import JobStatus


class TestAdvancedWorkflowOrchestrator:
    @pytest.fixture
    def mock_agent_coordinator(self) -> Mock:
        return Mock(spec=AgentCoordinator)

    @pytest.fixture
    def mock_message_bus(self) -> Mock:
        return Mock(spec=MessageBusPort)

    @pytest.fixture
    def mock_tracer(self) -> Mock:
        return Mock(spec=TracingPort)

    @pytest.fixture
    def orchestrator(
        self,
        mock_agent_coordinator: Mock,
        mock_message_bus: Mock,
        mock_tracer: Mock,
    ) -> AdvancedWorkflowOrchestrator:
        return AdvancedWorkflowOrchestrator(
            agent_coordinator=mock_agent_coordinator,
            message_bus=mock_message_bus,
            tracer=mock_tracer,
        )

    @pytest.mark.asyncio
    async def test_execute_sequential_workflow(self, orchestrator: AdvancedWorkflowOrchestrator, mock_message_bus: Mock):
        steps = [
            WorkflowStep(name="step_one", agent_type="typeA", action="do", inputs={}, outputs=["out1"]),
            WorkflowStep(name="step_two", agent_type="typeB", action="do", inputs={"prev": "{{step_one.out1}}"}, outputs=[]),
        ]
        workflow = WorkflowDefinition(name="seq", version="1", pattern=WorkflowPattern.SEQUENTIAL, steps=steps)
        workflow_id = "wf_seq"

        result = await orchestrator._execute_workflow(workflow, workflow_id, tenant_id="tenant")

        assert result == workflow_id
        assert [call.kwargs["topic"] for call in mock_message_bus.publish.call_args_list] == [
            "agents.typeA.do",
            "agents.typeB.do",
        ]
        context = orchestrator.active_workflows[workflow_id]
        assert set(context["step_results"].keys()) == {"step_one", "step_two"}

    @pytest.mark.asyncio
    async def test_execute_map_reduce_workflow(self, orchestrator: AdvancedWorkflowOrchestrator, mock_message_bus: Mock):
        steps = [
            WorkflowStep(name="map_fetch", agent_type="worker", action="fetch", inputs={}, outputs=["data"]),
            WorkflowStep(name="map_process", agent_type="worker", action="process", inputs={}, outputs=["processed"]),
            WorkflowStep(name="reduce_finalize", agent_type="worker", action="finalize", inputs={"items": "{{map_process.processed}}"}, outputs=["summary"]),
        ]
        workflow = WorkflowDefinition(name="mapred", version="1", pattern=WorkflowPattern.MAP_REDUCE, steps=steps)
        workflow_id = "wf_map"

        result = await orchestrator._execute_workflow(workflow, workflow_id, tenant_id="tenant")

        assert result == workflow_id
        assert [call.kwargs["topic"] for call in mock_message_bus.publish.call_args_list] == [
            "agents.worker.fetch",
            "agents.worker.process",
            "agents.worker.finalize",
        ]
        context = orchestrator.active_workflows[workflow_id]
        assert set(context["step_results"].keys()) == {"map_fetch", "map_process", "reduce_finalize"}

    @pytest.mark.asyncio
    async def test_saga_rollback_on_failure(self, orchestrator: AdvancedWorkflowOrchestrator, mock_message_bus: Mock, monkeypatch: pytest.MonkeyPatch):
        steps = [
            WorkflowStep(name="create_item", agent_type="svc", action="create", inputs={}, outputs=["id"]),
            WorkflowStep(name="update_item", agent_type="svc", action="update", inputs={}, outputs=["status"]),
        ]
        workflow = WorkflowDefinition(name="saga", version="1", pattern=WorkflowPattern.SAGA, steps=steps)
        workflow_id = "wf_saga"

        original_execute_step = orchestrator._execute_step

        async def failing_step(step: WorkflowStep, inputs: dict, context: dict):
            if step.name == "update_item":
                raise RuntimeError("boom")
            return await original_execute_step(step, inputs, context)

        monkeypatch.setattr(orchestrator, "_execute_step", failing_step)

        with pytest.raises(RuntimeError):
            await orchestrator._execute_workflow(workflow, workflow_id, tenant_id="tenant")

        topics = [call.kwargs["topic"] for call in mock_message_bus.publish.call_args_list]
        assert "agents.svc.create" in topics
        assert "agents.svc.rollback" in topics
        context = orchestrator.active_workflows[workflow_id]
        assert context["status"] == JobStatus.FAILED
        assert "create_item" in context["step_results"]


    def test_resolve_step_inputs_nested_and_edge_cases(self, orchestrator: AdvancedWorkflowOrchestrator):
        step_results = {
            "step_one": {
                "value": 1,
                "nested.inner": "deep",
            }
        }

        step = WorkflowStep(
            name="step_two",
            agent_type="worker",
            action="act",
            inputs={
                "simple": "{{step_one.value}}",
                "nested": "{{step_one.nested.inner}}",
                "missing": "{{absent.result}}",
                "malformed": "{{step_one}}",
                "not_placeholder": "{{step_one.value",
            },
            outputs=[],
        )

        resolved = orchestrator._resolve_step_inputs(step.inputs, step_results)

        assert resolved["simple"] == 1
        assert resolved["nested"] == "deep"
        assert resolved["missing"] == "{{absent.result}}"
        assert resolved["malformed"] == "{{step_one}}"
        assert resolved["not_placeholder"] == "{{step_one.value"


