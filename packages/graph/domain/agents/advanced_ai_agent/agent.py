"""Advanced AI Agent orchestrating specialized components."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from application.ports.base import LLMPort, MessageBusPort
from application.ports.knowledge_graph_port import KnowledgeGraphPort
from domain.agent_coordinator import AgentCoordinator
from domain.entities import JobStatus
from domain.services.semantic_search_service import SemanticSearchService
from domain.services.architectural_pattern_service import ArchitecturalPatternService

from .query_processing import (
    QueryProcessor,
    NaturalLanguageQuery,
    QueryResponse,
    QueryType,
)
from .code_review import (
    CodeReviewAssistant,
    CodeReviewSuggestion,
    SemanticCompletion,
)
from .pattern_detection import PatternDetector

logger = logging.getLogger(__name__)


class AdvancedAIAgent:
    """Agent for advanced AI capabilities in architecture development"""

    def __init__(
        self,
        message_bus: MessageBusPort,
        llm: LLMPort,
        knowledge_graph: KnowledgeGraphPort,
        agent_coordinator: Optional[AgentCoordinator] = None,
        tenant_id: str = "default",
    ) -> None:
        self.message_bus = message_bus
        self.llm = llm
        self.knowledge_graph = knowledge_graph
        self.agent_coordinator = agent_coordinator
        self.tenant_id = tenant_id

        self.semantic_search = SemanticSearchService(knowledge_graph, llm)
        self.pattern_service = ArchitecturalPatternService(knowledge_graph, llm)

        self.query_processor = QueryProcessor(
            message_bus,
            llm,
            self.semantic_search,
            self.pattern_service,
            tenant_id,
            self._publish_error,
        )
        self.code_review = CodeReviewAssistant(
            message_bus, llm, tenant_id, self._publish_error
        )
        self.pattern_detector = PatternDetector(
            message_bus, self.pattern_service, tenant_id, self._publish_error
        )

        self.is_running = False

        self._subscribe_to_events()
        if self.agent_coordinator:
            self._register_with_coordinator()
        logger.info("AdvancedAIAgent initialized for tenant %s", tenant_id)

    # Life-cycle -----------------------------------------------------
    def start(self) -> None:
        self.is_running = True
        logger.info("AdvancedAIAgent started")
        self.message_bus.publish(
            topic="agent.status",
            message={
                "agent_type": "advanced_ai",
                "status": "started",
                "tenant_id": self.tenant_id,
                "timestamp": datetime.now().isoformat(),
            },
            tenant_id=self.tenant_id,
        )

    def stop(self) -> None:
        self.is_running = False
        logger.info("AdvancedAIAgent stopped")
        self.message_bus.publish(
            topic="agent.status",
            message={
                "agent_type": "advanced_ai",
                "status": "stopped",
                "tenant_id": self.tenant_id,
                "timestamp": datetime.now().isoformat(),
            },
            tenant_id=self.tenant_id,
        )

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_type": "advanced_ai",
            "is_running": self.is_running,
            "tenant_id": self.tenant_id,
            "query_count": self.query_processor.query_count,
            "review_count": self.code_review.review_count,
            "completion_count": self.code_review.completion_count,
        }

    # Event handling -------------------------------------------------
    def _subscribe_to_events(self) -> None:
        self.message_bus.subscribe(
            topic="ai.natural_language_query",
            handler=self._handle_natural_language_query,
            tenant_id=self.tenant_id,
        )
        self.message_bus.subscribe(
            topic="ai.code_review_request",
            handler=self._handle_code_review_request,
            tenant_id=self.tenant_id,
        )
        self.message_bus.subscribe(
            topic="ai.semantic_completion_request",
            handler=self._handle_semantic_completion_request,
            tenant_id=self.tenant_id,
        )
        self.message_bus.subscribe(
            topic="ai.anti_pattern_detection",
            handler=self._handle_anti_pattern_detection,
            tenant_id=self.tenant_id,
        )
        self.message_bus.subscribe(
            topic="agent.coordination",
            handler=self._handle_agent_coordination,
            tenant_id=self.tenant_id,
        )

    def _register_with_coordinator(self) -> None:
        try:
            self.agent_coordinator.register_workflow_handler(
                topic="workflows.ai.advanced_analysis",
                handler=self._handle_coordinator_workflow,
                tenant_id=self.tenant_id,
            )
            logger.info("AdvancedAIAgent registered with AgentCoordinator")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to register with AgentCoordinator: %s", exc)

    # Delegated handlers --------------------------------------------
    def _handle_natural_language_query(self, message: Dict[str, Any]) -> None:
        if self.is_running:
            self.query_processor.handle_natural_language_query(message)

    def _classify_query(self, query_text: str) -> QueryType:
        return self.query_processor.classify_query(query_text)

    def _process_natural_language_query(self, query: NaturalLanguageQuery) -> QueryResponse:
        return self.query_processor.process_query(query)

    def _handle_component_search_query(self, query: NaturalLanguageQuery) -> QueryResponse:
        return self.query_processor.handle_component_search_query(query)

    def _handle_pattern_detection_query(self, query: NaturalLanguageQuery) -> QueryResponse:
        return self.query_processor.handle_pattern_detection_query(query)

    def _handle_anti_pattern_query(self, query: NaturalLanguageQuery) -> QueryResponse:
        return self.query_processor.handle_anti_pattern_query(query)

    def _handle_general_architecture_query(self, query: NaturalLanguageQuery) -> QueryResponse:
        return self.query_processor.handle_general_architecture_query(query)

    def _handle_code_review_request(self, message: Dict[str, Any]) -> None:
        if self.is_running:
            self.code_review.handle_code_review_request(message)

    def _generate_code_review_suggestions(
        self, file_path: str, code_content: str, context: Dict[str, Any]
    ) -> List[CodeReviewSuggestion]:
        return self.code_review.generate_code_review_suggestions(
            file_path, code_content, context
        )

    def _handle_semantic_completion_request(self, message: Dict[str, Any]) -> None:
        if self.is_running:
            self.code_review.handle_semantic_completion_request(message)

    def _generate_semantic_completions(
        self,
        file_path: str,
        cursor_position: Dict[str, Any],
        code_context: str,
        partial_input: str,
    ) -> List[SemanticCompletion]:
        return self.code_review.generate_semantic_completions(
            file_path, cursor_position, code_context, partial_input
        )

    def _handle_anti_pattern_detection(self, message: Dict[str, Any]) -> None:
        if self.is_running:
            self.pattern_detector.handle_anti_pattern_detection(message)

    def _calculate_severity(self, anti_pattern) -> str:
        return self.pattern_detector._calculate_severity(anti_pattern)


    # Coordination ---------------------------------------------------
    def _handle_agent_coordination(self, message: Dict[str, Any]) -> None:
        try:
            action = message.get("action")
            if action == "architecture_analysis_request":
                self._handle_anti_pattern_detection(message)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Error handling agent coordination: %s", exc)

    def _handle_coordinator_workflow(self, message: Dict[str, Any]) -> None:
        try:
            workflow_id = message.get("workflow_id")
            workflow_type = message.get("workflow_type")
            if workflow_type == "advanced_ai_analysis":
                query = message.get("query", "")
                analysis_result = self._perform_comprehensive_analysis(query)
                if self.agent_coordinator:
                    self.agent_coordinator.update_workflow_status(
                        workflow_id=workflow_id,
                        step_name="advanced_ai_analysis",
                        status=JobStatus.COMPLETED,
                        tenant_id=self.tenant_id,
                        result=analysis_result,
                    )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Error handling coordinator workflow: %s", exc)

    def _perform_comprehensive_analysis(self, query: str) -> Dict[str, Any]:
        nl_query = NaturalLanguageQuery(query_text=query, tenant_id=self.tenant_id)
        query_response = self.query_processor.process_query(nl_query)
        pattern_analysis = self.pattern_service.analyze_patterns(self.tenant_id)
        return {
            "query_response": {
                "response_text": query_response.response_text,
                "confidence": query_response.confidence,
                "suggestions": query_response.suggestions,
            },
            "pattern_analysis": {
                "quality_score": pattern_analysis.architecture_quality_score,
                "detected_patterns": len(pattern_analysis.detected_patterns),
                "anti_patterns": len(pattern_analysis.anti_patterns),
            },
        }

    # Error handling -------------------------------------------------
    def _publish_error(self, operation: str, error_message: str) -> None:
        self.message_bus.publish(
            topic="ai.error",
            message={
                "agent_type": "advanced_ai",
                "operation": operation,
                "error_message": error_message,
                "tenant_id": self.tenant_id,
                "timestamp": datetime.now().isoformat(),
            },
            tenant_id=self.tenant_id,
        )


def create_advanced_ai_agent(
    message_bus: MessageBusPort,
    llm: LLMPort,
    knowledge_graph: KnowledgeGraphPort,
    agent_coordinator: Optional[AgentCoordinator] = None,
    tenant_id: str = "default",
) -> AdvancedAIAgent:
    return AdvancedAIAgent(
        message_bus=message_bus,
        llm=llm,
        knowledge_graph=knowledge_graph,
        agent_coordinator=agent_coordinator,
        tenant_id=tenant_id,
    )
