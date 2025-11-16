import pytest

from services.graph.domain.services.best_practices_knowledge_graph import (
    BestPracticesKnowledgeGraph,
    PracticeContext,
)


def test_recommendation_requires_rule_match(monkeypatch):
    graph = BestPracticesKnowledgeGraph()
    practice = graph.get_practice("hexagonal_dependency_inversion")

    # No detection rules fire
    monkeypatch.setattr(graph, "_execute_detection_rule", lambda rule: False)
    recs = graph.recommend_practices([], {PracticeContext.HEXAGONAL_ARCHITECTURE})
    assert practice not in [p for p, _ in recs]
    assert recs == []

    # Only the target rule fires
    target_rule = practice.detection_rules[0]
    monkeypatch.setattr(graph, "_execute_detection_rule", lambda rule: rule == target_rule)
    recs = graph.recommend_practices([], {PracticeContext.HEXAGONAL_ARCHITECTURE})
    assert practice in [p for p, _ in recs]
