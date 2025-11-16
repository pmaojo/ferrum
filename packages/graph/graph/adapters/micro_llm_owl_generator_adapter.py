from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from application.ports import LLMPort, OwlAxiomGeneratorPort

logger = logging.getLogger(__name__)


class MicroLLMOwlGeneratorAdapter(OwlAxiomGeneratorPort):
    """Adapter using a lightweight LLM to generate OWL axioms."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def generate_axioms(
        self,
        *,
        text: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        prompt = (
            "Convert the following text into OWL axioms using Manchester syntax.\n"
            f"{text}\nAxioms:"
        )
        logger.info("Generating OWL axioms from text snippet")
        result = self._llm.generate(prompt=prompt, tenant_id=tenant_id, opts=opts)
        axioms = [line.strip() for line in result.splitlines() if line.strip()]
        return axioms
