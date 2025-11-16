"""Generation assistant for producing OWL axioms and code suggestions.

This agent listens for generation requests and uses provided ports to:

* Convert natural language descriptions into Manchester syntax OWL axioms
  via an ``OwlAxiomGeneratorPort`` implementation.
* Generate refactoring and code generation suggestions using an ``LLMPort``.
* Publish events that can be consumed by services able to execute Kthulu CLI
  commands for actual code generation.

The assistant integrates with the existing ``MessageBusPort`` so it can be
orchestrated alongside other agents.  It follows the same lifecycle methods as
``ReasonerAgent`` and ``ExplanationAgent``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from application.ports.base import LLMPort, MessageBusPort
from application.ports.owl import OwlAxiomGeneratorPort
from domain.agent_coordinator import AgentCoordinator
from domain.entities import JobStatus

logger = logging.getLogger(__name__)


class GenerationAssistant:
    """Agent responsible for generating OWL axioms and code suggestions."""

    def __init__(
        self,
        message_bus: MessageBusPort,
        axiom_generator: OwlAxiomGeneratorPort,
        llm: LLMPort,
        agent_coordinator: Optional[AgentCoordinator] = None,
        tenant_id: str = "default",
    ) -> None:
        """Initialise the generation assistant and subscribe to events."""

        self.message_bus = message_bus
        self.axiom_generator = axiom_generator
        self.llm = llm
        self.agent_coordinator = agent_coordinator
        self.tenant_id = tenant_id

        self.is_running = False

        self._subscribe_to_events()
        if self.agent_coordinator:
            self._register_with_coordinator()

        logger.info("GenerationAssistant initialised for tenant %s", tenant_id)

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the assistant and broadcast status."""
        self.is_running = True
        self.message_bus.publish(
            topic="agent.status",
            message={
                "agent_type": "generation",
                "status": "started",
                "tenant_id": self.tenant_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            tenant_id=self.tenant_id,
        )
        logger.info("GenerationAssistant started")

    def stop(self) -> None:
        """Stop the assistant and broadcast status."""
        self.is_running = False
        self.message_bus.publish(
            topic="agent.status",
            message={
                "agent_type": "generation",
                "status": "stopped",
                "tenant_id": self.tenant_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            tenant_id=self.tenant_id,
        )
        logger.info("GenerationAssistant stopped")

    def get_status(self) -> Dict[str, Any]:
        """Return basic status information about the assistant."""
        return {
            "agent_type": "generation",
            "is_running": self.is_running,
            "tenant_id": self.tenant_id,
        }

    # ------------------------------------------------------------------
    # Event subscription and coordination
    # ------------------------------------------------------------------
    def _subscribe_to_events(self) -> None:
        """Subscribe to generation request events."""
        self.message_bus.subscribe(
            topic="generation.request",
            handler=self._handle_generation_request,
            tenant_id=self.tenant_id,
        )
        self.message_bus.subscribe(
            topic="agent.coordination",
            handler=self._handle_agent_coordination,
            tenant_id=self.tenant_id,
        )

    def _register_with_coordinator(self) -> None:
        """Register workflow handler with an ``AgentCoordinator``."""
        try:
            self.agent_coordinator.register_workflow_handler(
                topic="workflows.generation.create_axioms",
                handler=self._handle_coordinator_workflow,
                tenant_id=self.tenant_id,
            )
            logger.info("GenerationAssistant registered with AgentCoordinator")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to register GenerationAssistant: %s", exc)

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------
    def _handle_generation_request(self, message: Dict[str, Any]) -> None:
        """Handle generation request messages."""
        if not self.is_running:
            return

        text = message.get("text") or message.get("prompt") or ""
        code_context = message.get("code_context")
        generate_code = message.get("generate_code", False)

        axioms = self._generate_axioms(text)
        suggestions = self._generate_refactoring_suggestions(text, code_context)

        if generate_code and suggestions:
            # Emit message that could be handled by a service invoking Kthulu CLI
            self.message_bus.publish(
                topic="kthulu.codegen",
                message={
                    "instructions": suggestions,
                    "tenant_id": self.tenant_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                tenant_id=self.tenant_id,
            )

        self.message_bus.publish(
            topic="generation.completed",
            message={
                "agent_type": "generation",
                "axioms": axioms,
                "suggestions": suggestions,
                "tenant_id": self.tenant_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            tenant_id=self.tenant_id,
        )

    def _handle_agent_coordination(self, message: Dict[str, Any]) -> None:
        """Respond to coordination messages from other agents."""
        action = message.get("action")
        if action == "generation_request":
            self._handle_generation_request(message)

    def _handle_coordinator_workflow(self, message: Dict[str, Any]) -> None:
        """Handle workflow messages when coordinated by ``AgentCoordinator``."""
        workflow_id = message.get("workflow_id")
        request = message.get("request", {})

        axioms = self._generate_axioms(request.get("text", ""))
        suggestions = self._generate_refactoring_suggestions(
            request.get("text", ""), request.get("code_context")
        )

        if self.agent_coordinator and workflow_id:
            self.agent_coordinator.update_workflow_status(
                workflow_id=workflow_id,
                step_name="generation",
                status=JobStatus.COMPLETED,
                tenant_id=self.tenant_id,
                result={"axioms": axioms, "suggestions": suggestions},
            )

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------
    def _generate_axioms(self, text: str) -> Optional[list]:
        """Convert natural language text to OWL axioms."""
        if not text:
            return []
        try:
            return self.axiom_generator.generate_axioms(
                text=text, tenant_id=self.tenant_id
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to generate axioms: %s", exc)
            return []

    def _generate_refactoring_suggestions(
        self, text: str, code_context: Optional[str]
    ) -> str:
        """Use LLM to generate refactoring suggestions."""
        prompt = (
            "Provide refactoring suggestions such as creating ports or emitting "
            "events for the following description. Respond succinctly.\n" + text
        )
        if code_context:
            prompt += f"\nCode context:\n{code_context}"

        try:
            return self.llm.generate(prompt=prompt, tenant_id=self.tenant_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to generate refactoring suggestions: %s", exc)
            return ""


# Factory -----------------------------------------------------------------

def create_generation_assistant(
    message_bus: MessageBusPort,
    axiom_generator: OwlAxiomGeneratorPort,
    llm: LLMPort,
    agent_coordinator: Optional[AgentCoordinator] = None,
    tenant_id: str = "default",
) -> GenerationAssistant:
    """Factory function to create a ``GenerationAssistant``."""

    return GenerationAssistant(
        message_bus=message_bus,
        axiom_generator=axiom_generator,
        llm=llm,
        agent_coordinator=agent_coordinator,
        tenant_id=tenant_id,
    )
