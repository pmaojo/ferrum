import logging
import json
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from application.ports.base import MessageBusPort, LLMPort
from domain.entities.architectural_component import ArchitecturalComponent
from domain.services.semantic_search_service import (
    SemanticSearchService,
    SemanticSearchQuery,
    SearchScope,
)
from domain.services.architectural_pattern_service import ArchitecturalPatternService

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of natural language queries supported"""

    COMPONENT_SEARCH = "component_search"
    RELATIONSHIP_ANALYSIS = "relationship_analysis"
    PATTERN_DETECTION = "pattern_detection"
    ARCHITECTURE_REVIEW = "architecture_review"
    CODE_SUGGESTION = "code_suggestion"
    ANTI_PATTERN_CHECK = "anti_pattern_check"


@dataclass
class NaturalLanguageQuery:
    """Natural language query with context"""

    query_text: str
    query_type: Optional[QueryType] = None
    context: Dict[str, Any] | None = None
    tenant_id: str = "default"


@dataclass
class QueryResponse:
    """Response to natural language query"""

    query: NaturalLanguageQuery
    response_text: str
    structured_data: Dict[str, Any]
    confidence: float
    suggestions: List[str]
    related_components: List[ArchitecturalComponent]


class QueryProcessor:
    """Process natural language queries."""

    def __init__(
        self,
        message_bus: MessageBusPort,
        llm: LLMPort,
        semantic_search: SemanticSearchService,
        pattern_service: ArchitecturalPatternService,
        tenant_id: str,
        error_handler,
    ) -> None:
        self.message_bus = message_bus
        self.llm = llm
        self.semantic_search = semantic_search
        self.pattern_service = pattern_service
        self.tenant_id = tenant_id
        self.error_handler = error_handler
        self.query_count = 0

    # Public API -----------------------------------------------------
    def handle_natural_language_query(self, message: Dict[str, Any]) -> None:
        """Handle natural language architecture queries"""
        query_text = message.get("query", "")
        context = message.get("context", {})

        try:
            query = NaturalLanguageQuery(
                query_text=query_text,
                context=context,
                tenant_id=self.tenant_id,
            )
            query.query_type = self.classify_query(query_text)
            response = self.process_query(query)

            self.message_bus.publish(
                topic="ai.natural_language_response",
                message={
                    "query": query_text,
                    "response": response.response_text,
                    "structured_data": response.structured_data,
                    "confidence": response.confidence,
                    "suggestions": response.suggestions,
                    "related_components": [
                        {
                            "iri": comp.iri,
                            "name": comp.name,
                            "type": comp.component_type.value,
                        }
                        for comp in response.related_components
                    ],
                    "tenant_id": self.tenant_id,
                    "timestamp": datetime.now().isoformat(),
                },
                tenant_id=self.tenant_id,
            )
            self.query_count += 1
            logger.info("Processed natural language query")
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Error handling natural language query: %s", exc)
            self.error_handler("natural_language_query", str(exc))

    def classify_query(self, query_text: str) -> QueryType:
        """Classify the type of natural language query"""
        query_lower = query_text.lower()

        if any(w in query_lower for w in ["find", "search", "show", "list", "get"]):
            if any(w in query_lower for w in ["component", "module", "usecase", "adapter", "port"]):
                return QueryType.COMPONENT_SEARCH

        if any(w in query_lower for w in ["depends", "uses", "calls", "relationship", "connected"]):
            return QueryType.RELATIONSHIP_ANALYSIS

        if any(w in query_lower for w in ["pattern", "architecture", "design", "structure"]):
            return QueryType.PATTERN_DETECTION

        if any(w in query_lower for w in ["review", "improve", "suggest", "fix", "optimize"]):
            return QueryType.CODE_SUGGESTION

        if any(w in query_lower for w in ["problem", "issue", "violation", "anti-pattern", "smell"]):
            return QueryType.ANTI_PATTERN_CHECK

        return QueryType.ARCHITECTURE_REVIEW

    def process_query(self, query: NaturalLanguageQuery) -> QueryResponse:
        if query.query_type == QueryType.COMPONENT_SEARCH:
            return self.handle_component_search_query(query)
        if query.query_type == QueryType.RELATIONSHIP_ANALYSIS:
            return self.handle_relationship_analysis_query(query)
        if query.query_type == QueryType.PATTERN_DETECTION:
            return self.handle_pattern_detection_query(query)
        if query.query_type == QueryType.ANTI_PATTERN_CHECK:
            return self.handle_anti_pattern_query(query)
        return self.handle_general_architecture_query(query)

    # Internal helpers ----------------------------------------------
    def handle_component_search_query(self, query: NaturalLanguageQuery) -> QueryResponse:
        search_query = SemanticSearchQuery(
            query_text=query.query_text,
            scope=SearchScope.ALL,
            tenant_id=query.tenant_id,
        )
        search_results = self.semantic_search.search(search_query)

        if search_results:
            components = [result.component for result in search_results[:5]]
            component_names = [comp.name for comp in components]
            response_text = (
                f"Found {len(search_results)} components matching your query. "
                f"Top matches: {', '.join(component_names[:3])}"
            )
            if len(search_results) > 3:
                response_text += f" and {len(search_results) - 3} more."
            structured_data = {
                "search_results": [
                    {
                        "component": {
                            "iri": result.component.iri,
                            "name": result.component.name,
                            "type": result.component.component_type.value,
                            "module": result.component.module_namespace,
                        },
                        "relevance_score": result.relevance_score,
                        "match_type": result.match_type,
                    }
                    for result in search_results
                ]
            }
            suggestions = [
                "Use more specific terms to narrow results",
                "Try searching within a specific module",
                "Look for related components using relationships",
            ]
            return QueryResponse(
                query=query,
                response_text=response_text,
                structured_data=structured_data,
                confidence=0.9,
                suggestions=suggestions,
                related_components=components,
            )
        return QueryResponse(
            query=query,
            response_text="No components found matching your query. Try using different search terms.",
            structured_data={"search_results": []},
            confidence=0.8,
            suggestions=[
                "Try broader search terms",
                "Check spelling",
                "Search in specific component types",
            ],
            related_components=[],
        )

    def handle_relationship_analysis_query(self, query: NaturalLanguageQuery) -> QueryResponse:
        extraction_prompt = f"""
        Extract component names and relationship types from this query: "{query.query_text}"

        Return JSON with:
        - "components": list of component names mentioned
        - "relationship_types": list of relationship types (depends, uses, calls, implements, etc.)
        - "direction": "incoming", "outgoing", or "both"

        Example: {{"components": ["UserService"], "relationship_types": ["depends"], "direction": "outgoing"}}
        """
        try:
            extraction_result = self.llm.generate(extraction_prompt, query.tenant_id)
            extracted_data = json.loads(extraction_result)
            components = extracted_data.get("components", [])
            relationship_types = extracted_data.get("relationship_types", [])
            if components:
                relationships_data = self._analyze_component_relationships(
                    components[0], relationship_types, query.tenant_id
                )
                response_text = (
                    f"Analysis of relationships for {components[0]}:\n"
                    f"Found {len(relationships_data['relationships'])} relationships."
                )
                return QueryResponse(
                    query=query,
                    response_text=response_text,
                    structured_data=relationships_data,
                    confidence=0.8,
                    suggestions=[
                        "Explore specific relationship types",
                        "Analyze dependency paths",
                    ],
                    related_components=[],
                )
            return QueryResponse(
                query=query,
                response_text="Could not identify specific components in your query. Please mention component names.",
                structured_data={},
                confidence=0.5,
                suggestions=[
                    "Mention specific component names",
                    "Use exact component names from your architecture",
                ],
                related_components=[],
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error in relationship analysis: %s", exc)
            return QueryResponse(
                query=query,
                response_text="Error analyzing relationships. Please try rephrasing your query.",
                structured_data={},
                confidence=0.3,
                suggestions=["Try simpler query", "Mention specific component names"],
                related_components=[],
            )

    def handle_pattern_detection_query(self, query: NaturalLanguageQuery) -> QueryResponse:
        pattern_analysis = self.pattern_service.analyze_patterns(query.tenant_id)
        detected_patterns = pattern_analysis.detected_patterns
        quality_score = pattern_analysis.architecture_quality_score
        response_text = (
            f"Architecture Analysis Results:\nQuality Score: {quality_score:.1f}/100\n"
            f"Detected {len(detected_patterns)} architectural patterns:\n"
        )
        for pattern in detected_patterns[:3]:
            response_text += f"- {pattern.pattern_type.value}: {pattern.description}\n"
        structured_data = {
            "quality_score": quality_score,
            "detected_patterns": [
                {
                    "type": pattern.pattern_type.value,
                    "confidence": pattern.confidence.value,
                    "description": pattern.description,
                    "components": [comp.name for comp in pattern.components],
                    "recommendations": pattern.recommendations,
                }
                for pattern in detected_patterns
            ],
            "anti_patterns": [
                {
                    "type": anti_pattern.pattern_type.value,
                    "confidence": anti_pattern.confidence.value,
                    "description": anti_pattern.description,
                    "components": [comp.name for comp in anti_pattern.components],
                }
                for anti_pattern in pattern_analysis.anti_patterns
            ],
        }
        return QueryResponse(
            query=query,
            response_text=response_text,
            structured_data=structured_data,
            confidence=0.9,
            suggestions=pattern_analysis.recommendations,
            related_components=[],
        )

    def handle_anti_pattern_query(self, query: NaturalLanguageQuery) -> QueryResponse:
        pattern_analysis = self.pattern_service.analyze_patterns(query.tenant_id)
        anti_patterns = pattern_analysis.anti_patterns
        if anti_patterns:
            response_text = f"Found {len(anti_patterns)} potential issues:\n"
            for anti_pattern in anti_patterns[:3]:
                response_text += f"- {anti_pattern.pattern_type.value}: {anti_pattern.description}\n"
        else:
            response_text = "No significant anti-patterns detected in your architecture. Good job!"
        structured_data = {
            "anti_patterns": [
                {
                    "type": anti_pattern.pattern_type.value,
                    "confidence": anti_pattern.confidence.value,
                    "description": anti_pattern.description,
                    "components": [comp.name for comp in anti_pattern.components],
                    "recommendations": anti_pattern.recommendations,
                    "evidence": anti_pattern.evidence,
                }
                for anti_pattern in anti_patterns
            ]
        }
        return QueryResponse(
            query=query,
            response_text=response_text,
            structured_data=structured_data,
            confidence=0.9,
            suggestions=[
                rec
                for anti_pattern in anti_patterns
                for rec in anti_pattern.recommendations
            ],
            related_components=[],
        )

    def handle_general_architecture_query(self, query: NaturalLanguageQuery) -> QueryResponse:
        guidance_prompt = f"""
        As an expert software architect, answer this question about software architecture: "{query.query_text}"

        Consider:
        - Hexagonal architecture principles
        - Domain-driven design
        - SOLID principles
        - Best practices

        Provide practical, actionable advice.
        """
        try:
            response_text = self.llm.generate(guidance_prompt, query.tenant_id)
            return QueryResponse(
                query=query,
                response_text=response_text,
                structured_data={"type": "general_guidance"},
                confidence=0.7,
                suggestions=[
                    "Consider specific architectural patterns",
                    "Review your current implementation",
                ],
                related_components=[],
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error generating architectural guidance: %s", exc)
            return QueryResponse(
                query=query,
                response_text="I'm having trouble generating a response. Please try rephrasing your question.",
                structured_data={},
                confidence=0.3,
                suggestions=[
                    "Try a more specific question",
                    "Ask about particular architectural concepts",
                ],
                related_components=[],
            )

    # Private utilities ---------------------------------------------
    def _analyze_component_relationships(
        self, component_name: str, relationship_types: List[str], tenant_id: str
    ) -> Dict[str, Any]:
        return {
            "component": component_name,
            "relationships": [],
            "relationship_count": 0,
            "dependency_depth": 0,
        }
