"""Example usage of ReasonerAgent with existing PermaGraph infrastructure.

This example demonstrates how to integrate the ReasonerAgent with the existing
PermaGraph system components for automated ontology validation.
"""

import logging
from datetime import datetime
from typing import List

from domain.agents.reasoner_agent import create_reasoner_agent
from domain.agent_coordinator import AgentCoordinator
from adapters.inmemory_message_bus_adapter import InMemoryMessageBusAdapter
from adapters.hybrid_reasoner_adapter import HybridReasonerAdapter
from domain.entities import Triple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_triples(tenant_id: str) -> List[Triple]:
    """Create sample triples for testing."""
    return [
        Triple(
            subject="http://example.org/auth/Module",
            predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            object="http://kthulu.io/ontology#Module",
            tenant_id=tenant_id
        ),
        Triple(
            subject="http://example.org/auth/CreateUserUseCase",
            predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            object="http://kthulu.io/ontology#UseCase",
            tenant_id=tenant_id
        ),
        Triple(
            subject="http://example.org/auth/Module",
            predicate="http://kthulu.io/ontology#definesUseCase",
            object="http://example.org/auth/CreateUserUseCase",
            tenant_id=tenant_id
        ),
        # Add a potential DIP violation for testing
        Triple(
            subject="http://example.org/auth/CreateUserUseCase",
            predicate="http://kthulu.io/ontology#calls",
            object="http://example.org/auth/DatabaseAdapter",
            tenant_id=tenant_id
        ),
        Triple(
            subject="http://example.org/auth/DatabaseAdapter",
            predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            object="http://kthulu.io/ontology#Adapter",
            tenant_id=tenant_id
        )
    ]


def main():
    """Demonstrate ReasonerAgent integration."""
    tenant_id = "example_tenant"
    
    print("🚀 Starting ReasonerAgent Integration Example")
    print("=" * 50)
    
    # 1. Initialize infrastructure components
    print("1. Initializing infrastructure components...")
    
    # Message bus for agent communication
    message_bus = InMemoryMessageBusAdapter()
    
    # Ontology validator (hybrid reasoner)
    ontology_validator = HybridReasonerAdapter()
    
    # Agent coordinator for workflow management
    agent_coordinator = AgentCoordinator(message_bus)
    
    print("   ✓ Message bus initialized")
    print("   ✓ Ontology validator initialized")
    print("   ✓ Agent coordinator initialized")
    
    # 2. Create and start ReasonerAgent
    print("\n2. Creating and starting ReasonerAgent...")
    
    reasoner_agent = create_reasoner_agent(
        message_bus=message_bus,
        ontology_validator=ontology_validator,
        agent_coordinator=agent_coordinator,
        tenant_id=tenant_id,
        failure_threshold=3,
        recovery_timeout=30
    )
    
    reasoner_agent.start()
    print("   ✓ ReasonerAgent created and started")
    
    # 3. Display agent status
    print("\n3. Agent Status:")
    status = reasoner_agent.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # 4. Simulate ontology change event
    print("\n4. Simulating ontology change event...")
    
    sample_triples = create_sample_triples(tenant_id)
    
    # Publish ontology change event
    ontology_change_event = {
        "event_type": "ontology_updated",
        "triples": [
            {
                "subject": triple.subject,
                "predicate": triple.predicate,
                "object": triple.object
            }
            for triple in sample_triples
        ],
        "ontology_version_id": f"version_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now().isoformat()
    }
    
    message_bus.publish(
        topic="ontology.changed",
        message=ontology_change_event,
        tenant_id=tenant_id,
        idempotency_key=f"change_{datetime.now().timestamp()}"
    )
    
    print("   ✓ Ontology change event published")
    print(f"   ✓ Event contains {len(sample_triples)} triples")
    
    # 5. Simulate validation request
    print("\n5. Simulating direct validation request...")
    
    validation_request = {
        "triples": [
            {
                "subject": triple.subject,
                "predicate": triple.predicate,
                "object": triple.object
            }
            for triple in sample_triples[:3]  # Use subset for direct validation
        ],
        "ontology_version_id": "direct_validation_test",
        "request_id": f"req_{datetime.now().timestamp()}"
    }
    
    message_bus.publish(
        topic="validation.requested",
        message=validation_request,
        tenant_id=tenant_id,
        idempotency_key=f"validation_{datetime.now().timestamp()}"
    )
    
    print("   ✓ Validation request published")
    
    # 6. Simulate workflow-based validation
    print("\n6. Simulating workflow-based validation...")
    
    workflow_validation = {
        "workflow_id": f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "workflow_type": "ontology_validation",
        "triples": [
            {
                "subject": triple.subject,
                "predicate": triple.predicate,
                "object": triple.object
            }
            for triple in sample_triples
        ],
        "ontology_version_id": "workflow_test"
    }
    
    message_bus.publish(
        topic="workflows.validation.start",
        message=workflow_validation,
        tenant_id=tenant_id,
        idempotency_key=f"workflow_{datetime.now().timestamp()}"
    )
    
    print("   ✓ Workflow validation published")
    
    # 7. Display final agent status
    print("\n7. Final Agent Status:")
    final_status = reasoner_agent.get_status()
    for key, value in final_status.items():
        print(f"   {key}: {value}")
    
    # 8. Demonstrate circuit breaker (optional)
    print("\n8. Circuit Breaker Status:")
    print(f"   State: {reasoner_agent.circuit_breaker.state.value}")
    print(f"   Failure Count: {reasoner_agent.circuit_breaker.failure_count}")
    print(f"   Success Count: {reasoner_agent.circuit_breaker.success_count}")
    
    # 9. Stop the agent
    print("\n9. Stopping ReasonerAgent...")
    reasoner_agent.stop()
    print("   ✓ ReasonerAgent stopped")
    
    print("\n" + "=" * 50)
    print("🎉 ReasonerAgent Integration Example Complete!")
    print("\nKey Features Demonstrated:")
    print("• Event-driven ontology validation")
    print("• Integration with existing agent coordination system")
    print("• Circuit breaker protection for reasoner failures")
    print("• Multi-tenant message bus communication")
    print("• Workflow-based validation support")
    print("• Real-time status monitoring")


if __name__ == "__main__":
    main()