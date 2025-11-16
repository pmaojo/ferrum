import asyncio
import pytest
from unittest.mock import Mock

from domain.entities import Triple, ValidationReport
from domain.knowledge_discovery import (
    PatternMiningService,
    OntologyEnrichmentService,
    AnomalyDetectionService,
    HypothesisGenerationService,
    DiscoveryValidationService,
    DiscoveryVisualizationService,
    Pattern,
    Hypothesis,
)
from adapters.knowledge_discovery import (
    InMemoryTripleProvider,
    SimplePatternMiningAdapter,
    SimpleOntologyEnrichmentAdapter,
    SimpleAnomalyDetectionAdapter,
    SimpleHypothesisGenerationAdapter,
    SimpleDiscoveryValidationAdapter,
    SimpleDiscoveryVisualizationAdapter,
)
from application.use_cases.knowledge_discovery import (
    PatternDiscoveryUseCase,
    OntologyEnrichmentUseCase,
    AnomalyDetectionUseCase,
    HypothesisGenerationUseCase,
    DiscoveryValidationUseCase,
    DiscoveryVisualizationUseCase,
    PatternDiscoveryRequest,
    OntologyEnrichmentRequest,
    AnomalyDetectionRequest,
    HypothesisGenerationRequest,
    DiscoveryValidationRequest,
    DiscoveryVisualizationRequest,
)


@pytest.fixture
def sample_triples() -> list[Triple]:
    return [
        Triple("a", "likes", "b", "t1"),
        Triple("b", "likes", "c", "t1"),
        Triple("a", "likes", "c", "t1"),
        Triple("a", "worksWith", "b", "t1"),
    ]


class DummyOntologyRepo:
    def get_version(self, oid: str, tenant_id: str):
        class O:
            predicates = ["worksWith"]
        return O()


class DummyValidator:
    def validate(self, *, triples, ontology_version_id):
        inconsistent = any(t.predicate == "worksWith" for t in triples)
        return ValidationReport(
            is_consistent=not inconsistent,
            unsat_classes=["Error"] if inconsistent else [],
            repair_suggestions=[],
            tenant_id="t1",
            ontology_version_id=ontology_version_id,
        )


def make_services(triples):
    provider = InMemoryTripleProvider(triples)
    mining = SimplePatternMiningAdapter(PatternMiningService())
    enrichment = SimpleOntologyEnrichmentAdapter(
        OntologyEnrichmentService(DummyOntologyRepo())
    )
    detector = SimpleAnomalyDetectionAdapter(AnomalyDetectionService(DummyValidator()))
    generator = SimpleHypothesisGenerationAdapter(HypothesisGenerationService())
    validator = SimpleDiscoveryValidationAdapter(
        DiscoveryValidationService(DummyValidator())
    )
    visualizer = SimpleDiscoveryVisualizationAdapter(
        DiscoveryVisualizationService(Mock())
    )
    return {
        "provider": provider,
        "mining": mining,
        "enrichment": enrichment,
        "detector": detector,
        "generator": generator,
        "validator": validator,
        "visualizer": visualizer,
    }


def test_full_workflow(sample_triples):
    services = make_services(sample_triples)

    pattern_uc = PatternDiscoveryUseCase(services["provider"], services["mining"])
    patterns_resp = asyncio.run(
        pattern_uc.execute(PatternDiscoveryRequest(kg_id="kg", tenant_id="t1", min_support=2))
    )
    assert any(p.predicate == "likes" for p in patterns_resp.patterns)

    enrichment_uc = OntologyEnrichmentUseCase(
        services["provider"], services["enrichment"]
    )
    enrich_resp = asyncio.run(
        enrichment_uc.execute(
            OntologyEnrichmentRequest(
                kg_id="kg", tenant_id="t1", ontology_version_id="v1"
            )
        )
    )
    assert all(isinstance(h, Hypothesis) for h in enrich_resp.suggestions)

    anomaly_uc = AnomalyDetectionUseCase(
        services["provider"], services["detector"]
    )
    anomaly_resp = asyncio.run(
        anomaly_uc.execute(
            AnomalyDetectionRequest(
                kg_id="kg", tenant_id="t1", ontology_version_id="v1"
            )
        )
    )
    assert len(anomaly_resp.anomalies) == 1

    hypo_uc = HypothesisGenerationUseCase(
        services["provider"], services["mining"], services["generator"]
    )
    hypo_resp = asyncio.run(
        hypo_uc.execute(
            HypothesisGenerationRequest(kg_id="kg", tenant_id="t1")
        )
    )
    assert hypo_resp.hypotheses

    validation_uc = DiscoveryValidationUseCase(services["validator"])
    val_resp = asyncio.run(
        validation_uc.execute(
            DiscoveryValidationRequest(
                hypotheses=hypo_resp.hypotheses,
                ontology_version_id="v1",
                tenant_id="t1",
            )
        )
    )
    assert all(isinstance(r.confidence, float) for r in val_resp.results)

    viz_uc = DiscoveryVisualizationUseCase(services["visualizer"])
    viz_resp = asyncio.run(
        viz_uc.execute(
            DiscoveryVisualizationRequest(
                kg_id="kg",
                tenant_id="t1",
                patterns=patterns_resp.patterns,
                hypotheses=[],
            )
        )
    )
    assert isinstance(viz_resp.layout, Mock)

