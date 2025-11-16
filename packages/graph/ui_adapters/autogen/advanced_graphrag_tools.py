"""Advanced GraphRAG tools for specialized agent workflows."""

from typing import Dict, Any, List, Optional, Union
from functools import wraps
import logging

from .graphrag_tool import GraphRAGToolRegistry

logger = logging.getLogger(__name__)


def tool(func):
    """Enhanced tool decorator with GraphRAG-specific metadata."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper._tool = True
    wrapper._tool_name = getattr(func, "__name__", "graphrag_tool")
    wrapper._tool_description = getattr(func, "__doc__", "GraphRAG tool")
    wrapper._tool_category = "graphrag"
    wrapper._tool_capabilities = getattr(func, "_capabilities", [])

    return wrapper


@tool
def research_entity_deeply(
    entity_name: str,
    kg_id: str = "default",
    tenant_id: str = "default",
    depth: int = 3,
    include_related: bool = True,
    _registry: Optional[GraphRAGToolRegistry] = None,
) -> Union[str, Dict[str, Any]]:
    """Deep research on a specific entity across multiple relationship hops.

    This tool performs comprehensive entity research by traversing the knowledge
    graph to specified depth, gathering all relevant information and relationships.

    Args:
        entity_name: Name of entity to research
        kg_id: Knowledge graph identifier
        tenant_id: Tenant identifier
        depth: Maximum traversal depth (1-5)
        include_related: Include related entities in results

    Returns:
        Comprehensive entity profile with relationships and context
    """
    if _registry is None:
        raise ValueError("GraphRAGToolRegistry is required")

    opts = {"depth": depth, "include_related": include_related}
    question = f"Research entity {entity_name}"
    return _registry.retriever.run(
        question=question,
        kg_id=kg_id,
        tenant_id=tenant_id,
        opts=opts,
    )


research_entity_deeply._capabilities = [
    "multi_hop_traversal",
    "relationship_analysis",
    "context_aggregation"
]


@tool
def find_knowledge_gaps(
    research_domain: str,
    kg_id: str = "default",
    tenant_id: str = "default",
    gap_types: List[str] = None,
    _registry: Optional[GraphRAGToolRegistry] = None,
) -> Union[str, Dict[str, Any]]:
    """Identify knowledge gaps and missing information in specified domain.

    Analyzes the knowledge graph to find:
    - Missing entity relationships
    - Incomplete entity profiles
    - Inconsistent information
    - Potential research opportunities

    Args:
        research_domain: Domain to analyze for gaps
        kg_id: Knowledge graph identifier
        tenant_id: Tenant identifier
        gap_types: Types of gaps to search for

    Returns:
        Analysis of knowledge gaps with suggestions for improvement
    """
    if _registry is None:
        raise ValueError("GraphRAGToolRegistry is required")

    opts = {"gap_types": gap_types or []}
    question = f"Find knowledge gaps in {research_domain}"
    return _registry.retriever.run(
        question=question,
        kg_id=kg_id,
        tenant_id=tenant_id,
        opts=opts,
    )


find_knowledge_gaps._capabilities = [
    "gap_analysis",
    "consistency_checking",
    "research_planning"
]


@tool
def synthesize_multi_source_evidence(
    research_question: str,
    knowledge_graphs: List[str],
    tenant_id: str = "default",
    synthesis_strategy: str = "weighted_consensus",
    _registry: Optional[GraphRAGToolRegistry] = None,
) -> Union[str, Dict[str, Any]]:
    """Synthesize evidence from multiple knowledge sources.

    Performs federated search across multiple knowledge graphs and
    synthesizes findings using advanced reasoning strategies.

    Args:
        research_question: Question to research across sources
        knowledge_graphs: List of KG IDs to search
        tenant_id: Tenant identifier
        synthesis_strategy: How to combine evidence

    Returns:
        Synthesized answer with confidence scores and source attribution
    """
    if _registry is None:
        raise ValueError("GraphRAGToolRegistry is required")

    opts = {
        "knowledge_graphs": knowledge_graphs,
        "synthesis_strategy": synthesis_strategy,
    }
    kg = knowledge_graphs[0] if knowledge_graphs else "default"
    return _registry.retriever.run(
        question=research_question,
        kg_id=kg,
        tenant_id=tenant_id,
        opts=opts,
    )


synthesize_multi_source_evidence._capabilities = [
    "federated_search",
    "evidence_synthesis",
    "source_attribution",
    "confidence_scoring"
]


@tool
def detect_emerging_patterns(
    domain: str,
    kg_id: str = "default",
    tenant_id: str = "default",
    time_window: str = "30d",
    pattern_types: List[str] = None,
    _registry: Optional[GraphRAGToolRegistry] = None,
) -> Union[str, Dict[str, Any]]:
    """Detect emerging patterns and trends in knowledge graph data.

    Uses temporal analysis to identify:
    - New entity relationships
    - Changing entity properties
    - Trending topics
    - Anomalous patterns

    Args:
        domain: Domain to analyze for patterns
        kg_id: Knowledge graph identifier
        tenant_id: Tenant identifier
        time_window: Time period for analysis
        pattern_types: Specific pattern types to detect

    Returns:
        Analysis of emerging patterns with trend information
    """
    if _registry is None:
        raise ValueError("GraphRAGToolRegistry is required")

    opts = {"time_window": time_window, "pattern_types": pattern_types or []}
    question = f"Detect emerging patterns in {domain}"
    return _registry.retriever.run(
        question=question,
        kg_id=kg_id,
        tenant_id=tenant_id,
        opts=opts,
    )


detect_emerging_patterns._capabilities = [
    "temporal_analysis",
    "pattern_detection",
    "trend_analysis",
    "anomaly_detection"
]


@tool
def validate_knowledge_consistency(
    kg_id: str = "default",
    tenant_id: str = "default",
    validation_rules: List[str] = None,
    fix_inconsistencies: bool = False,
    _registry: Optional[GraphRAGToolRegistry] = None,
) -> Union[str, Dict[str, Any]]:
    """Validate knowledge graph consistency and logical coherence.

    Performs comprehensive validation including:
    - Ontological consistency
    - Logical contradiction detection
    - Reference integrity
    - Schema compliance

    Args:
        kg_id: Knowledge graph identifier
        tenant_id: Tenant identifier
        validation_rules: Specific rules to apply
        fix_inconsistencies: Attempt automatic fixes

    Returns:
        Validation report with identified issues and fixes
    """
    if _registry is None:
        raise ValueError("GraphRAGToolRegistry is required")

    opts = {
        "validation_rules": validation_rules or [],
        "fix_inconsistencies": fix_inconsistencies,
    }
    question = "Validate knowledge graph consistency"
    return _registry.retriever.run(
        question=question,
        kg_id=kg_id,
        tenant_id=tenant_id,
        opts=opts,
    )


validate_knowledge_consistency._capabilities = [
    "consistency_validation",
    "contradiction_detection",
    "schema_compliance",
    "automatic_repair"
]


@tool
def explain_reasoning_path(
    question: str,
    answer: str,
    kg_id: str = "default",
    tenant_id: str = "default",
    explanation_depth: str = "detailed",
    _registry: Optional[GraphRAGToolRegistry] = None,
) -> Union[str, Dict[str, Any]]:
    """Explain the reasoning path for a GraphRAG answer.

    Provides detailed explanation of how an answer was derived,
    including entity traversal paths, inference steps, and confidence calculations.

    Args:
        question: Original question
        answer: Answer to explain
        kg_id: Knowledge graph identifier
        tenant_id: Tenant identifier
        explanation_depth: Level of detail in explanation

    Returns:
        Detailed reasoning explanation with step-by-step breakdown
    """
    if _registry is None:
        raise ValueError("GraphRAGToolRegistry is required")

    opts = {"answer": answer, "explanation_depth": explanation_depth}
    return _registry.retriever.run(
        question=question,
        kg_id=kg_id,
        tenant_id=tenant_id,
        opts=opts,
    )


explain_reasoning_path._capabilities = [
    "explainable_ai",
    "reasoning_trace",
    "confidence_explanation",
    "path_visualization"
]


# Tool registry for advanced GraphRAG capabilities
ADVANCED_GRAPHRAG_TOOLS = {
    "research_entity_deeply": research_entity_deeply,
    "find_knowledge_gaps": find_knowledge_gaps,
    "synthesize_multi_source_evidence": synthesize_multi_source_evidence,
    "detect_emerging_patterns": detect_emerging_patterns,
    "validate_knowledge_consistency": validate_knowledge_consistency,
    "explain_reasoning_path": explain_reasoning_path
}


def create_bound_advanced_tools(registry) -> Dict[str, Any]:
    """Create bound versions of advanced GraphRAG tools.

    Args:
        registry: GraphRAGToolRegistry instance

    Returns:
        Dictionary of bound tool functions
    """
    bound_tools = {}

    for tool_name, tool_func in ADVANCED_GRAPHRAG_TOOLS.items():
        def create_bound_tool(original_func, name):
            @wraps(original_func)
            def bound_tool(*args, **kwargs):
                # Add registry context
                kwargs["_registry"] = registry
                return original_func(*args, **kwargs)

            bound_tool._tool_name = name
            bound_tool._tool_description = original_func.__doc__
            bound_tool._tool_capabilities = getattr(original_func, "_capabilities", [])
            return bound_tool

        bound_tools[tool_name] = create_bound_tool(tool_func, tool_name)

    return bound_tools
