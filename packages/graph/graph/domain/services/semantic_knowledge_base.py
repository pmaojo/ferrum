"""
Semantic Knowledge Base Service

Main service that integrates architectural pattern library, best practices
knowledge graph, pattern matching, and community knowledge sharing to provide
a comprehensive semantic knowledge base for software architecture.
"""

from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

from ..entities.architectural_component import ArchitecturalComponent
from ..entities.validation_report import ValidationReport
from .architectural_pattern_library import ArchitecturalPatternLibrary, ArchitecturalPattern, PatternCategory, PatternComplexity
from .best_practices_knowledge_graph import BestPracticesKnowledgeGraph, BestPractice, PracticeContext, PracticeType
from .pattern_matching_service import PatternMatchingService, PatternMatch, ImprovementSuggestion
from .community_knowledge_service import CommunityKnowledgeService, CommunityContribution


class KnowledgeQueryType(Enum):
    PATTERN_SEARCH = "pattern_search"
    PRACTICE_SEARCH = "practice_search"
    VIOLATION_ANALYSIS = "violation_analysis"
    IMPROVEMENT_SUGGESTIONS = "improvement_suggestions"
    COMMUNITY_CONTENT = "community_content"
    ARCHITECTURAL_GUIDANCE = "architectural_guidance"


@dataclass
class KnowledgeQuery:
    """Represents a query to the knowledge base"""
    query_type: KnowledgeQueryType
    query_text: str
    context: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    max_results: int = 10


@dataclass
class KnowledgeResult:
    """Result from a knowledge base query"""
    query_id: str
    result_type: str
    title: str
    description: str
    content: Dict[str, Any]
    relevance_score: float
    source: str  # "library", "community", "generated"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArchitecturalInsight:
    """High-level architectural insight derived from knowledge base"""
    id: str
    title: str
    description: str
    insight_type: str  # "pattern_opportunity", "violation_risk", "improvement_potential"
    confidence: float
    supporting_evidence: List[str]
    recommended_actions: List[str]
    related_patterns: List[str]
    related_practices: List[str]
    impact_assessment: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)


class SemanticKnowledgeBase:
    """Main semantic knowledge base service"""
    
    def __init__(self):
        # Initialize core components
        self.pattern_library = ArchitecturalPatternLibrary()
        self.practices_graph = BestPracticesKnowledgeGraph()
        self.pattern_matcher = PatternMatchingService(
            self.pattern_library, 
            self.practices_graph
        )
        self.community_service = CommunityKnowledgeService()
        
        # Query history and caching
        self.query_history: List[KnowledgeQuery] = []
        self.result_cache: Dict[str, List[KnowledgeResult]] = {}
        
        # Integrate community contributions
        self._integrate_community_knowledge()
    
    def _integrate_community_knowledge(self):
        """Integrate approved community contributions into the knowledge base"""
        
        # Add approved community patterns to the library
        community_patterns = self.community_service.export_approved_patterns()
        for pattern in community_patterns:
            self.pattern_library.add_pattern(pattern)
        
        # Add approved community practices to the graph
        community_practices = self.community_service.export_approved_practices()
        for practice in community_practices:
            self.practices_graph.add_practice(practice)
    
    def query_knowledge_base(self, query: KnowledgeQuery) -> List[KnowledgeResult]:
        """Main entry point for querying the knowledge base"""
        
        # Store query in history regardless of cache hits
        self.query_history.append(query)
        
        # Check cache
        cache_key = self._generate_cache_key(query)
        if cache_key in self.result_cache:
            return self.result_cache[cache_key]
        
        # Route query to appropriate handler
        results = []
        
        if query.query_type == KnowledgeQueryType.PATTERN_SEARCH:
            results = self._handle_pattern_search(query)
        elif query.query_type == KnowledgeQueryType.PRACTICE_SEARCH:
            results = self._handle_practice_search(query)
        elif query.query_type == KnowledgeQueryType.VIOLATION_ANALYSIS:
            results = self._handle_violation_analysis(query)
        elif query.query_type == KnowledgeQueryType.IMPROVEMENT_SUGGESTIONS:
            results = self._handle_improvement_suggestions(query)
        elif query.query_type == KnowledgeQueryType.COMMUNITY_CONTENT:
            results = self._handle_community_content(query)
        elif query.query_type == KnowledgeQueryType.ARCHITECTURAL_GUIDANCE:
            results = self._handle_architectural_guidance(query)
        
        # Cache results
        self.result_cache[cache_key] = results
        
        return results
    
    def _handle_pattern_search(self, query: KnowledgeQuery) -> List[KnowledgeResult]:
        """Handle pattern search queries"""
        
        # Extract search parameters and coerce types
        category = query.filters.get("category")
        complexity = query.filters.get("complexity")
        tags = query.filters.get("tags")
        
        if isinstance(category, str):
            try:
                category = PatternCategory(category)
            except ValueError:
                category = None
        if isinstance(complexity, str):
            try:
                complexity = PatternComplexity(complexity)
            except ValueError:
                complexity = None
        if isinstance(tags, list):
            tags = set(tags)
        
        # Search patterns
        patterns = self.pattern_library.search_patterns(
            query=query.query_text,
            category=category,
            complexity=complexity,
            tags=tags,
        )
        
        results = []
        for pattern in patterns[:query.max_results]:
            result = KnowledgeResult(
                query_id=self._generate_query_id(),
                result_type="architectural_pattern",
                title=pattern.name,
                description=pattern.description,
                content={
                    "pattern": self._pattern_to_dict(pattern),
                    "examples": [
                        {
                            "language": ex.language,
                            "code": ex.code_snippet,
                            "description": ex.description
                        }
                        for ex in pattern.examples
                    ],
                    "violations": [
                        {
                            "type": v.violation_type,
                            "description": v.description,
                            "fix": v.fix_suggestion
                        }
                        for v in pattern.common_violations
                    ]
                },
                relevance_score=self._calculate_pattern_relevance(pattern, query),
                source="library",
                metadata={
                    "category": pattern.category.value,
                    "complexity": pattern.complexity.value,
                    "tags": list(pattern.tags),
                    "usage_count": pattern.usage_count,
                    "community_rating": pattern.community_rating
                }
            )
            results.append(result)
        
        return results
    
    def _handle_practice_search(self, query: KnowledgeQuery) -> List[KnowledgeResult]:
        """Handle best practice search queries"""
        
        # Extract search parameters and coerce types
        practice_type = query.filters.get("practice_type")
        context = query.filters.get("context")
        severity = query.filters.get("severity")
        tags = query.filters.get("tags")
        
        if isinstance(practice_type, str):
            try:
                practice_type = PracticeType(practice_type)
            except ValueError:
                practice_type = None
        if isinstance(context, str):
            try:
                context = PracticeContext(context)
            except ValueError:
                context = None
        if isinstance(tags, list):
            tags = set(tags)
        
        # Search practices
        practices = self.practices_graph.search_practices(
            query=query.query_text,
            practice_type=practice_type,
            context=context,
            tags=tags,
            severity=severity
        )
        
        results = []
        for practice in practices[:query.max_results]:
            result = KnowledgeResult(
                query_id=self._generate_query_id(),
                result_type="best_practice",
                title=practice.name,
                description=practice.description,
                content={
                    "practice": self._practice_to_dict(practice),
                    "implementation_steps": practice.implementation_steps,
                    "code_examples": practice.code_examples,
                    "evidence": [
                        {
                            "source": ev.source,
                            "type": ev.evidence_type.value,
                            "description": ev.description,
                            "confidence": ev.confidence_score
                        }
                        for ev in practice.evidence
                    ]
                },
                relevance_score=self._calculate_practice_relevance(practice, query),
                source="library",
                metadata={
                    "practice_type": practice.practice_type.value,
                    "context": [ctx.value for ctx in practice.context],
                    "severity": practice.severity,
                    "effort_to_fix": practice.effort_to_fix,
                    "tags": list(practice.tags)
                }
            )
            results.append(result)
        
        return results
    
    def _handle_violation_analysis(self, query: KnowledgeQuery) -> List[KnowledgeResult]:
        """Handle violation analysis queries"""
        
        # Extract components from query context
        components = query.context.get("components", [])
        if not components:
            return []
        
        # Convert to ArchitecturalComponent objects if needed
        if isinstance(components[0], dict):
            components = [self._dict_to_component(comp) for comp in components]
        
        # Find pattern matches and violations
        project_context = set(query.context.get("project_context", []))
        pattern_matches, suggestions = self.pattern_matcher.analyze_architecture(
            components, project_context
        )
        
        results = []
        
        # Add violation results
        for match in pattern_matches:
            if match.violations:
                result = KnowledgeResult(
                    query_id=self._generate_query_id(),
                    result_type="violation_analysis",
                    title=f"{match.pattern_name} Violations",
                    description=f"Found {len(match.violations)} violations of {match.pattern_name}",
                    content={
                        "pattern_id": match.pattern_id,
                        "pattern_name": match.pattern_name,
                        "violations": match.violations,
                        "matched_components": match.matched_components,
                        "confidence": match.confidence,
                        "evidence": match.evidence
                    },
                    relevance_score=match.confidence,
                    source="generated",
                    metadata={
                        "violation_count": len(match.violations),
                        "affected_components": len(match.matched_components)
                    }
                )
                results.append(result)
        
        return results
    
    def _handle_improvement_suggestions(self, query: KnowledgeQuery) -> List[KnowledgeResult]:
        """Handle improvement suggestion queries"""
        
        # Extract components from query context
        components = query.context.get("components", [])
        if not components:
            return []
        
        # Convert to ArchitecturalComponent objects if needed
        if isinstance(components[0], dict):
            components = [self._dict_to_component(comp) for comp in components]
        
        # Generate suggestions
        project_context = set(query.context.get("project_context", []))
        _, suggestions = self.pattern_matcher.analyze_architecture(
            components, project_context
        )
        
        results = []
        for suggestion in suggestions[:query.max_results]:
            result = KnowledgeResult(
                query_id=self._generate_query_id(),
                result_type="improvement_suggestion",
                title=suggestion.title,
                description=suggestion.description,
                content={
                    "suggestion_id": suggestion.id,
                    "suggestion_type": suggestion.suggestion_type.value,
                    "priority": suggestion.priority.value,
                    "rationale": suggestion.rationale,
                    "implementation_steps": suggestion.implementation_steps,
                    "code_examples": suggestion.code_examples,
                    "benefits": suggestion.benefits,
                    "risks": suggestion.risks,
                    "estimated_effort": suggestion.estimated_effort
                },
                relevance_score=suggestion.confidence,
                source="generated",
                metadata={
                    "priority": suggestion.priority.value,
                    "effort": suggestion.estimated_effort,
                    "affected_components": len(suggestion.affected_components)
                }
            )
            results.append(result)
        
        return results
    
    def _handle_community_content(self, query: KnowledgeQuery) -> List[KnowledgeResult]:
        """Handle community content queries"""
        
        # Extract search parameters
        contribution_type = query.filters.get("contribution_type")
        status = query.filters.get("status")
        tags = query.filters.get("tags")
        category = query.filters.get("category")
        
        # Search community contributions
        contributions = self.community_service.search_contributions(
            query=query.query_text,
            contribution_type=contribution_type,
            status=status,
            tags=tags,
            category=category
        )
        
        results = []
        for contribution in contributions[:query.max_results]:
            contributor = self.community_service.users.get(contribution.contributor_id)
            
            result = KnowledgeResult(
                query_id=self._generate_query_id(),
                result_type="community_contribution",
                title=contribution.title,
                description=contribution.description,
                content={
                    "contribution_id": contribution.id,
                    "contribution_type": contribution.contribution_type.value,
                    "content": contribution.content,
                    "contributor": contributor.username if contributor else "Unknown",
                    "upvotes": contribution.upvotes,
                    "downvotes": contribution.downvotes,
                    "reviews": [
                        {
                            "reviewer": self.community_service.users.get(r.reviewer_id, {}).get("username", "Unknown"),
                            "status": r.status.value,
                            "rating": r.rating,
                            "comments": r.comments
                        }
                        for r in contribution.reviews
                    ]
                },
                relevance_score=self._calculate_contribution_relevance(contribution, query),
                source="community",
                metadata={
                    "status": contribution.status.value,
                    "category": contribution.category,
                    "tags": list(contribution.tags),
                    "created_at": contribution.created_at.isoformat(),
                    "vote_ratio": contribution.upvotes / max(1, contribution.upvotes + contribution.downvotes)
                }
            )
            results.append(result)
        
        return results
    
    def _handle_architectural_guidance(self, query: KnowledgeQuery) -> List[KnowledgeResult]:
        """Handle architectural guidance queries"""
        
        # This would provide high-level architectural guidance
        # combining patterns, practices, and community wisdom
        
        results = []
        
        # Get relevant patterns
        patterns = self.pattern_library.search_patterns(query=query.query_text)[:3]
        
        # Get relevant practices
        practices = self.practices_graph.search_practices(query=query.query_text)[:3]
        
        # Combine into guidance
        if patterns or practices:
            guidance_content = {
                "recommended_patterns": [
                    {
                        "name": p.name,
                        "description": p.description,
                        "when_to_use": p.intent
                    }
                    for p in patterns
                ],
                "recommended_practices": [
                    {
                        "name": p.name,
                        "description": p.description,
                        "when_to_apply": p.when_to_apply
                    }
                    for p in practices
                ],
                "guidance_summary": self._generate_guidance_summary(patterns, practices, query)
            }
            
            result = KnowledgeResult(
                query_id=self._generate_query_id(),
                result_type="architectural_guidance",
                title=f"Architectural Guidance for: {query.query_text}",
                description="Comprehensive guidance combining patterns and practices",
                content=guidance_content,
                relevance_score=0.8,
                source="generated",
                metadata={
                    "patterns_count": len(patterns),
                    "practices_count": len(practices)
                }
            )
            results.append(result)
        
        return results
    
    def generate_architectural_insights(
        self,
        components: List[ArchitecturalComponent],
        project_context: Set[PracticeContext]
    ) -> List[ArchitecturalInsight]:
        """Generate high-level architectural insights"""
        
        insights = []
        
        # Analyze architecture
        pattern_matches, suggestions = self.pattern_matcher.analyze_architecture(
            components, project_context
        )
        
        # Generate insights from pattern analysis
        for match in pattern_matches:
            if match.confidence > 0.7:
                # High confidence pattern match - opportunity insight
                insight = ArchitecturalInsight(
                    id=f"pattern_opportunity_{match.pattern_id}",
                    title=f"Strong {match.pattern_name} Implementation",
                    description=f"Your architecture shows strong alignment with {match.pattern_name}",
                    insight_type="pattern_opportunity",
                    confidence=match.confidence,
                    supporting_evidence=[
                        f"Matched {len(match.matched_components)} components",
                        f"Pattern confidence: {match.confidence:.2f}"
                    ],
                    recommended_actions=[
                        "Continue following this pattern",
                        "Consider documenting this pattern usage",
                        "Share as example with team"
                    ],
                    related_patterns=[match.pattern_id],
                    related_practices=[],
                    impact_assessment={
                        "maintainability": "positive",
                        "testability": "positive",
                        "complexity": "neutral"
                    }
                )
                insights.append(insight)
            
            elif match.violations:
                # Pattern violations - risk insight
                insight = ArchitecturalInsight(
                    id=f"violation_risk_{match.pattern_id}",
                    title=f"{match.pattern_name} Violations Detected",
                    description=f"Found {len(match.violations)} violations that may impact code quality",
                    insight_type="violation_risk",
                    confidence=0.8,
                    supporting_evidence=match.violations,
                    recommended_actions=[
                        "Review and fix pattern violations",
                        "Consider refactoring affected components",
                        "Add validation rules to prevent future violations"
                    ],
                    related_patterns=[match.pattern_id],
                    related_practices=[],
                    impact_assessment={
                        "maintainability": "negative",
                        "testability": "negative",
                        "complexity": "negative"
                    }
                )
                insights.append(insight)
        
        # Generate insights from suggestions
        high_priority_suggestions = [s for s in suggestions if s.priority.value in ["critical", "high"]]
        if high_priority_suggestions:
            insight = ArchitecturalInsight(
                id="improvement_potential",
                title="High-Impact Improvement Opportunities",
                description=f"Found {len(high_priority_suggestions)} high-priority improvements",
                insight_type="improvement_potential",
                confidence=0.9,
                supporting_evidence=[s.title for s in high_priority_suggestions[:3]],
                recommended_actions=[
                    "Prioritize high-impact improvements",
                    "Create improvement backlog",
                    "Estimate effort for implementation"
                ],
                related_patterns=[],
                related_practices=[],
                impact_assessment={
                    "maintainability": "positive",
                    "code_quality": "positive",
                    "development_velocity": "positive"
                }
            )
            insights.append(insight)
        
        return insights
    
    def get_knowledge_base_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the knowledge base"""
        
        pattern_stats = self.pattern_library.get_pattern_statistics()
        practice_stats = self.practices_graph.get_knowledge_graph_stats()
        community_stats = self.community_service.get_community_statistics()
        
        return {
            "patterns": pattern_stats,
            "practices": practice_stats,
            "community": community_stats,
            "queries": {
                "total_queries": len(self.query_history),
                "cached_results": len(self.result_cache),
                "query_types": self._get_query_type_distribution()
            },
            "integration": {
                "community_patterns_integrated": len(self.community_service.export_approved_patterns()),
                "community_practices_integrated": len(self.community_service.export_approved_practices())
            }
        }
    
    # Helper methods
    def _generate_cache_key(self, query: KnowledgeQuery) -> str:
        """Generate cache key for query"""
        import hashlib
        query_str = f"{query.query_type.value}_{query.query_text}_{json.dumps(query.filters, sort_keys=True)}"
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def _generate_query_id(self) -> str:
        """Generate unique query ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _pattern_to_dict(self, pattern: ArchitecturalPattern) -> Dict[str, Any]:
        """Convert pattern to dictionary"""
        return {
            "id": pattern.id,
            "name": pattern.name,
            "category": pattern.category.value,
            "complexity": pattern.complexity.value,
            "description": pattern.description,
            "intent": pattern.intent,
            "structure": pattern.structure,
            "participants": pattern.participants,
            "collaborations": pattern.collaborations,
            "consequences": pattern.consequences,
            "implementation_notes": pattern.implementation_notes
        }
    
    def _practice_to_dict(self, practice: BestPractice) -> Dict[str, Any]:
        """Convert practice to dictionary"""
        return {
            "id": practice.id,
            "name": practice.name,
            "practice_type": practice.practice_type.value,
            "context": [ctx.value for ctx in practice.context],
            "description": practice.description,
            "rationale": practice.rationale,
            "when_to_apply": practice.when_to_apply,
            "when_not_to_apply": practice.when_not_to_apply
        }
    
    def _dict_to_component(self, comp_dict: Dict[str, Any]) -> ArchitecturalComponent:
        """Convert dictionary to ArchitecturalComponent"""
        # This would need proper implementation based on ArchitecturalComponent structure
        # For now, return a mock component
        from ..entities.architectural_component import ComponentType, Relationship
        
        return ArchitecturalComponent(
            iri=comp_dict.get("iri", ""),
            component_type=ComponentType(comp_dict.get("component_type", "MODULE")),
            name=comp_dict.get("name", ""),
            module_namespace=comp_dict.get("module_namespace", ""),
            properties=comp_dict.get("properties", {}),
            relationships=[]
        )
    
    def _calculate_pattern_relevance(self, pattern: ArchitecturalPattern, query: KnowledgeQuery) -> float:
        """Calculate relevance score for pattern"""
        score = 0.0
        
        # Text match
        query_lower = query.query_text.lower()
        if query_lower in pattern.name.lower():
            score += 0.5
        if query_lower in pattern.description.lower():
            score += 0.3
        
        # Tag match
        query_tags = set(query.filters.get("tags", []))
        if query_tags & pattern.tags:
            score += 0.2
        
        # Community rating
        score += pattern.community_rating * 0.1
        
        return min(1.0, score)
    
    def _calculate_practice_relevance(self, practice: BestPractice, query: KnowledgeQuery) -> float:
        """Calculate relevance score for practice"""
        score = 0.0
        
        # Text match
        query_lower = query.query_text.lower()
        if query_lower in practice.name.lower():
            score += 0.5
        if query_lower in practice.description.lower():
            score += 0.3
        
        # Context match
        query_context = query.filters.get("context")
        if query_context and query_context in [ctx.value for ctx in practice.context]:
            score += 0.3
        
        # Community rating
        score += practice.community_rating * 0.1
        
        return min(1.0, score)
    
    def _calculate_contribution_relevance(self, contribution: CommunityContribution, query: KnowledgeQuery) -> float:
        """Calculate relevance score for community contribution"""
        score = 0.0
        
        # Text match
        query_lower = query.query_text.lower()
        if query_lower in contribution.title.lower():
            score += 0.5
        if query_lower in contribution.description.lower():
            score += 0.3
        
        # Vote ratio
        total_votes = contribution.upvotes + contribution.downvotes
        if total_votes > 0:
            vote_ratio = contribution.upvotes / total_votes
            score += vote_ratio * 0.2
        
        return min(1.0, score)
    
    def _generate_guidance_summary(
        self,
        patterns: List[ArchitecturalPattern],
        practices: List[BestPractice],
        query: KnowledgeQuery
    ) -> str:
        """Generate a summary of architectural guidance"""
        
        summary_parts = []
        
        if patterns:
            pattern_names = [p.name for p in patterns]
            summary_parts.append(f"Consider applying these patterns: {', '.join(pattern_names)}")
        
        if practices:
            practice_names = [p.name for p in practices]
            summary_parts.append(f"Follow these practices: {', '.join(practice_names)}")
        
        summary_parts.append(f"This guidance is based on your query: '{query.query_text}'")
        
        return ". ".join(summary_parts)
    
    def _get_query_type_distribution(self) -> Dict[str, int]:
        """Get distribution of query types"""
        distribution = {}
        for query in self.query_history:
            query_type = query.query_type.value
            distribution[query_type] = distribution.get(query_type, 0) + 1
        return distribution