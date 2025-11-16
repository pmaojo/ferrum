# Package alias to support imports used in tests
from domain.services.semantic_knowledge_base import (
    SemanticKnowledgeBase,
    KnowledgeQuery,
    KnowledgeQueryType,
    KnowledgeResult,
    ArchitecturalInsight,
)

from domain.services.architectural_pattern_library import (
    ArchitecturalPattern,
    PatternCategory,
    PatternComplexity,
)

from domain.services.best_practices_knowledge_graph import (
    BestPractice,
    PracticeType,
    PracticeContext,
)

from domain.entities.architectural_component import (
    ArchitecturalComponent,
    ComponentType,
    ComponentRelationship,
)

# Backward-compatible alias compatible with tests
class Relationship(ComponentRelationship):
    def __init__(self, subject_iri: str = None, predicate_iri: str = None, object_iri: str = None, relationship_type: str = None, **kwargs):
        src = subject_iri or kwargs.get('source_iri', '')
        tgt = object_iri or kwargs.get('target_iri', '')
        rel_type = relationship_type or (predicate_iri.split('#')[-1] if isinstance(predicate_iri, str) else '')
        props = kwargs.get('properties', {})
        super().__init__(source_iri=src, target_iri=tgt, relationship_type=rel_type, properties=props)
        # Expose legacy attribute names expected by other code/tests
        self.subject_iri = src
        self.object_iri = tgt
        self.predicate_iri = predicate_iri or rel_type

# Provide deep import compatibility by aliasing modules under PermaGraph.*
import importlib as _importlib
import logging as _logging
import sys as _sys

_aliases = {
    'PermaGraph.domain': 'domain',
    'PermaGraph.domain.services': 'domain.services',
    'PermaGraph.domain.entities': 'domain.entities',
    'PermaGraph.domain.services.semantic_knowledge_base': 'domain.services.semantic_knowledge_base',
    'PermaGraph.domain.services.architectural_pattern_library': 'domain.services.architectural_pattern_library',
    'PermaGraph.domain.services.best_practices_knowledge_graph': 'domain.services.best_practices_knowledge_graph',
    'PermaGraph.domain.entities.architectural_component': 'domain.entities.architectural_component',
}

_critical_aliases = {
    'PermaGraph.domain.services.semantic_knowledge_base',
    'PermaGraph.domain.entities.architectural_component',
}

_logger = _logging.getLogger(__name__)

for _alias, _target in _aliases.items():
    try:
        _mod = _importlib.import_module(_target)
        # Ensure compatibility symbol for Relationship
        if _target == 'domain.entities.architectural_component':
            setattr(_mod, 'Relationship', Relationship)
        _sys.modules[_alias] = _mod
    except Exception:
        _logger.exception("Failed to import '%s' for alias '%s'", _target, _alias)
        if _alias in _critical_aliases:
            raise
        # Best-effort aliasing; tests may not need all modules
