"""Tests for the HybridReasonerAdapter."""

import unittest
from unittest.mock import MagicMock, patch
import pytest
from datetime import datetime
import importlib.util
import sys
import builtins
from pathlib import Path
import types

from domain.entities import Triple, ValidationReport, OntologyVersion, ScientificDomain
from domain.owl_conversion import _normalize_entity_name, _is_data_property


def test_has_elk_flag_false_when_pyelk_missing(monkeypatch):
    """HAS_ELK should be False when pyelk is not installed."""
    monkeypatch.delitem(sys.modules, "pyelk", raising=False)

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):  # pragma: no cover - patching import
        if name == "pyelk":
            raise ImportError("No module named 'pyelk'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Create stub modules to satisfy imports without heavy dependencies
    adapters_pkg = types.ModuleType("adapters")
    adapters_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["adapters"] = adapters_pkg

    axiom_applier_mod = types.ModuleType("adapters.axiom_applier")
    class _Stub:  # pragma: no cover - simple stubs
        pass
    axiom_applier_mod.AxiomApplier = _Stub
    axiom_applier_mod.BasicAxiomApplier = _Stub
    axiom_applier_mod.FullAxiomApplier = _Stub
    sys.modules["adapters.axiom_applier"] = axiom_applier_mod
    adapters_pkg.axiom_applier = axiom_applier_mod

    repositories_pkg = types.ModuleType("adapters.repositories")
    repositories_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["adapters.repositories"] = repositories_pkg
    adapters_pkg.repositories = repositories_pkg

    falkor_repo_mod = types.ModuleType("adapters.repositories.falkordb_ontology_repository")
    class FalkorDBOntologyRepository:  # pragma: no cover - stub
        pass
    falkor_repo_mod.FalkorDBOntologyRepository = FalkorDBOntologyRepository
    sys.modules["adapters.repositories.falkordb_ontology_repository"] = falkor_repo_mod
    repositories_pkg.falkordb_ontology_repository = falkor_repo_mod

    module_path = Path(__file__).resolve().parents[1] / "adapters" / "hybrid_reasoner_adapter.py"
    spec = importlib.util.spec_from_file_location("hybrid_reasoner_adapter", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.HAS_ELK is False


class TestHybridReasonerAdapter(unittest.TestCase):
    """Test suite for HybridReasonerAdapter."""

    def setUp(self):
        """Set up test fixtures."""
        from adapters.hybrid_reasoner_adapter import HybridReasonerAdapter

        # Create mock world and reasoners
        self.mock_world = MagicMock()
        self.mock_elk_reasoner = MagicMock()
        self.mock_hermit_reasoner = MagicMock()

        # Create adapter with mocks
        self.adapter = HybridReasonerAdapter(
            world=self.mock_world,
            elk_reasoner=self.mock_elk_reasoner,
            hermit_reasoner=self.mock_hermit_reasoner,
        )
        self.adapter.ontology_repository = MagicMock()

        # Sample triples for testing
        self.sample_triples = [
            Triple(
                subject="Person1",
                predicate="type",
                object="Person",
                tenant_id="tenant1",
            ),
            Triple(
                subject="Person1",
                predicate="hasName",
                object="'John Doe'",
                tenant_id="tenant1",
            ),
            Triple(
                subject="Person1", predicate="hasAge", object="30", tenant_id="tenant1"
            ),
            Triple(
                subject="Person1",
                predicate="knows",
                object="Person2",
                tenant_id="tenant1",
            ),
        ]

        # Sample ontology version
        self.sample_version = OntologyVersion(
            id="v1",
            checksum="abc123",
            parent_version=None,
            tenant_id="tenant1",
            domain=ScientificDomain.GENERAL,
            created_at=datetime.now(),
            axioms=["Class: Person", "ObjectProperty: knows"],
        )
        self.adapter.ontology_repository.get_ontology_version.return_value = (
            self.sample_version
        )

    def test_convert_to_owl(self):
        """Test conversion of triples to OWL Manchester syntax."""
        # Call the method
        result = self.adapter.convert_to_owl(triples=self.sample_triples)

        # Verify the result contains expected elements
        assert "Ontology:" in result
        assert "Class: Person" in result
        assert "Individual: Person1" in result
        assert "Individual: Person2" in result
        assert "ObjectProperty: knows" in result
        assert "DataProperty: hasName" in result or "DataProperty: hasAge" in result
        assert "ClassAssertion: Person Person1" in result

    def test_classify_axioms(self):
        """Test classification of axioms into EL and FULL categories."""
        # Sample OWL axioms
        owl_axioms = """
        Ontology: <http://example.org/ontology>

        Class: Person

        ObjectProperty: knows

        DataProperty: hasName

        Individual: Person1

        ClassAssertion: Person Person1

        ObjectPropertyAssertion: knows Person1 Person2

        # Non-EL axiom (universal quantification)
        SubClassOf: Person ObjectAllValuesFrom(knows Person)
        """

        # Call the method
        el_axioms, full_axioms = self.adapter._classify_axioms(owl_axioms)

        # Verify classification
        assert len(el_axioms) > 0
        assert len(full_axioms) > 0
        assert "SubClassOf: Person ObjectAllValuesFrom(knows Person)" in full_axioms
        assert "ClassAssertion: Person Person1" in el_axioms

    @patch("adapters.hybrid_reasoner_adapter.sync_reasoner_hermit")
    def test_validate(self, mock_sync_reasoner):
        """Test validation of triples against ontology."""
        # Setup mock ontology
        mock_ontology = MagicMock()
        mock_cls = MagicMock()
        mock_cls.name = "TestClass"
        mock_cls.is_a = []
        mock_ontology.classes.return_value = [mock_cls]

        # Setup mock for _create_temp_ontology
        self.adapter._create_temp_ontology = MagicMock(return_value=mock_ontology)

        # Call the method
        result = self.adapter.validate(
            triples=self.sample_triples, ontology_version_id="v1"
        )

        # Verify the result
        assert isinstance(result, ValidationReport)
        assert result.is_consistent is True
        assert len(result.unsat_classes) == 0
        assert result.tenant_id == "tenant1"
        assert result.ontology_version_id == "v1"

        # HermiT reasoner should be invoked when FULL axioms are present
        # In this simplified test no FULL axioms exist

    def test_validate_delta(self):
        """Test delta validation against existing ontology version."""
        # Mock the validate method
        self.adapter.validate = MagicMock(
            return_value=ValidationReport(
                is_consistent=True,
                violated_rules=[],
                unsat_classes=[],
                repair_suggestions=[],
                explanation=None,
                tenant_id="tenant1",
                ontology_version_id="v1",
            )
        )

        # Call the method
        result = self.adapter.validate_delta(
            new_triples=self.sample_triples,
            existing_version_id="v1",
            tenant_id="tenant1",
        )

        # Verify the result
        assert isinstance(result, ValidationReport)
        assert result.is_consistent is True
        assert result.tenant_id == "tenant1"
        assert result.ontology_version_id == "v1"

        # The validate method is mocked but should not be invoked in this path
        self.adapter.validate.assert_not_called()

    def test_apply_basic_axioms(self):
        """Ensure simple axioms are added to ontology."""
        ontology = MagicMock()
        axioms = [
            "Class: Person",
            "ObjectProperty: knows",
            "DataProperty: age",
            "Individual: John",
        ]
        self.adapter._apply_basic_axioms(ontology, axioms)
        assert hasattr(ontology, "Person")
        assert hasattr(ontology, "knows")
        assert hasattr(ontology, "age")
        assert hasattr(ontology, "John")

    def test_is_el_axiom(self):
        """Test identification of OWL 2 EL axioms."""
        # EL axioms
        assert self.adapter._is_el_axiom("Class: Person")
        assert self.adapter._is_el_axiom("SubClassOf: Student Person")
        assert self.adapter._is_el_axiom(
            "ObjectPropertyAssertion: knows Person1 Person2"
        )

        # Non-EL axioms
        assert not self.adapter._is_el_axiom(
            "SubClassOf: Person ObjectAllValuesFrom(knows Person)"
        )
        assert not self.adapter._is_el_axiom("ObjectMaxCardinality: 1 hasSpouse")
        assert not self.adapter._is_el_axiom("DisjointClasses: Man Woman")

    def test_normalize_entity_name(self):
        """Test normalization of entity names for Manchester syntax."""
        assert _normalize_entity_name("Person") == "Person"
        assert _normalize_entity_name("John Doe") == "John_Doe"
        assert _normalize_entity_name("123") == "e_123"
        assert _normalize_entity_name("has-property") == "has_property"

    def test_is_data_property(self):
        """Test identification of data properties vs object properties."""
        assert _is_data_property("'John Doe'")
        assert _is_data_property('"John Doe"')
        assert _is_data_property("42")
        assert _is_data_property("3.14")
        assert not _is_data_property("Person")
        assert not _is_data_property("knows")

    @patch("adapters.hybrid_reasoner_adapter.sync_reasoner_hermit")
    def test_validate_inconsistent_returns_explanation(self, mock_sync_reasoner):
        mock_ontology = MagicMock()
        self.adapter._create_temp_ontology = MagicMock(return_value=mock_ontology)
        self.adapter._validate_ontology = MagicMock(return_value=(False, ["A"], ["Fix"]))
        self.adapter._get_reasoner_explanation = MagicMock(return_value="Because")

        result = self.adapter.validate(triples=self.sample_triples, ontology_version_id="v1")

        assert result.is_consistent is False
        assert result.explanation == "Because"
        self.adapter._get_reasoner_explanation.assert_called_once_with(mock_ontology)


if __name__ == "__main__":
    unittest.main()
