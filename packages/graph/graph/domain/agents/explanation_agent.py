"""Explanation agent for generating natural language descriptions of violations.

This agent listens for ontology validation events and produces human readable
explanations for rule violations using a provided language model.  The agent is
designed to integrate with the existing message bus and optional
``AgentCoordinator`` to participate in multi‑agent workflows.

Features implemented:

* Subscribes to ``validation.completed`` events as well as individual
  ``validation.rule_violation`` events.
* Uses an ``LLMPort`` to turn rule violations into natural language
  explanations.
* Provides reusable explanation templates for common architectural rule
  categories (DIP, DDD and SOLID).
* Caches generated explanations so identical violations reuse previous
  responses.
* Optionally registers with an ``AgentCoordinator`` so it can be orchestrated
  alongside other agents.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from application.ports.base import LLMPort, MessageBusPort
from domain.agent_coordinator import AgentCoordinator
from domain.entities import JobStatus

logger = logging.getLogger(__name__)


# Reusable templates for different violation categories.
EXPLANATION_TEMPLATES: Dict[str, str] = {
    "DIP": (
        "The Dependency Inversion Principle (DIP) states that high‑level modules "
        "should not depend on low‑level modules. Components {components} depend on "
        "{constraint}, violating this principle. {suggestion}"
    ),
    "DDD": (
        "Domain‑Driven Design (DDD) encourages clear boundaries between domains. "
        "{description} involving {components} breaks the rule {constraint}. "
        "Consider: {suggestion}"
    ),
    "SOLID": (
        "A SOLID design principle violation was detected: {description}. "
        "Components affected: {components}. Constraint: {constraint}. "
        "Suggested fix: {suggestion}"
    ),
    "DEFAULT": (
        "Validation rule {rule_id} was violated: {description}. Components: "
        "{components}. Constraint: {constraint}. Suggested fix: {suggestion}"
    ),
}


class ExplanationAgent:
    """Agent responsible for explaining validation rule violations."""

    def __init__(
        self,
        message_bus: MessageBusPort,
        llm: LLMPort,
        agent_coordinator: Optional[AgentCoordinator] = None,
        tenant_id: str = "default",
    ) -> None:
        """Initialise the agent and subscribe to relevant events.

        Args:
            message_bus: Messaging interface used for inter‑agent communication
            llm: Language model used to generate explanations
            agent_coordinator: Optional coordinator for workflow orchestration
            tenant_id: Tenant identifier for multi‑tenant isolation
        """

        self.message_bus = message_bus
        self.llm = llm
        self.agent_coordinator = agent_coordinator
        self.tenant_id = tenant_id

        # Runtime state
        self.is_running = False
        self.explanation_cache: Dict[str, str] = {}

        # Subscribe to validation events
        self._subscribe_to_events()

        # Register with coordinator if provided
        if self.agent_coordinator:
            self._register_with_coordinator()

        logger.info("ExplanationAgent initialised for tenant %s", tenant_id)

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the agent and broadcast status."""
        self.is_running = True
        self.message_bus.publish(
            topic="agent.status",
            message={
                "agent_type": "explanation",
                "status": "started",
                "tenant_id": self.tenant_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            tenant_id=self.tenant_id,
        )
        logger.info("ExplanationAgent started")

    def stop(self) -> None:
        """Stop the agent and broadcast status."""
        self.is_running = False
        self.message_bus.publish(
            topic="agent.status",
            message={
                "agent_type": "explanation",
                "status": "stopped",
                "tenant_id": self.tenant_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            tenant_id=self.tenant_id,
        )
        logger.info("ExplanationAgent stopped")

    def get_status(self) -> Dict[str, Any]:
        """Return basic status information about the agent."""
        return {
            "agent_type": "explanation",
            "is_running": self.is_running,
            "cache_size": len(self.explanation_cache),
            "tenant_id": self.tenant_id,
        }

    # ------------------------------------------------------------------
    # Event subscription and coordination
    # ------------------------------------------------------------------
    def _subscribe_to_events(self) -> None:
        """Subscribe to validation related events."""
        self.message_bus.subscribe(
            topic="validation.completed",
            handler=self._handle_validation_report,
            tenant_id=self.tenant_id,
        )

        # Individual violations may also be published separately
        self.message_bus.subscribe(
            topic="validation.rule_violation",
            handler=self._handle_rule_violation,
            tenant_id=self.tenant_id,
        )

        # Participate in coordination messages from other agents
        self.message_bus.subscribe(
            topic="agent.coordination",
            handler=self._handle_agent_coordination,
            tenant_id=self.tenant_id,
        )

    def _register_with_coordinator(self) -> None:
        """Register workflow handler with the ``AgentCoordinator``."""
        try:
            self.agent_coordinator.register_workflow_handler(
                topic="workflows.validation.explanation",
                handler=self._handle_coordinator_workflow,
                tenant_id=self.tenant_id,
            )
            logger.info("ExplanationAgent registered with AgentCoordinator")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to register ExplanationAgent: %s", exc)

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------
    def _handle_validation_report(self, message: Dict[str, Any]) -> None:
        """Handle a complete validation report message."""
        if not self.is_running:
            return

        report = message.get("validation_report")
        if not report:
            return

        self._process_validation_report(report)

    def _handle_rule_violation(self, message: Dict[str, Any]) -> None:
        """Handle an individual rule violation message."""
        if not self.is_running:
            return

        violation = message.get("rule_violation") or message
        explanation = self._generate_explanation(violation)

        self.message_bus.publish(
            topic="explanation.completed",
            message={
                "agent_type": "explanation",
                "validation_report": None,
                "explanations": {violation.get("rule_id", "unknown"): explanation},
                "tenant_id": self.tenant_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            tenant_id=self.tenant_id,
        )

    def _handle_agent_coordination(self, message: Dict[str, Any]) -> None:
        """Respond to coordination messages from other agents."""
        action = message.get("action")
        if action == "validation_completed":
            report = message.get("validation_report")
            if report:
                self._process_validation_report(report)

    def _handle_coordinator_workflow(self, message: Dict[str, Any]) -> None:
        """Handle workflow messages when coordinated by ``AgentCoordinator``."""
        workflow_id = message.get("workflow_id")
        report = message.get("validation_report")

        explanations = self._process_validation_report(report or {})

        if self.agent_coordinator and workflow_id:
            self.agent_coordinator.update_workflow_status(
                workflow_id=workflow_id,
                step_name="explanation_generation",
                status=JobStatus.COMPLETED,
                tenant_id=self.tenant_id,
                result={"explanations": explanations},
            )

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------
    def _process_validation_report(self, report: Dict[str, Any]) -> Dict[str, str]:
        """Generate explanations for each violation in a validation report."""
        violations = report.get("violated_rules", [])
        explanations: Dict[str, str] = {}

        for violation in violations:
            explanation = self._generate_explanation(violation)
            rule_id = violation.get("rule_id", "unknown")
            explanations[rule_id] = explanation

        # Publish combined message including explanations
        self.message_bus.publish(
            topic="explanation.completed",
            message={
                "agent_type": "explanation",
                "validation_report": report,
                "explanations": explanations,
                "tenant_id": self.tenant_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            tenant_id=self.tenant_id,
        )

        # Notify other agents of completion
        self.message_bus.publish(
            topic="agent.coordination",
            message={
                "agent_type": "explanation",
                "action": "explanation_generated",
                "validation_report": report,
                "explanations": explanations,
                "tenant_id": self.tenant_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            tenant_id=self.tenant_id,
        )

        logger.info("Generated explanations for %d violations", len(explanations))
        return explanations

    def _generate_explanation(self, violation: Dict[str, Any]) -> str:
        """Generate or retrieve a cached explanation for a rule violation."""

        rule_id = violation.get("rule_id", "UNKNOWN")
        description = violation.get("description", "")
        components = ", ".join(violation.get("violating_components", []))
        constraint = violation.get("violated_constraint", "")
        suggestion = (
            violation.get("repair_suggestion", {}).get("description")
            if isinstance(violation.get("repair_suggestion"), dict)
            else getattr(
                getattr(violation, "repair_suggestion", None), "description", ""
            )
        )

        cache_key = self._cache_key(rule_id, description, components)
        if cache_key in self.explanation_cache:
            return self.explanation_cache[cache_key]

        template_key = "DEFAULT"
        upper_id = rule_id.upper()
        for key in ("DIP", "DDD", "SOLID"):
            if key in upper_id:
                template_key = key
                break

        template = EXPLANATION_TEMPLATES[template_key]
        prompt = template.format(
            rule_id=rule_id,
            description=description,
            components=components,
            constraint=constraint,
            suggestion=suggestion,
        )

        try:
            explanation = self.llm.generate(prompt=prompt, tenant_id=self.tenant_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to generate explanation: %s", exc)
            explanation = prompt  # Fallback to prompt

        self.explanation_cache[cache_key] = explanation
        return explanation

    @staticmethod
    def _cache_key(rule_id: str, description: str, components: str) -> str:
        """Create a stable cache key for a violation."""
        return f"{rule_id}:{description}:{components}"


def create_explanation_agent(
    message_bus: MessageBusPort,
    llm: LLMPort,
    agent_coordinator: Optional[AgentCoordinator] = None,
    tenant_id: str = "default",
) -> ExplanationAgent:
    """Factory function to create an ``ExplanationAgent``."""

    return ExplanationAgent(
        message_bus=message_bus,
        llm=llm,
        agent_coordinator=agent_coordinator,
        tenant_id=tenant_id,
    )

