"""LLM-based adapter for persona generation."""

from typing import Dict, List, Optional

from application.ports import LLMPort, PersonaGeneratorPort


class PersonaGeneratorAdapter(PersonaGeneratorPort):
    """Generate personas using an injected LLM port."""

    def __init__(self, llm: LLMPort):
        self.llm = llm

    def generate_personas(
        self,
        *,
        description: str,
        tenant_id: str,
        num_personas: int = 3,
        opts: Optional[Dict[str, object]] = None,
    ) -> List[str]:
        prompt = (
            "Generate "
            f"{num_personas} distinct user personas for the following project description:\n"
            f"{description}\n"
            "Return each persona on a separate line."
        )
        response = self.llm.generate(prompt=prompt, tenant_id=tenant_id, opts=opts)
        personas = [line.strip("- ") for line in response.splitlines() if line.strip()]
        return personas
