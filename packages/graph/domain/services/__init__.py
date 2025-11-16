"""Service exports for domain layer.

This package exposes commonly used services and utilities from the domain
layer.  It aggregates implementations from across the domain package so that
consumers can simply import from ``domain.services``.
"""

from __future__ import annotations

from ..agent_coordinator import AgentCoordinator, CoordinationException
from ..exceptions import GraphRAGException
from ..ingestion_service import IngestionService
from ..code_ingestion_service import CodeIngestionService
try:  # Optional dependency used by some services
    from application.services import ConfigTemplateService
except Exception:  # pragma: no cover - fallback when optional deps missing
    ConfigTemplateService = None  # type: ignore

from ..observability_service import ObservabilityService
from ..query_service import QueryService
from ..query_execution import QueryExecutionService
from ..multimodal_response_generator import MultimodalResponseGenerator
from ..workflow_orchestrator import WorkflowOrchestrator
from ..hybrid_reasoning import (
    OntologyLoaderService,
    ConsistencyCheckerService,
    ReasoningExplanationService,
    EntityLinkingService,
    HybridReasoningService,
)

__all__ = [
    "GraphRAGException",
    "IngestionService",
    "CodeIngestionService",
    "WorkflowOrchestrator",
    "QueryService",
    "QueryExecutionService",
    "AgentCoordinator",
    "CoordinationException",
    "ObservabilityService",
    "MultimodalResponseGenerator",
    "OntologyLoaderService",
    "ConsistencyCheckerService",
    "ReasoningExplanationService",
    "EntityLinkingService",
    "HybridReasoningService",
    "ConfigTemplateService",
]
