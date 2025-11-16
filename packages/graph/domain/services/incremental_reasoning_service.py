"""
Incremental Reasoning Service for Performance Optimization

This service implements incremental reasoning to handle large projects efficiently
by only re-reasoning over changed parts of the ontology.
"""

from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from abc import ABC, abstractmethod

from domain.entities.validation_report import ValidationReport
from domain.entities.graph_delta import GraphDelta
from application.ports.ontology_adapter import OntologyAdapter


@dataclass
class ReasoningCache:
    """Cache entry for reasoning results"""
    ontology_hash: str
    validation_report: ValidationReport
    timestamp: datetime
    affected_modules: Set[str]


@dataclass
class IncrementalContext:
    """Context for incremental reasoning operations"""
    changed_modules: Set[str]
    affected_dependencies: Set[str]
    reasoning_scope: Set[str]
    cache_hits: int = 0
    cache_misses: int = 0


class IncrementalReasoningPort(ABC):
    """Port for incremental reasoning operations"""
    
    @abstractmethod
    def compute_reasoning_scope(self, delta: GraphDelta) -> Set[str]:
        """Compute the minimal scope for reasoning based on changes"""
        pass
    
    @abstractmethod
    def validate_incremental(self, scope: Set[str]) -> ValidationReport:
        """Validate only the specified scope"""
        pass


class IncrementalReasoningService:
    """
    Service that implements incremental reasoning for large ontologies.
    
    Key optimizations:
    1. Dependency tracking to minimize reasoning scope
    2. Result caching to avoid redundant computations
    3. Modular validation to isolate changes
    4. Background processing for non-critical validations
    """
    
    def __init__(self, ontology_adapter: OntologyAdapter, reasoning_port: IncrementalReasoningPort):
        self.ontology_port = ontology_adapter
        self.reasoning_port = reasoning_port
        self.reasoning_cache: Dict[str, ReasoningCache] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        self.module_hashes: Dict[str, str] = {}
        
    def compute_reasoning_scope(self, delta: GraphDelta) -> Set[str]:
        """Compute reasoning scope from a graph delta.

        The scope contains all modules that were directly changed in the delta
        plus any modules that depend on those modules according to the current
        dependency graph.
        """
        changed_modules = self._extract_changed_modules(delta)
        return self._compute_reasoning_scope(changed_modules)

    def validate_incremental(self, delta: GraphDelta) -> ValidationReport:
        """Validate ontology incrementally using a ``GraphDelta``.

        This method determines which modules are affected by the delta,
        re-validates only those modules and combines the results with any
        cached validation reports for unaffected modules.
        """
        context = IncrementalContext(
            changed_modules=self._extract_changed_modules(delta),
            affected_dependencies=set(),
            reasoning_scope=set(),
        )

        # Determine reasoning scope based on dependencies
        context.reasoning_scope = self._compute_reasoning_scope(context.changed_modules)
        context.affected_dependencies = self._get_affected_dependencies(
            context.changed_modules
        )

        cached_results = self._get_cached_results(context)

        if context.reasoning_scope:
            new_results = self.reasoning_port.validate_incremental(
                context.reasoning_scope
            )
            self._update_cache(context.reasoning_scope, new_results)

            if cached_results:
                return self._merge_validation_results(cached_results, new_results)
            return new_results

        if cached_results:
            return cached_results

        return ValidationReport(
            is_consistent=True,
            violated_rules=[],
            unsat_classes=[],
            repair_suggestions=[],
            explanation="No changes detected",
            timestamp=datetime.now(),
        )
    
    def _extract_changed_modules(self, delta: GraphDelta) -> Set[str]:
        """Extract module names affected by a ``GraphDelta``."""
        changed_modules: Set[str] = set()

        # Handle component changes first – these contain explicit namespace info
        for change in delta.component_changes:
            if change.component and getattr(change.component, "namespace", None):
                changed_modules.add(self._module_from_namespace(change.component.namespace))
            if change.previous_component and getattr(change.previous_component, "namespace", None):
                changed_modules.add(
                    self._module_from_namespace(change.previous_component.namespace)
                )

        # Relationship changes reference components by IRIs.  Derive module
        # names from those IRIs where possible.
        for change in delta.relationship_changes:
            rel = change.relationship
            module = self._extract_module_from_iri(rel.subject_iri)
            if module:
                changed_modules.add(module)
            module = self._extract_module_from_iri(rel.object_iri)
            if module:
                changed_modules.add(module)

            if change.previous_relationship:
                prev = change.previous_relationship
                module = self._extract_module_from_iri(prev.subject_iri)
                if module:
                    changed_modules.add(module)
                module = self._extract_module_from_iri(prev.object_iri)
                if module:
                    changed_modules.add(module)

        return changed_modules

    def _module_from_namespace(self, namespace: str) -> str:
        """Derive module name from a component namespace."""
        return namespace.split(".")[0] if "." in namespace else namespace
    
    def _compute_reasoning_scope(self, changed_modules: Set[str]) -> Set[str]:
        """Compute minimal scope for reasoning based on dependency graph"""
        scope = set(changed_modules)
        
        # Add direct dependencies
        for module in changed_modules:
            if module in self.dependency_graph:
                scope.update(self.dependency_graph[module])
        
        # Add reverse dependencies (modules that depend on changed modules)
        for module, deps in self.dependency_graph.items():
            if deps.intersection(changed_modules):
                scope.add(module)
        
        return scope
    
    def _get_affected_dependencies(self, changed_modules: Set[str]) -> Set[str]:
        """Get all modules affected by changes (transitive closure)"""
        affected = set(changed_modules)
        queue = list(changed_modules)
        
        while queue:
            current = queue.pop(0)
            
            # Add modules that depend on current
            for module, deps in self.dependency_graph.items():
                if current in deps and module not in affected:
                    affected.add(module)
                    queue.append(module)
        
        return affected
    
    def _get_cached_results(self, context: IncrementalContext) -> Optional[ValidationReport]:
        """Get cached validation results for unchanged modules"""
        cached_reports = []
        
        for module in self.module_hashes:
            if module not in context.reasoning_scope:
                module_hash = self._compute_module_hash(module)
                if module_hash == self.module_hashes[module] and module_hash in self.reasoning_cache:
                    cached_reports.append(self.reasoning_cache[module_hash].validation_report)
                    context.cache_hits += 1
                else:
                    context.cache_misses += 1
        
        if cached_reports:
            return self._merge_validation_reports(cached_reports)
        
        return None
    
    def _update_cache(self, scope: Set[str], validation_report: ValidationReport):
        """Update reasoning cache with new results"""
        for module in scope:
            module_hash = self._compute_module_hash(module)
            self.module_hashes[module] = module_hash
            
            self.reasoning_cache[module_hash] = ReasoningCache(
                ontology_hash=module_hash,
                validation_report=validation_report,
                timestamp=datetime.now(),
                affected_modules={module}
            )
    
    def _compute_module_hash(self, module: str) -> str:
        """Compute hash for module content to detect changes"""
        try:
            # Get module triples from ontology
            module_triples = self.ontology_port.get_module_triples(module)
            content = json.dumps(sorted(module_triples), sort_keys=True)
            return hashlib.sha256(content.encode()).hexdigest()
        except Exception:
            # Fallback to timestamp-based hash
            return hashlib.sha256(f"{module}_{datetime.now().isoformat()}".encode()).hexdigest()
    
    def _extract_module_from_iri(self, iri: str) -> Optional[str]:
        """Extract module name from IRI"""
        if '#' in iri:
            parts = iri.split('#')[-1].split('_')
            if len(parts) > 1:
                return parts[0]  # Assume first part is module name
        return None
    
    def _merge_validation_results(self, cached: ValidationReport, new: ValidationReport) -> ValidationReport:
        """Merge cached and new validation results"""
        return ValidationReport(
            is_consistent=cached.is_consistent and new.is_consistent,
            violated_rules=cached.violated_rules + new.violated_rules,
            unsat_classes=list(set(cached.unsat_classes + new.unsat_classes)),
            repair_suggestions=cached.repair_suggestions + new.repair_suggestions,
            explanation=f"Cached: {cached.explanation}; New: {new.explanation}",
            timestamp=new.timestamp
        )
    
    def _merge_validation_reports(self, reports: List[ValidationReport]) -> ValidationReport:
        """Merge multiple validation reports"""
        if not reports:
            return ValidationReport(
                is_consistent=True,
                violated_rules=[],
                unsat_classes=[],
                repair_suggestions=[],
                explanation="No reports to merge",
                timestamp=datetime.now()
            )
        
        merged = reports[0]
        for report in reports[1:]:
            merged = self._merge_validation_results(merged, report)
        
        return merged
    
    def update_dependency_graph(self, dependencies: Dict[str, Set[str]]):
        """Update the module dependency graph"""
        self.dependency_graph = dependencies
    
    def clear_cache(self):
        """Clear all cached reasoning results"""
        self.reasoning_cache.clear()
        self.module_hashes.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache performance statistics"""
        return {
            'cache_entries': len(self.reasoning_cache),
            'cached_modules': len(self.module_hashes),
            'dependency_edges': sum(len(deps) for deps in self.dependency_graph.values())
        }