"""Integration tests for the hybrid reasoning system with architectural validation rules."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from domain.entities import Triple, ValidationReport, RuleViolation, RepairSuggestion
from adapters.hybrid_reasoner_adapter import HybridReasonerAdapter
from domain.services.validation_rules_engine import ValidationRulesEngine


class TestHybridReasoningIntegration:
    """Integration tests for hybrid reasoning with architectural validation."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock world and reasoners
        self.mock_world = MagicMock()
        self.mock_elk_reasoner = MagicMock()
        self.mock_hermit_reasoner = MagicMock()

        # Create validation rules engine
        self.validation_rules_engine = ValidationRulesEngine()

        # Create adapter with validation rules engine
        self.adapter = HybridReasonerAdapter(
            world=self.mock_world,
            elk_reasoner=self.mock_elk_reasoner,
            hermit_reasoner=self.mock_hermit_reasoner,
            validation_rules_engine=self.validation_rules_engine,
        )
        
        self.tenant_id = "test_tenant"
        self.ontology_version_id = "test_version"

    def test_dip_violation_detected_in_hybrid_validation(self):
        """Test that DIP violations are detected during hybrid validation."""
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

        # Mock the ontology validation to return consistent
        self.adapter._validate_ontology = MagicMock(return_value=(True, [], []))
        self.adapter._create_temp_ontology = MagicMock()

        # Run validation
        result = self.adapter.validate(
            triples=triples,
            ontology_version_id=self.ontology_version_id
        )

        # Should detect DIP violation and mark as inconsistent
        assert not result.is_consistent
        assert len(result.violated_rules) == 1
        
        violation = result.violated_rules[0]
        assert violation.rule_id == "DIP_VIOLATION"
        assert violation.severity == "HIGH"
        assert "UserService" in violation.description
        assert "DatabaseAdapter" in violation.description

    def test_bounded_context_violation_detected_in_hybrid_validation(self):
        """Test that bounded context violations are detected during hybrid validation."""
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

        # Mock the ontology validation to return consistent
        self.adapter._validate_ontology = MagicMock(return_value=(True, [], []))
        self.adapter._create_temp_ontology = MagicMock()

        # Run validation
        result = self.adapter.validate(
            triples=triples,
            ontology_version_id=self.ontology_version_id
        )

        # Should detect bounded context violation
        assert not result.is_consistent
        assert len(result.violated_rules) == 1
        
        violation = result.violated_rules[0]
        assert violation.rule_id == "BOUNDED_CONTEXT_VIOLATION"
        assert violation.severity == "MEDIUM"
        assert "UserService" in violation.description
        assert "Order" in violation.description

    def test_aggregate_integrity_violation_detected_in_hybrid_validation(self):
        """Test that aggregate integrity violations are detected during hybrid validation."""
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

        # Mock the ontology validation to return consistent
        self.adapter._validate_ontology = MagicMock(return_value=(True, [], []))
        self.adapter._create_temp_ontology = MagicMock()

        # Run validation
        result = self.adapter.validate(
            triples=triples,
            ontology_version_id=self.ontology_version_id
        )

        # Should detect aggregate integrity violation
        assert not result.is_consistent
        assert len(result.violated_rules) == 1
        
        violation = result.violated_rules[0]
        assert violation.rule_id == "AGGREGATE_INTEGRITY_VIOLATION"
        assert violation.severity == "HIGH"
        assert "User" in violation.description
        assert "multiple aggregates" in violation.description

    def test_multiple_violations_detected_simultaneously(self):
        """Test that multiple architectural violations can be detected simultaneously."""
        triples = [
            # DIP violation setup
            Triple(
                subject="http://example.org/UserService",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#UseCase",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/DatabaseAdapter",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#Adapter",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/UserService",
                predicate="http://kthulu.io/ontology#calls",
                object="http://example.org/DatabaseAdapter",
                tenant_id=self.tenant_id
            ),
            # Aggregate integrity violation setup
            Triple(
                subject="http://example.org/User",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#DomainEntity",
                tenant_id=self.tenant_id
            ),
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

        # Mock the ontology validation to return consistent
        self.adapter._validate_ontology = MagicMock(return_value=(True, [], []))
        self.adapter._create_temp_ontology = MagicMock()

        # Run validation
        result = self.adapter.validate(
            triples=triples,
            ontology_version_id=self.ontology_version_id
        )

        # Should detect both violations
        assert not result.is_consistent
        assert len(result.violated_rules) == 2
        
        rule_ids = [v.rule_id for v in result.violated_rules]
        assert "DIP_VIOLATION" in rule_ids
        assert "AGGREGATE_INTEGRITY_VIOLATION" in rule_ids

    def test_reasoner_inconsistency_combined_with_architectural_violations(self):
        """Test that reasoner inconsistencies are combined with architectural violations."""
        triples = [
            # DIP violation
            Triple(
                subject="http://example.org/UserService",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#UseCase",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/DatabaseAdapter",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#Adapter",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/UserService",
                predicate="http://kthulu.io/ontology#calls",
                object="http://example.org/DatabaseAdapter",
                tenant_id=self.tenant_id
            )
        ]

        # Mock the ontology validation to return inconsistent
        self.adapter._validate_ontology = MagicMock(
            return_value=(False, ["UnsatisfiableClass"], ["Fix the class"])
        )
        self.adapter._create_temp_ontology = MagicMock()

        # Run validation
        result = self.adapter.validate(
            triples=triples,
            ontology_version_id=self.ontology_version_id
        )

        # Should detect both architectural and reasoner violations
        assert not result.is_consistent
        assert len(result.violated_rules) == 2
        
        rule_ids = [v.rule_id for v in result.violated_rules]
        assert "DIP_VIOLATION" in rule_ids
        assert "REASONER_INCONSISTENCY" in rule_ids

    def test_valid_architecture_passes_hybrid_validation(self):
        """Test that a valid architecture passes both reasoner and architectural validation."""
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
            # Correct relationship: UseCase uses Port (both domain components)
            Triple(
                subject="http://example.org/UserService",
                predicate="http://kthulu.io/ontology#usesPort",
                object="http://example.org/UserRepository",
                tenant_id=self.tenant_id
            )
        ]

        # Mock the ontology validation to return consistent
        self.adapter._validate_ontology = MagicMock(return_value=(True, [], []))
        self.adapter._create_temp_ontology = MagicMock()

        # Run validation
        result = self.adapter.validate(
            triples=triples,
            ontology_version_id=self.ontology_version_id
        )

        # Should pass validation
        assert result.is_consistent
        assert len(result.violated_rules) == 0

    def test_delta_validation_with_architectural_rules(self):
        """Test that delta validation includes architectural rule validation."""
        new_triples = [
            # Add a DIP violation in delta
            Triple(
                subject="http://example.org/UserService",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#UseCase",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/DatabaseAdapter",
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://kthulu.io/ontology#Adapter",
                tenant_id=self.tenant_id
            ),
            Triple(
                subject="http://example.org/UserService",
                predicate="http://kthulu.io/ontology#calls",
                object="http://example.org/DatabaseAdapter",
                tenant_id=self.tenant_id
            )
        ]

        # Mock the required methods
        self.adapter._get_ontology_version = MagicMock(return_value=MagicMock(
            id="existing_version",
            axioms=["Class: ExistingClass"]
        ))
        self.adapter._create_ontology_from_version = MagicMock()
        self.adapter._create_temp_ontology_with_base = MagicMock()
        self.adapter._validate_ontology = MagicMock(return_value=(True, [], []))

        # Run delta validation
        result = self.adapter.validate_delta(
            new_triples=new_triples,
            existing_version_id="existing_version",
            tenant_id=self.tenant_id
        )

        # Should detect DIP violation in delta
        assert not result.is_consistent
        assert len(result.violated_rules) == 1
        assert result.violated_rules[0].rule_id == "DIP_VIOLATION"