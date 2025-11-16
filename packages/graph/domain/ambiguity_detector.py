from __future__ import annotations

import logging
import re
from typing import Any, List, Optional, Tuple, Union

from domain.entities import Triple

logger = logging.getLogger(__name__)


class AmbiguityDetector:
    """Analyze queries and results for potential ambiguity."""

    def detect(
        self,
        *,
        question: str,
        results: Union[str, List[Triple]],
        translated_query: str,
    ) -> Tuple[bool, Optional[List[str]]]:
        clarification_needed = False
        clarification_questions: List[str] = []

        ambiguous_indicators = [
            "it",
            "this",
            "that",
            "they",
            "them",
            "he",
            "she",
            "his",
            "her",
            "something",
            "someone",
            "anything",
            "anyone",
            "some",
            "any",
        ]

        question_lower = question.lower()
        found_ambiguous = [
            term for term in ambiguous_indicators if f" {term} " in f" {question_lower} "
        ]
        if found_ambiguous:
            clarification_needed = True
            clarification_questions.append(
                f"Your query contains ambiguous terms ({', '.join(found_ambiguous)}). Could you be more specific about what you're referring to?"
            )

        if isinstance(results, str) and results.strip():
            sentences = results.split(". ")
            if len(sentences) > 5:
                entities = self.extract_potential_entities_from_text(results)
                if len(entities) > 3:
                    clarification_needed = True
                    clarification_questions.append(
                        f"I found information about multiple topics: {', '.join(entities[:3])}. Which specific aspect would you like to know more about?"
                    )
        elif isinstance(results, list) and len(results) > 10:
            subjects = {t.subject for t in results}
            predicates = {t.predicate for t in results}
            if len(subjects) > 5 and len(predicates) > 3:
                clarification_needed = True
                clarification_questions.append(
                    f"Your query returned many relationships involving {len(subjects)} different entities. Would you like to focus on a specific entity or type of relationship?"
                )

        if len(question.strip().split()) <= 2:
            clarification_needed = True
            clarification_questions.append(
                "Your query is quite brief. Could you provide more details about what you're looking for?"
            )

        question_words = ["what", "who", "where", "when", "why", "how", "which"]
        found_question_words = [word for word in question_words if word in question_lower]
        if len(found_question_words) > 2:
            clarification_needed = True
            clarification_questions.append(
                "Your query asks about multiple aspects. Would you like to focus on one specific question at a time?"
            )

        return clarification_needed, (clarification_questions if clarification_questions else None)

    @staticmethod
    def extract_potential_entities_from_text(text: str) -> List[str]:
        """Extract potential entity names from text results."""
        capitalized_words = re.findall(r"\b[A-Z][a-zA-Z]+\b", text)
        common_words = {
            "The",
            "This",
            "That",
            "These",
            "Those",
            "A",
            "An",
            "And",
            "Or",
            "But",
            "In",
            "On",
            "At",
            "To",
            "For",
            "Of",
            "With",
            "By",
            "From",
            "About",
            "When",
            "Where",
            "What",
            "Who",
            "Why",
            "How",
            "Which",
            "Can",
            "Could",
            "Would",
            "Should",
            "Will",
            "May",
            "Might",
            "Must",
            "Shall",
        }
        entities = [word for word in capitalized_words if word not in common_words]
        seen = set()
        unique_entities: List[str] = []
        for ent in entities:
            if ent not in seen:
                seen.add(ent)
                unique_entities.append(ent)
        return unique_entities[:10]
