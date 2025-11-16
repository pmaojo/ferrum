"""Reasoner Agent for event-driven ontology validation.

This agent integrates with the existing agent coordination system to provide
automated ontology validation using the hybrid reasoner adapter with circuit
breaker protection.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from application.ports.base import MessageBusPort, OntologyValidatorPort
from domain.entities import Triple, ValidationReport, JobStatus
from domain.entities.validation_report import RuleViolation, RepairSuggestion
from domain.agent_coordinator import AgentCoordinator
from domain.services.monitoring_service import MonitoringService, PerformanceMonitor

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states for reasoner failure protection."""
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failures detected, blocking requests
    HALF_OPEN = "HALF_OPEN"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds before attempting recovery
    success_threshold: int = 2  # Successful calls needed to close circuit
    timeout_seconds: int = 30   # Timeout for reasoner operations


class CircuitBreaker:
    """Circuit breaker for protecting against reasoner failures."""
    
    def __init__(self, config: CircuitBreakerConfig):
        """Initialize circuit breaker with configuration.
        
        Args:
            config: CircuitBreakerConfig with failure thresholds and timeouts
        """
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_attempt_time: Optional[datetime] = None
    
    def can_execute(self) -> bool:
        """Check if operation can be executed based on circuit state.
        
        Returns:
            True if operation should proceed, False if circuit is open
        """
        now = datetime.now()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        elif self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (self.last_failure_time and 
                now - self.last_failure_time > timedelta(seconds=self.config.recovery_timeout)):
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN state")
                return True
            return False
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self) -> None:
        """Record successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker closed after successful recovery")
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker reopened after failure during recovery")


class ReasonerAgent:
    """Agent for event-driven ontology validation with circuit breaker protection.
    
    This agent integrates with the existing agent coordination system to provide
    automated ontology validation using the hybrid reasoner adapter. It includes
    circuit breaker protection to handle reasoner failures gracefully.
    """
    
    def __init__(
        self,
        message_bus: MessageBusPort,
        ontology_validator: OntologyValidatorPort,
        monitoring_service: Optional[MonitoringService] = None,
        agent_coordinator: Optional[AgentCoordinator] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        tenant_id: str = "default"
    ):
        """Initialize the reasoner agent.
        
        Args:
            message_bus: Message bus for event communication
            ontology_validator: Validator for ontology reasoning
            agent_coordinator: Optional agent coordinator for workflow integration
            circuit_breaker_config: Optional circuit breaker configuration
            tenant_id: Tenant identifier for multi-tenant isolation
        """
        self.message_bus = message_bus
        self.ontology_validator = ontology_validator
        self.monitoring_service = monitoring_service
        self.agent_coordinator = agent_coordinator
        self.tenant_id = tenant_id
        
        # Initialize circuit breaker
        config = circuit_breaker_config or CircuitBreakerConfig()
        self.circuit_breaker = CircuitBreaker(config)
        
        # Agent state
        self.is_running = False
        self.validation_count = 0
        self.last_validation_time: Optional[datetime] = None
        
        # Subscribe to ontology change events
        self._subscribe_to_events()
        
        # Register with agent coordinator if available
        if self.agent_coordinator:
            self._register_with_coordinator()
        
        logger.info(f"ReasonerAgent initialized for tenant {tenant_id}")
    
    def start(self) -> None:
        """Start the reasoner agent."""
        self.is_running = True
        logger.info("ReasonerAgent started")
        
        # Publish agent status
        self.message_bus.publish(
            topic="agent.status",
            message={
                "agent_type": "reasoner",
                "status": "started",
                "tenant_id": self.tenant_id,
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=self.tenant_id
        )
    
    def stop(self) -> None:
        """Stop the reasoner agent."""
        self.is_running = False
        logger.info("ReasonerAgent stopped")
        
        # Publish agent status
        self.message_bus.publish(
            topic="agent.status",
            message={
                "agent_type": "reasoner",
                "status": "stopped",
                "tenant_id": self.tenant_id,
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=self.tenant_id
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status.
        
        Returns:
            Dictionary containing agent status information
        """
        return {
            "agent_type": "reasoner",
            "is_running": self.is_running,
            "tenant_id": self.tenant_id,
            "validation_count": self.validation_count,
            "last_validation_time": self.last_validation_time.isoformat() if self.last_validation_time else None,
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "circuit_breaker_failure_count": self.circuit_breaker.failure_count,
            "circuit_breaker_success_count": self.circuit_breaker.success_count
        }
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to ontology change events."""
        # Subscribe to ontology change events
        self.message_bus.subscribe(
            topic="ontology.changed",
            handler=self._handle_ontology_change,
            tenant_id=self.tenant_id
        )
        
        # Subscribe to validation requests
        self.message_bus.subscribe(
            topic="validation.requested",
            handler=self._handle_validation_request,
            tenant_id=self.tenant_id
        )
        
        # Subscribe to workflow events for coordination
        self.message_bus.subscribe(
            topic="workflows.validation.start",
            handler=self._handle_workflow_validation,
            tenant_id=self.tenant_id
        )
        
        # Subscribe to agent coordination events
        self.message_bus.subscribe(
            topic="agent.coordination",
            handler=self._handle_agent_coordination,
            tenant_id=self.tenant_id
        )
        
        logger.info("ReasonerAgent subscribed to ontology change events")
    
    def _register_with_coordinator(self) -> None:
        """Register this agent with the agent coordinator."""
        try:
            # Register workflow handler for validation workflows
            self.agent_coordinator.register_workflow_handler(
                topic="workflows.validation.reasoner",
                handler=self._handle_coordinator_workflow,
                tenant_id=self.tenant_id
            )
            
            logger.info("ReasonerAgent registered with AgentCoordinator")
            
        except Exception as e:
            logger.warning(f"Failed to register with AgentCoordinator: {str(e)}")
    
    def _handle_agent_coordination(self, message: Dict[str, Any]) -> None:
        """Handle agent coordination messages.
        
        Args:
            message: Coordination message from other agents
        """
        try:
            agent_type = message.get("agent_type")
            action = message.get("action")
            
            if agent_type == "reasoner":
                # Skip our own messages
                return
            
            # React to other agents' actions
            if action == "explanation_requested":
                # Another agent is requesting explanation, we can provide validation context
                validation_report = message.get("validation_report")
                if validation_report:
                    self._provide_validation_context(validation_report)
            
            elif action == "generation_completed":
                # Generation agent completed, we might need to re-validate
                triples = message.get("new_triples", [])
                if triples:
                    self._trigger_revalidation(triples)
                    
        except Exception as e:
            logger.exception(f"Error handling agent coordination: {str(e)}")
    
    def _handle_coordinator_workflow(self, message: Dict[str, Any]) -> None:
        """Handle workflow messages from the agent coordinator.
        
        Args:
            message: Workflow message from agent coordinator
        """
        try:
            workflow_id = message.get("workflow_id")
            workflow_type = message.get("workflow_type")
            
            if workflow_type == "ontology_validation":
                # Handle validation workflow
                triples = message.get("triples", [])
                ontology_version_id = message.get("ontology_version_id", "unknown")
                
                # Update workflow status to in progress
                if self.agent_coordinator:
                    self.agent_coordinator.update_workflow_status(
                        workflow_id=workflow_id,
                        step_name="reasoner_validation",
                        status=JobStatus.IN_PROGRESS,
                        tenant_id=self.tenant_id
                    )
                
                # Perform validation
                validation_report = self._validate_with_circuit_breaker(
                    triples=triples,
                    ontology_version_id=ontology_version_id
                )
                
                # Update workflow status based on results
                status = JobStatus.COMPLETED if validation_report.is_consistent else JobStatus.FAILED
                
                if self.agent_coordinator:
                    self.agent_coordinator.update_workflow_status(
                        workflow_id=workflow_id,
                        step_name="reasoner_validation",
                        status=status,
                        tenant_id=self.tenant_id,
                        result={
                            "validation_report": {
                                "is_consistent": validation_report.is_consistent,
                                "violation_count": len(validation_report.violated_rules),
                                "unsat_classes": validation_report.unsat_classes
                            }
                        }
                    )
                
                logger.info(f"Completed workflow validation: {workflow_id}")
                
        except Exception as e:
            logger.exception(f"Error handling coordinator workflow: {str(e)}")
            
            # Update workflow status to failed
            if self.agent_coordinator and message.get("workflow_id"):
                self.agent_coordinator.update_workflow_status(
                    workflow_id=message["workflow_id"],
                    step_name="reasoner_validation",
                    status=JobStatus.FAILED,
                    tenant_id=self.tenant_id,
                    result={"error": str(e)}
                )
    
    def _handle_workflow_validation(self, message: Dict[str, Any]) -> None:
        """Handle workflow-based validation requests.
        
        Args:
            message: Workflow validation message
        """
        try:
            workflow_id = message.get("workflow_id")
            workflow_type = message.get("workflow_type", "validation")
            
            logger.info(f"Processing workflow validation: {workflow_id}")
            
            # Extract validation parameters
            triples = message.get("triples", [])
            ontology_version_id = message.get("ontology_version_id", "unknown")
            
            # Convert message triples to Triple objects if needed
            if triples and isinstance(triples[0], dict):
                triples = [
                    Triple(
                        subject=t["subject"],
                        predicate=t["predicate"],
                        object=t["object"],
                        tenant_id=self.tenant_id
                    )
                    for t in triples
                ]
            
            # Perform validation
            validation_report = self._validate_with_circuit_breaker(
                triples=triples,
                ontology_version_id=ontology_version_id
            )
            
            # Publish workflow results
            self._publish_workflow_validation_results(
                validation_report=validation_report,
                workflow_id=workflow_id,
                workflow_type=workflow_type
            )
            
        except Exception as e:
            logger.exception(f"Error handling workflow validation: {str(e)}")
            self._publish_workflow_validation_error(
                workflow_id=message.get("workflow_id", "unknown"),
                error_message=str(e)
            )
    
    def _handle_ontology_change(self, message: Dict[str, Any]) -> None:
        """Handle ontology change events.
        
        Args:
            message: Event message containing ontology change information
        """
        if not self.is_running:
            logger.debug("ReasonerAgent not running, ignoring ontology change event")
            return
        
        try:
            # Extract event data
            event_type = message.get("event_type", "unknown")
            triples = message.get("triples", [])
            ontology_version_id = message.get("ontology_version_id", "unknown")
            
            logger.info(f"Processing ontology change event: {event_type}, "
                       f"{len(triples)} triples, version {ontology_version_id}")
            
            # Convert message triples to Triple objects if needed
            if triples and isinstance(triples[0], dict):
                triples = [
                    Triple(
                        subject=t["subject"],
                        predicate=t["predicate"],
                        object=t["object"],
                        tenant_id=self.tenant_id
                    )
                    for t in triples
                ]
            
            # Perform validation
            validation_report = self._validate_with_circuit_breaker(
                triples=triples,
                ontology_version_id=ontology_version_id
            )
            
            # Publish validation results
            self._publish_validation_results(validation_report, event_type)
            
        except Exception as e:
            logger.exception(f"Error handling ontology change event: {str(e)}")
            self._publish_validation_error(str(e))
    
    def _handle_validation_request(self, message: Dict[str, Any]) -> None:
        """Handle explicit validation requests.
        
        Args:
            message: Validation request message
        """
        if not self.is_running:
            logger.debug("ReasonerAgent not running, ignoring validation request")
            return
        
        try:
            # Extract request data
            triples = message.get("triples", [])
            ontology_version_id = message.get("ontology_version_id", "unknown")
            request_id = message.get("request_id", "unknown")
            
            logger.info(f"Processing validation request {request_id}: "
                       f"{len(triples)} triples, version {ontology_version_id}")
            
            # Convert message triples to Triple objects if needed
            if triples and isinstance(triples[0], dict):
                triples = [
                    Triple(
                        subject=t["subject"],
                        predicate=t["predicate"],
                        object=t["object"],
                        tenant_id=self.tenant_id
                    )
                    for t in triples
                ]
            
            # Perform validation
            validation_report = self._validate_with_circuit_breaker(
                triples=triples,
                ontology_version_id=ontology_version_id
            )
            
            # Publish validation results with request ID
            self._publish_validation_results(validation_report, "validation_request", request_id)
            
        except Exception as e:
            logger.exception(f"Error handling validation request: {str(e)}")
            self._publish_validation_error(str(e))
    
    def _validate_with_circuit_breaker(
        self,
        triples: List[Triple],
        ontology_version_id: str
    ) -> ValidationReport:
        """Perform validation with circuit breaker protection.
        
        Args:
            triples: List of triples to validate
            ontology_version_id: Ontology version identifier
            
        Returns:
            ValidationReport with validation results
        """
        # Check circuit breaker state
        if not self.circuit_breaker.can_execute():
            logger.warning("Circuit breaker is OPEN, skipping validation")
            return self._create_circuit_breaker_report(ontology_version_id)
        
        # Use performance monitor if monitoring service is available
        if self.monitoring_service:
            with PerformanceMonitor(self.monitoring_service, "ontology_validation", "reasoning") as monitor:
                try:
                    # Perform validation with timeout
                    validation_report = self.ontology_validator.validate(
                        triples=triples,
                        ontology_version_id=ontology_version_id
                    )
                    
                    # Set monitoring details
                    monitor.set_details(
                        triples_count=len(triples),
                        is_consistent=validation_report.is_consistent,
                        violations_count=len(validation_report.violated_rules),
                        ontology_version=ontology_version_id
                    )
                    
                    # Record success
                    self.circuit_breaker.record_success()
                    self.validation_count += 1
                    self.last_validation_time = datetime.now()
                    
                    logger.info(f"Validation completed, "
                               f"consistent: {validation_report.is_consistent}, "
                               f"violations: {len(validation_report.violated_rules)}")
                    
                    return validation_report
                    
                except Exception as e:
                    # Record failure
                    self.circuit_breaker.record_failure()
                    monitor.set_details(error=str(e))
                    raise
        else:
            # Fallback without monitoring
            start_time = time.time()
            
            try:
                # Perform validation with timeout
                validation_report = self.ontology_validator.validate(
                    triples=triples,
                    ontology_version_id=ontology_version_id
                )
                
                # Record success
                self.circuit_breaker.record_success()
                self.validation_count += 1
                self.last_validation_time = datetime.now()
                
                # Log performance metrics
                duration = time.time() - start_time
                logger.info(f"Validation completed in {duration:.2f}s, "
                           f"consistent: {validation_report.is_consistent}, "
                           f"violations: {len(validation_report.violated_rules)}")
                
                return validation_report
            
            except Exception as e:
                # Record failure
                self.circuit_breaker.record_failure()
                
                duration = time.time() - start_time
                logger.exception(f"Validation failed after {duration:.2f}s: {str(e)}")
                
                # Return error report
                return self._create_error_report(ontology_version_id, str(e))
    
    def _create_circuit_breaker_report(self, ontology_version_id: str) -> ValidationReport:
        """Create validation report when circuit breaker is open.
        
        Args:
            ontology_version_id: Ontology version identifier
            
        Returns:
            ValidationReport indicating circuit breaker protection
        """
        return ValidationReport(
            tenant_id=self.tenant_id,
            is_consistent=False,
            violated_rules=[
                RuleViolation(
                    rule_id="CIRCUIT_BREAKER_OPEN",
                    violated_constraint="Reasoner availability",
                    violating_components=[],
                    severity="ERROR",
                    description="Reasoner agent circuit breaker is open due to repeated failures. "
                               "Validation is temporarily disabled for system protection.",
                    repair_suggestion=RepairSuggestion(
                        action="Wait for circuit breaker recovery",
                        description="The reasoner will automatically retry after the recovery timeout. "
                                   "Check system logs for underlying issues.",
                        confidence=0.9
                    )
                )
            ],
            unsat_classes=[],
            repair_suggestions=["Wait for reasoner recovery or contact system administrator"],
            explanation="Circuit breaker protection activated due to reasoner failures",
            ontology_version_id=ontology_version_id
        )
    
    def _create_error_report(self, ontology_version_id: str, error_message: str) -> ValidationReport:
        """Create validation report for errors.
        
        Args:
            ontology_version_id: Ontology version identifier
            error_message: Error message from validation failure
            
        Returns:
            ValidationReport indicating validation error
        """
        return ValidationReport(
            tenant_id=self.tenant_id,
            is_consistent=False,
            violated_rules=[
                RuleViolation(
                    rule_id="VALIDATION_ERROR",
                    violated_constraint="Validation process",
                    violating_components=[],
                    severity="ERROR",
                    description=f"Validation process failed: {error_message}",
                    repair_suggestion=RepairSuggestion(
                        action="Check system logs and contact administrator",
                        description="The validation process encountered an unexpected error. "
                                   "Review system logs for detailed error information.",
                        confidence=0.8
                    )
                )
            ],
            unsat_classes=[],
            repair_suggestions=[f"Validation error: {error_message}"],
            explanation=f"Validation failed due to system error: {error_message}",
            ontology_version_id=ontology_version_id
        )
    
    def _publish_validation_results(
        self,
        validation_report: ValidationReport,
        event_type: str,
        request_id: Optional[str] = None
    ) -> None:
        """Publish validation results to message bus.
        
        Args:
            validation_report: Validation results to publish
            event_type: Type of event that triggered validation
            request_id: Optional request identifier for tracking
        """
        message = {
            "event_type": "validation_completed",
            "trigger_event": event_type,
            "validation_report": {
                "is_consistent": validation_report.is_consistent,
                "violated_rules": [
                    {
                        "rule_id": rule.rule_id,
                        "violated_constraint": rule.violated_constraint,
                        "violating_components": rule.violating_components,
                        "severity": rule.severity,
                        "description": rule.description,
                        "repair_suggestion": {
                            "action": rule.repair_suggestion.action,
                            "description": rule.repair_suggestion.description,
                            "confidence": rule.repair_suggestion.confidence
                        }
                    }
                    for rule in validation_report.violated_rules
                ],
                "unsat_classes": validation_report.unsat_classes,
                "repair_suggestions": validation_report.repair_suggestions,
                "explanation": validation_report.explanation,
                "ontology_version_id": validation_report.ontology_version_id,
                "timestamp": validation_report.timestamp.isoformat() if validation_report.timestamp else None
            },
            "agent_info": {
                "agent_type": "reasoner",
                "validation_count": self.validation_count,
                "circuit_breaker_state": self.circuit_breaker.state.value
            },
            "tenant_id": self.tenant_id,
            "timestamp": datetime.now().isoformat()
        }
        
        if request_id:
            message["request_id"] = request_id
        
        # Publish to validation results topic
        self.message_bus.publish(
            topic="validation.completed",
            message=message,
            tenant_id=self.tenant_id,
            idempotency_key=f"validation_{validation_report.ontology_version_id}_{int(time.time())}"
        )
        
        # Also publish to agent coordination topic for other agents
        self.message_bus.publish(
            topic="agent.coordination",
            message={
                "agent_type": "reasoner",
                "action": "validation_completed",
                "validation_report": message["validation_report"],
                "tenant_id": self.tenant_id,
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=self.tenant_id
        )
        
        logger.info(f"Published validation results: consistent={validation_report.is_consistent}, "
                   f"violations={len(validation_report.violated_rules)}")
    
    def _publish_validation_error(self, error_message: str) -> None:
        """Publish validation error to message bus.
        
        Args:
            error_message: Error message to publish
        """
        self.message_bus.publish(
            topic="validation.error",
            message={
                "agent_type": "reasoner",
                "error_message": error_message,
                "circuit_breaker_state": self.circuit_breaker.state.value,
                "tenant_id": self.tenant_id,
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=self.tenant_id
        )
        
        logger.error(f"Published validation error: {error_message}")
    
    def _provide_validation_context(self, validation_report: Dict[str, Any]) -> None:
        """Provide validation context to other agents.
        
        Args:
            validation_report: Validation report to provide context for
        """
        try:
            # Publish validation context for other agents
            self.message_bus.publish(
                topic="agent.coordination",
                message={
                    "agent_type": "reasoner",
                    "action": "validation_context_provided",
                    "validation_context": {
                        "is_consistent": validation_report.get("is_consistent", False),
                        "violation_count": len(validation_report.get("violated_rules", [])),
                        "circuit_breaker_state": self.circuit_breaker.state.value,
                        "validation_count": self.validation_count
                    },
                    "tenant_id": self.tenant_id,
                    "timestamp": datetime.now().isoformat()
                },
                tenant_id=self.tenant_id
            )
            
            logger.info("Provided validation context to other agents")
            
        except Exception as e:
            logger.exception(f"Error providing validation context: {str(e)}")
    
    def _trigger_revalidation(self, triples: List[Dict[str, Any]]) -> None:
        """Trigger revalidation after generation agent changes.
        
        Args:
            triples: New triples to validate
        """
        try:
            # Convert dict triples to Triple objects
            triple_objects = [
                Triple(
                    subject=t["subject"],
                    predicate=t["predicate"],
                    object=t["object"],
                    tenant_id=self.tenant_id
                )
                for t in triples
            ]
            
            # Trigger validation
            validation_report = self._validate_with_circuit_breaker(
                triples=triple_objects,
                ontology_version_id="post_generation"
            )
            
            # Publish results
            self._publish_validation_results(validation_report, "post_generation_validation")
            
            logger.info(f"Triggered revalidation after generation: {len(triples)} triples")
            
        except Exception as e:
            logger.exception(f"Error triggering revalidation: {str(e)}")
    
    def _publish_workflow_validation_results(
        self,
        validation_report: ValidationReport,
        workflow_id: str,
        workflow_type: str
    ) -> None:
        """Publish workflow validation results.
        
        Args:
            validation_report: Validation results
            workflow_id: Workflow identifier
            workflow_type: Type of workflow
        """
        try:
            message = {
                "event_type": "workflow_validation_completed",
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "validation_report": {
                    "is_consistent": validation_report.is_consistent,
                    "violated_rules": [
                        {
                            "rule_id": rule.rule_id,
                            "violated_constraint": rule.violated_constraint,
                            "violating_components": rule.violating_components,
                            "severity": rule.severity,
                            "description": rule.description,
                            "repair_suggestion": {
                                "action": rule.repair_suggestion.action,
                                "description": rule.repair_suggestion.description,
                                "confidence": rule.repair_suggestion.confidence
                            }
                        }
                        for rule in validation_report.violated_rules
                    ],
                    "unsat_classes": validation_report.unsat_classes,
                    "repair_suggestions": validation_report.repair_suggestions,
                    "explanation": validation_report.explanation,
                    "ontology_version_id": validation_report.ontology_version_id,
                    "timestamp": validation_report.timestamp.isoformat() if validation_report.timestamp else None
                },
                "agent_info": {
                    "agent_type": "reasoner",
                    "validation_count": self.validation_count,
                    "circuit_breaker_state": self.circuit_breaker.state.value
                },
                "tenant_id": self.tenant_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Publish to workflow-specific topic
            self.message_bus.publish(
                topic=f"workflows.validation.{workflow_id}.completed",
                message=message,
                tenant_id=self.tenant_id,
                idempotency_key=f"workflow_validation_{workflow_id}_{int(time.time())}"
            )
            
            # Also publish to general workflow topic
            self.message_bus.publish(
                topic="workflows.validation.completed",
                message=message,
                tenant_id=self.tenant_id
            )
            
            logger.info(f"Published workflow validation results for {workflow_id}")
            
        except Exception as e:
            logger.exception(f"Error publishing workflow validation results: {str(e)}")
    
    def _publish_workflow_validation_error(self, workflow_id: str, error_message: str) -> None:
        """Publish workflow validation error.
        
        Args:
            workflow_id: Workflow identifier
            error_message: Error message
        """
        try:
            self.message_bus.publish(
                topic=f"workflows.validation.{workflow_id}.failed",
                message={
                    "event_type": "workflow_validation_failed",
                    "workflow_id": workflow_id,
                    "agent_type": "reasoner",
                    "error_message": error_message,
                    "circuit_breaker_state": self.circuit_breaker.state.value,
                    "tenant_id": self.tenant_id,
                    "timestamp": datetime.now().isoformat()
                },
                tenant_id=self.tenant_id
            )
            
            logger.error(f"Published workflow validation error for {workflow_id}: {error_message}")
            
        except Exception as e:
            logger.exception(f"Error publishing workflow validation error: {str(e)}")


def create_reasoner_agent(
    message_bus: MessageBusPort,
    ontology_validator: OntologyValidatorPort,
    agent_coordinator: Optional[AgentCoordinator] = None,
    tenant_id: str = "default",
    failure_threshold: int = 5,
    recovery_timeout: int = 60
) -> ReasonerAgent:
    """Factory function to create a reasoner agent with default configuration.
    
    Args:
        message_bus: Message bus for event communication
        ontology_validator: Validator for ontology reasoning
        agent_coordinator: Optional agent coordinator for workflow integration
        tenant_id: Tenant identifier for multi-tenant isolation
        failure_threshold: Number of failures before opening circuit breaker
        recovery_timeout: Seconds before attempting recovery
        
    Returns:
        Configured ReasonerAgent instance
    """
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout
    )
    
    return ReasonerAgent(
        message_bus=message_bus,
        ontology_validator=ontology_validator,
        agent_coordinator=agent_coordinator,
        circuit_breaker_config=circuit_breaker_config,
        tenant_id=tenant_id
    )