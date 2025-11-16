"""LLM-based adapter for scope document generation."""

from typing import Dict, Optional

from application.ports import LLMPort, ScopeGeneratorPort


class ScopeGeneratorAdapter(ScopeGeneratorPort):
    """Generate scope documents using an injected LLM port."""

    def __init__(self, llm: LLMPort):
        self.llm = llm

    def generate_scope_document(
        self,
        *,
        description: str,
        tenant_id: str,
        opts: Optional[Dict[str, object]] = None,
    ) -> str:
        prompt = (
            "Create a concise project scope document based on the following description:\n"
            f"{description}"
        )
        return self.llm.generate(prompt=prompt, tenant_id=tenant_id, opts=opts)
