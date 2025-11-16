"""Tests for the validation rules engine."""

import pytest
from datetime import datetime

from domain.entities import Triple
from domain.entities.validation_report import RuleViolation, RepairSuggestion
from domain.services.validation_rules_engine import (
    ValidationRulesEngine,
    ValidationContext,
    create_validation_context,
    RuleType
)


class TestValidationRulesEngine:
    """Test cases for the ValidationRulesEngine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ValidationRulesEngine()
        self.tenant_id = "test_tenant"
        self.ontology_version_id = "test_version"

    def test_dip_violation_detection(self):
        """Test detection of Dependency Inversion Principle violations."""
        # Create triples representing a DIP violation
        triples = [
            # Define a UseCase (domain component)
            Triple(
                subject="http://example.org/UserService",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#UseCase",
                tenant_id=self.tenant_id
            ),
            # Define an Adapter (infrastructure component)
            Triple(
                subject="http://example.org/DatabaseAdapter",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#Adapter",
                tenant_id=self.tenant_id
            ),
            # DIP violation: UseCase calls Adapter directly
            Triple(
                subject="http://example.org/UserService",
                predicate="http://kthulu.io/ontology#calls",
                object="http://example.org/DatabaseAdapter",
                tenant_id=self.tenant_id
            )
        ]

        context = create_validation_context(
            self.tenant_id, self.ontology_version_id, triples
        )
        violations = self.engine.validate_all_rules(context)

        # Should detect one DIP violation
        dip_violations = [v for v in violations if v.rule_id == "DIP_VIOLATION"]
        assert len(dip_violations) == 1
        
        violation = dip_violations[0]
        assert violation.severity == "HIGH"
        assert "UserService" in violation.description
        assert "DatabaseAdapter" in violation.description
        assert "port interface" in violation.repair_suggestion.action

    def test_no_dip_violation_with_port(self):
        """Test that no DIP violation is detected when using ports correctly."""
        triples = [
            # Define a UseCase (domain component)
            Triple(
                subject="http://example.org/UserService",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#UseCase",
                tenant_id=self.tenant_id
            ),
            # Define a Port (domain component)
            Triple(
                subject="http://example.org/UserRepository",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#Port",
                tenant_id=self.tenant_id
            ),
            # Correct: UseCase calls Port (both domain components)
            Triple(
                subject="http://example.org/UserService",
                predicate="http://kthulu.io/ontology#calls",
                object="http://example.org/UserRepository",
                tenant_id=self.tenant_id
            )
        ]

        context = create_validation_context(
            self.tenant_id, self.ontology_version_id, triples
        )
        violations = self.engine.validate_all_rules(context)

        # Should not detect any DIP violations
        dip_violations = [v for v in violations if v.rule_id == "DIP_VIOLATION"]
        assert len(dip_violations) == 0

    def test_bounded_context_violation_detection(self):
        """Test detection of bounded context violations."""
        triples = [
            # Define modules
            Triple(
                subject="http://example.org/UserModule",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#Module",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/OrderModule",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#Module",
                tenant_id=self.tenant_id
            ),
            # Define a UseCase in UserModule
            Triple(
                subject="http://example.org/UserService",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#UseCase",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/UserModule",
                predicate="http://kthulu.io/ontology#definesUseCase",
                object="http://example.org/UserService",
                tenant_id=self.tenant_id
            ),
            # Define an Entity in OrderModule
            Triple(
                subject="http://example.org/Order",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#DomainEntity",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/OrderModule",
                predicate="http://kthulu.io/ontology#hasEntity",
                object="http://example.org/Order",
                tenant_id=self.tenant_id
            ),
            # Bounded context violation: UseCase from UserModule uses Entity from OrderModule
            Triple(
                subject="http://example.org/UserService",
                predicate="http://kthulu.io/ontology#usesEntity",
                object="http://example.org/Order",
                tenant_id=self.tenant_id
            )
        ]

        context = create_validation_context(
            self.tenant_id, self.ontology_version_id, triples
        )
        violations = self.engine.validate_all_rules(context)

        # Should detect one bounded context violation
        bc_violations = [v for v in violations if v.rule_id == "BOUNDED_CONTEXT_VIOLATION"]
        assert len(bc_violations) == 1
        
        violation = bc_violations[0]
        assert violation.severity == "MEDIUM"
        assert "UserService" in violation.description
        assert "Order" in violation.description
        assert "domain events" in violation.repair_suggestion.action

    def test_aggregate_integrity_violation_detection(self):
        """Test detection of aggregate integrity violations."""
        triples = [
            # Define an entity
            Triple(
                subject="http://example.org/User",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#DomainEntity",
                tenant_id=self.tenant_id
            ),
            # Define two aggregates
            Triple(
                subject="http://example.org/UserAggregate",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#AggregateRoot",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/AccountAggregate",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#AggregateRoot",
                tenant_id=self.tenant_id
            ),
            # Aggregate integrity violation: Entity belongs to multiple aggregates
            Triple(
                subject="http://example.org/User",
                predicate="http://kthulu.io/ontology#partOfAggregate",
                object="http://example.org/UserAggregate",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/User",
                predicate="http://kthulu.io/ontology#partOfAggregate",
                object="http://example.org/AccountAggregate",
                tenant_id=self.tenant_id
            )
        ]

        context = create_validation_context(
            self.tenant_id, self.ontology_version_id, triples
        )
        violations = self.engine.validate_all_rules(context)

        # Should detect one aggregate integrity violation
        ai_violations = [v for v in violations if v.rule_id == "AGGREGATE_INTEGRITY_VIOLATION"]
        assert len(ai_violations) == 1
        
        violation = ai_violations[0]
        assert violation.severity == "HIGH"
        assert "User" in violation.description
        assert "multiple aggregates" in violation.description
        assert "Refactor entity ownership" in violation.repair_suggestion.action

    def test_no_violations_with_correct_architecture(self):
        """Test that no violations are detected with correct architecture."""
        triples = [
            # Define a module
            Triple(
                subject="http://example.org/UserModule",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#Module",
                tenant_id=self.tenant_id
            ),
            # Define a UseCase in the module
            Triple(
                subject="http://example.org/UserService",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#UseCase",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/UserModule",
                predicate="http://kthulu.io/ontology#definesUseCase",
                object="http://example.org/UserService",
                tenant_id=self.tenant_id
            ),
            # Define a Port in the module
            Triple(
                subject="http://example.org/UserRepository",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#Port",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/UserModule",
                predicate="http://kthulu.io/ontology#hasPort",
                object="http://example.org/UserRepository",
                tenant_id=self.tenant_id
            ),
            # Define an Entity in the module
            Triple(
                subject="http://example.org/User",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#DomainEntity",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/UserModule",
                predicate="http://kthulu.io/ontology#hasEntity",
                object="http://example.org/User",
                tenant_id=self.tenant_id
            ),
            # Define an Aggregate
            Triple(
                subject="http://example.org/UserAggregate",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#AggregateRoot",
                tenant_id=self.tenant_id
            ),
            # Correct relationships
            Triple(
                subject="http://example.org/UserService",
                predicate="http://kthulu.io/ontology#usesPort",
                object="http://example.org/UserRepository",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/UserService",
                predicate="http://kthulu.io/ontology#usesEntity",
                object="http://example.org/User",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/User",
                predicate="http://kthulu.io/ontology#partOfAggregate",
                object="http://example.org/UserAggregate",
                tenant_id=self.tenant_id
            )
        ]

        context = create_validation_context(
            self.tenant_id, self.ontology_version_id, triples
        )
        violations = self.engine.validate_all_rules(context)

        # Should not detect any violations
        assert len(violations) == 0

    def test_validation_context_creation(self):
        """Test creation of validation context."""
        triples = [
            Triple(
                subject="http://example.org/UserService",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#UseCase",
                tenant_id=self.tenant_id
            )
        ]

        context = create_validation_context(
            self.tenant_id, self.ontology_version_id, triples
        )

        assert context.tenant_id == self.tenant_id
        assert context.ontology_version_id == self.ontology_version_id
        assert context.triples == triples
        assert isinstance(context.component_types, dict)
        assert isinstance(context.calls_relationships, list)
        assert isinstance(context.module_memberships, dict)
        assert isinstance(context.entity_aggregates, dict)

    def test_component_name_extraction(self):
        """Test component name extraction from IRIs."""
        engine = ValidationRulesEngine()
        
        # Test with fragment identifier
        assert engine._get_component_name("http://example.org/ontology#UserService") == "UserService"
        
        # Test with path
        assert engine._get_component_name("http://example.org/ontology/UserService") == "UserService"
        
        # Test with simple name
        assert engine._get_component_name("UserService") == "UserService"

    def test_rule_engine_error_handling(self):
        """Test error handling in rule engine."""
        # Create a mock engine that will fail
        class FailingEngine(ValidationRulesEngine):
            def _validate_dip_rule(self, context):
                raise Exception("Test error")

        engine = FailingEngine()
        context = create_validation_context(
            self.tenant_id, self.ontology_version_id, []
        )
        
        violations = engine.validate_all_rules(context)
        
        # Should have one violation for the engine error
        error_violations = [v for v in violations if "ENGINE_ERROR" in v.rule_id]
        assert len(error_violations) == 1
        
        violation = error_violations[0]
        assert violation.severity == "ERROR"
        assert "Test error" in violation.description