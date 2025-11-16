"""Adapter using an LLM to parse requirement text into validation rules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from application.ports import LLMPort
from application.ports.requirement_parser_port import RequirementParserPort
from application.use_cases.requirements.generate_requirement_contracts_use_case import (
    ValidationRule,
)


@dataclass
class LLMRequirementParserAdapter(RequirementParserPort):
    """LLM-backed implementation of :class:`RequirementParserPort`."""

    llm: LLMPort
    tenant_id: str = "cli"

    def parse(self, requirements: str) -> List[ValidationRule]:
        prompt = (
            "Parse the following requirements into validation rules.\n"
            "Return one rule per line in the format 'type|name|expression' "
            "where type is precondition, postcondition or invariant.\n"
            f"Requirements:\n{requirements}\n"
        )
        try:
            response = self.llm.generate(prompt=prompt, tenant_id=self.tenant_id)
        except Exception:
            response = ""

        rules: List[ValidationRule] = []
        lines = [line.strip() for line in response.splitlines() if "|" in line]
        if not lines:
            lines = [line.strip() for line in requirements.splitlines() if line.strip()]
            for line in lines:
                rules.append(
                    ValidationRule(name=line, expression=line, kind="invariant")
                )
            return rules

        for line in lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 3:
                kind, name, expr = parts
            else:
                kind = "invariant"
                name = parts[0]
                expr = parts[-1]
            rules.append(ValidationRule(name=name, expression=expr, kind=kind))
        return rules
