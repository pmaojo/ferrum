
"""Unified agent coordination system that harmonizes all agent types."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass

from application.ports.messaging import MessageBusPort
from application.ports import TracingPort
from domain.entities import JobStatus, AgentType, CoordinationStrategy
from domain.agent_coordinator import AgentCoordinator, CoordinationException
from domain.advanced_workflow_orchestrator import AdvancedWorkflowOrchestrator, WorkflowDefinition
from domain.structrag.structrag_orchestrator import StructRAGOrchestrator

logger = logging.getLogger(__name__)


class AgentSystemType(Enum):
    """Types of agent systems available."""
    STRUCTRAG = "structrag"
    WORKFLOW = "workflow"
    GRAPHRAG = "graphrag"
    AUTOGEN = "autogen"
    FALKORDB = "falkordb"


@dataclass
class UnifiedAgentRequest:
    """Unified request for any agent system."""
    system_type: AgentSystemType
    operation: str
    parameters: Dict[str, Any]
    tenant_id: str
    workflow_id: str
    user_id: Optional[str] = None
    priority: int = 1
    timeout_seconds: int = 300


@dataclass
class UnifiedAgentResponse:
    """Unified response from any agent system."""
    system_type: AgentSystemType
    operation: str
    success: bool
    result: Dict[str, Any]
    error_message: Optional[str] = None
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = None


class CoordinationStrategyExecutor(ABC):
    """Interface for coordination strategy implementations."""

    @abstractmethod
    def execute(
        self, session_context: Dict[str, Any], coordinator: "UnifiedAgentCoordinator"
    ) -> str:
        """Execute coordination strategy and return session identifier."""


class HierarchicalCoordinationStrategy(CoordinationStrategyExecutor):
    """Primary system with sequential fallbacks."""

    def execute(
        self, session_context: Dict[str, Any], coordinator: "UnifiedAgentCoordinator"
    ) -> str:
        request = session_context["request"]
        systems = [session_context["primary_system"]] + session_context["fallback_systems"]

        for system_type in systems:
            try:
                logger.info("Attempting execution with %s", system_type)
                session_context["active_system"] = system_type
                response = coordinator._execute_on_system(system_type, request)

                if response.success:
                    session_context["responses"][system_type.value] = response
                    session_context["status"] = JobStatus.COMPLETED
                    session_context["primary_response"] = response
                    return session_context["session_id"]

            except Exception as e:  # pragma: no cover - defensive
                logger.warning("System %s failed: %s", system_type, e)
                session_context["responses"][system_type.value] = UnifiedAgentResponse(
                    system_type=system_type,
                    operation=request.operation,
                    success=False,
                    result={},
                    error_message=str(e),
                )

        raise CoordinationException(
            message="All agent systems failed in hierarchical coordination",
            error_code="ALL_SYSTEMS_FAILED",
            context={"session_id": session_context["session_id"]},
        )


class CollaborativeCoordinationStrategy(CoordinationStrategyExecutor):
    """Execute all systems and synthesize their results."""

    def execute(
        self, session_context: Dict[str, Any], coordinator: "UnifiedAgentCoordinator"
    ) -> str:
        request = session_context["request"]
        systems = [session_context["primary_system"]] + session_context["fallback_systems"]

        responses: Dict[str, UnifiedAgentResponse] = {}
        successful: List[UnifiedAgentResponse] = []

        for system_type in systems:
            try:
                response = coordinator._execute_on_system(system_type, request)
                responses[system_type.value] = response
                if response.success:
                    successful.append(response)
            except Exception as e:  # pragma: no cover - defensive
                responses[system_type.value] = UnifiedAgentResponse(
                    system_type=system_type,
                    operation=request.operation,
                    success=False,
                    result={},
                    error_message=str(e),
                )

        if successful:
            synthesized = coordinator._synthesize_collaborative_results(successful)
            session_context["responses"] = responses
            session_context["status"] = JobStatus.COMPLETED
            session_context["synthesized_response"] = synthesized
            return session_context["session_id"]

        raise CoordinationException(
            message="No successful responses in collaborative coordination",
            error_code="COLLABORATIVE_COORDINATION_FAILED",
            context={"session_id": session_context["session_id"]},
        )


class CompetitiveCoordinationStrategy(CoordinationStrategyExecutor):
    """Return first successful response from the available systems."""

    def execute(
        self, session_context: Dict[str, Any], coordinator: "UnifiedAgentCoordinator"
    ) -> str:
        request = session_context["request"]
        systems = [session_context["primary_system"]] + session_context["fallback_systems"]

        for system_type in systems:
            try:
                response = coordinator._execute_on_system(system_type, request)
                session_context["responses"][system_type.value] = response
                if response.success:
                    session_context["status"] = JobStatus.COMPLETED
                    session_context["primary_response"] = response
                    return session_context["session_id"]
            except Exception as e:  # pragma: no cover - defensive
                session_context["responses"][system_type.value] = UnifiedAgentResponse(
                    system_type=system_type,
                    operation=request.operation,
                    success=False,
                    result={},
                    error_message=str(e),
                )

        raise CoordinationException(
            message="No system succeeded in competitive coordination",
            error_code="COMPETITIVE_COORDINATION_FAILED",
            context={"session_id": session_context["session_id"]},
        )


class PipelineCoordinationStrategy(CoordinationStrategyExecutor):
    """Sequentially execute systems, passing results along the chain."""

    def execute(
        self, session_context: Dict[str, Any], coordinator: "UnifiedAgentCoordinator"
    ) -> str:
        request = session_context["request"]
        systems = [session_context["primary_system"]] + session_context["fallback_systems"]
        current_request = request
        last_response: Optional[UnifiedAgentResponse] = None

        for system_type in systems:
            response = coordinator._execute_on_system(system_type, current_request)
            session_context["responses"][system_type.value] = response
            if not response.success:
                raise CoordinationException(
                    message=f"System {system_type} failed in pipeline",
                    error_code="PIPELINE_STEP_FAILED",
                    context={"session_id": session_context["session_id"]},
                )
            last_response = response
            # Subsequent systems receive previous result as parameters
            current_request = UnifiedAgentRequest(
                system_type=current_request.system_type,
                operation=current_request.operation,
                parameters={**current_request.parameters, **response.result},
                tenant_id=current_request.tenant_id,
                workflow_id=current_request.workflow_id,
                user_id=current_request.user_id,
                priority=current_request.priority,
                timeout_seconds=current_request.timeout_seconds,
            )

        session_context["status"] = JobStatus.COMPLETED
        if last_response:
            session_context["primary_response"] = last_response
        return session_context["session_id"]


class UnifiedAgentCoordinator:
    """Unified coordinator that manages all agent systems."""

    def __init__(
        self,
        message_bus: MessageBusPort,
        tracer: Optional[TracingPort] = None,
        structrag_orchestrator: Optional[StructRAGOrchestrator] = None,
        workflow_orchestrator: Optional[AdvancedWorkflowOrchestrator] = None,
        base_coordinator: Optional[AgentCoordinator] = None,
        strategies: Optional[
            Dict[CoordinationStrategy, CoordinationStrategyExecutor]
        ] = None,
    ):
        """Initialize unified coordinator with all agent systems."""
        self.message_bus = message_bus
        self.tracer = tracer
        
        # Initialize individual coordinators
        self.base_coordinator = base_coordinator or AgentCoordinator(message_bus, tracer)
        self.structrag_orchestrator = structrag_orchestrator
        self.workflow_orchestrator = workflow_orchestrator
        
        # Active agent sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Agent system registry
        self.agent_systems: Dict[AgentSystemType, Any] = {}
        if structrag_orchestrator:
            self.agent_systems[AgentSystemType.STRUCTRAG] = structrag_orchestrator
        if workflow_orchestrator:
            self.agent_systems[AgentSystemType.WORKFLOW] = workflow_orchestrator

        self.strategies = strategies or {
            CoordinationStrategy.HIERARCHICAL: HierarchicalCoordinationStrategy(),
            CoordinationStrategy.COLLABORATIVE: CollaborativeCoordinationStrategy(),
            CoordinationStrategy.COMPETITIVE: CompetitiveCoordinationStrategy(),
            CoordinationStrategy.PIPELINE: PipelineCoordinationStrategy(),
        }

    def coordinate_unified_workflow(
        self,
        *,
        workflow_type: str,
        primary_system: AgentSystemType,
        fallback_systems: List[AgentSystemType],
        request: UnifiedAgentRequest,
        coordination_strategy: CoordinationStrategy = CoordinationStrategy.HIERARCHICAL,
    ) -> str:
        """Coordinate workflow across multiple agent systems."""
        
        session_id = f"unified_{request.workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create unified session
        session_context = {
            "session_id": session_id,
            "workflow_type": workflow_type,
            "primary_system": primary_system,
            "fallback_systems": fallback_systems,
            "coordination_strategy": coordination_strategy,
            "request": request,
            "status": JobStatus.PENDING,
            "created_at": datetime.now(),
            "responses": {},
            "active_system": None,
        }
        
        self.active_sessions[session_id] = session_context
        
        try:
            strategy = self.strategies.get(coordination_strategy)
            if not strategy:
                raise ValueError(f"Unsupported strategy: {coordination_strategy}")

            return strategy.execute(session_context, self)
                
        except Exception as e:
            session_context["status"] = JobStatus.FAILED
            session_context["error"] = str(e)
            raise CoordinationException(
                message=f"Unified coordination failed: {str(e)}",
                error_code="UNIFIED_COORDINATION_FAILED",
                context={"session_id": session_id, "workflow_type": workflow_type},
            ) from e


    def _execute_on_system(
        self, 
        system_type: AgentSystemType, 
        request: UnifiedAgentRequest
    ) -> UnifiedAgentResponse:
        """Execute request on specific agent system."""
        start_time = datetime.now()
        
        try:
            if system_type == AgentSystemType.STRUCTRAG:
                return self._execute_structrag_request(request)
            elif system_type == AgentSystemType.WORKFLOW:
                return self._execute_workflow_request(request)
            elif system_type == AgentSystemType.GRAPHRAG:
                return self._execute_graphrag_request(request)
            else:
                raise ValueError(f"Unsupported system type: {system_type}")
                
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            return UnifiedAgentResponse(
                system_type=system_type,
                operation=request.operation,
                success=False,
                result={},
                error_message=str(e),
                processing_time_ms=processing_time,
            )

    def _execute_structrag_request(self, request: UnifiedAgentRequest) -> UnifiedAgentResponse:
        """Execute request on StructRAG system."""
        if not self.structrag_orchestrator:
            raise ValueError("StructRAG orchestrator not available")
            
        start_time = datetime.now()
        
        if request.operation == "process_query":
            result = self.structrag_orchestrator.process_query(
                query=request.parameters.get("query", ""),
                documents=request.parameters.get("documents", []),
                tenant_id=request.tenant_id,
                kg_id=request.parameters.get("kg_id", "default"),
                opts=request.parameters.get("opts", {}),
            )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return UnifiedAgentResponse(
                system_type=AgentSystemType.STRUCTRAG,
                operation=request.operation,
                success=result.get("success", True),
                result=result,
                processing_time_ms=processing_time,
                metadata={"structure_type": result.get("structure_type")},
            )
        else:
            raise ValueError(f"Unsupported StructRAG operation: {request.operation}")

    def _execute_workflow_request(self, request: UnifiedAgentRequest) -> UnifiedAgentResponse:
        """Execute request on workflow orchestrator."""
        if not self.workflow_orchestrator:
            raise ValueError("Workflow orchestrator not available")
            
        start_time = datetime.now()
        
        if request.operation == "execute_research_workflow":
            workflow_id = self.workflow_orchestrator.execute_graphrag_research_workflow(
                research_query=request.parameters.get("query", ""),
                knowledge_graphs=request.parameters.get("knowledge_graphs", []),
                tenant_id=request.tenant_id,
                workflow_id=request.workflow_id,
                user_id=request.user_id,
            )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return UnifiedAgentResponse(
                system_type=AgentSystemType.WORKFLOW,
                operation=request.operation,
                success=True,
                result={"workflow_id": workflow_id},
                processing_time_ms=processing_time,
            )
        else:
            raise ValueError(f"Unsupported workflow operation: {request.operation}")

    def _execute_graphrag_request(self, request: UnifiedAgentRequest) -> UnifiedAgentResponse:
        """Execute request on base GraphRAG coordinator."""
        start_time = datetime.now()
        
        if request.operation == "coordinate_query":
            workflow_id = self.base_coordinator.coordinate_query_workflow(
                question=request.parameters.get("query", ""),
                kg_id=request.parameters.get("kg_id", "default"),
                tenant_id=request.tenant_id,
                user_id=request.user_id or "system",
                workflow_id=request.workflow_id,
                query_opts=request.parameters.get("opts", {}),
            )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return UnifiedAgentResponse(
                system_type=AgentSystemType.GRAPHRAG,
                operation=request.operation,
                success=True,
                result={"workflow_id": workflow_id},
                processing_time_ms=processing_time,
            )
        else:
            raise ValueError(f"Unsupported GraphRAG operation: {request.operation}")

    def _synthesize_collaborative_results(
        self, responses: List[UnifiedAgentResponse]
    ) -> UnifiedAgentResponse:
        """Synthesize results from multiple successful agent systems."""
        
        # Simple synthesis strategy - could be enhanced with LLM-based synthesis
        combined_results = {}
        total_processing_time = 0
        metadata = {}
        
        for response in responses:
            system_key = response.system_type.value
            combined_results[system_key] = response.result
            total_processing_time += response.processing_time_ms
            
            if response.metadata:
                metadata[system_key] = response.metadata
        
        # Create synthesized response
        return UnifiedAgentResponse(
            system_type=AgentSystemType.WORKFLOW,  # Mark as synthesized
            operation="collaborative_synthesis",
            success=True,
            result={
                "synthesized": True,
                "individual_results": combined_results,
                "consensus_score": len(responses) / len(self.agent_systems),
            },
            processing_time_ms=total_processing_time / len(responses),
            metadata=metadata,
        )

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of a unified coordination session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session not found: {session_id}")
            
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "workflow_type": session["workflow_type"],
            "status": session["status"],
            "active_system": session.get("active_system"),
            "responses_count": len(session["responses"]),
            "created_at": session["created_at"].isoformat(),
            "has_primary_response": "primary_response" in session,
            "has_synthesized_response": "synthesized_response" in session,
        }

