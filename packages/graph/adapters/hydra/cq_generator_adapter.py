"""LLM-based adapter for competency question generation."""

from typing import Dict, List, Optional

from application.ports import CompetencyQuestionPort, LLMPort


class CompetencyQuestionGeneratorAdapter(CompetencyQuestionPort):
    """Generate competency questions using an injected LLM port."""

    def __init__(self, llm: LLMPort):
        self.llm = llm

    def generate_competency_questions(
        self,
        *,
        context: str,
        tenant_id: str,
        num_questions: int = 10,
        opts: Optional[Dict[str, object]] = None,
    ) -> List[str]:
        prompt = (
            "Generate "
            f"{num_questions} distinct competency questions for the following context:\n"
            f"{context}\n"
            "Return each question on a separate line."
        )
        response = self.llm.generate(prompt=prompt, tenant_id=tenant_id, opts=opts)
        questions: List[str] = []
        seen = set()
        for line in response.splitlines():
            question = line.strip("- ").strip()
            if question and question not in seen:
                seen.add(question)
                questions.append(question)
        return questions

