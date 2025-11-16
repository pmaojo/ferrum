import pytest

from domain.ambiguity_detector import AmbiguityDetector
from domain.entities import Triple


@pytest.fixture()
def detector() -> AmbiguityDetector:
    return AmbiguityDetector()


def test_detect_ambiguous_terms_returns_questions(detector: AmbiguityDetector):
    needed, questions = detector.detect(
        question="Tell me about it",
        results="Some information about a topic.",
        translated_query="query",
    )
    assert needed is True
    assert questions and questions[0].startswith("Your query contains ambiguous terms")


def test_detect_long_text_results_triggers_clarification(detector: AmbiguityDetector):
    long_text = (
        "Apple was founded in 1976. Banana is yellow. Carrot is orange. "
        "Dog is faithful. Elephant is huge. Fox is cunning. Giraffe is tall."
    )
    needed, questions = detector.detect(
        question="Explain computing history",
        results=long_text,
        translated_query="query",
    )
    assert needed is True
    assert any(q.startswith("I found information about multiple topics") for q in questions)


def test_detect_short_question_triggers_clarification(detector: AmbiguityDetector):
    needed, questions = detector.detect(
        question="Hi",
        results="Hello world.",
        translated_query="query",
    )
    assert needed is True
    assert any(q.startswith("Your query is quite brief") for q in questions)


def test_detect_triple_results_many_entities_triggers_clarification(detector: AmbiguityDetector):
    triples = [
        Triple("A1", "p1", "B1", "t"),
        Triple("A2", "p1", "B2", "t"),
        Triple("A3", "p2", "B3", "t"),
        Triple("A4", "p3", "B4", "t"),
        Triple("A5", "p4", "B5", "t"),
        Triple("A6", "p1", "B6", "t"),
        Triple("A1", "p2", "B7", "t"),
        Triple("A2", "p3", "B8", "t"),
        Triple("A3", "p4", "B9", "t"),
        Triple("A4", "p1", "B10", "t"),
        Triple("A5", "p2", "B11", "t"),
    ]
    needed, questions = detector.detect(
        question="Show relationships",
        results=triples,
        translated_query="query",
    )
    assert needed is True
    assert any(q.startswith("Your query returned many relationships") for q in questions)


@pytest.mark.parametrize(
    "question,results",
    [
        ("Who discovered penicillin?", "Alexander Fleming discovered penicillin in 1928."),
        (
            "List friends of Alice",
            [Triple("Alice", "knows", "Bob", "t")],
        ),
    ],
)
def test_detect_returns_false_for_clear_inputs(detector: AmbiguityDetector, question, results):
    needed, questions = detector.detect(
        question=question,
        results=results,
        translated_query="query",
    )
    assert needed is False
    assert questions is None

