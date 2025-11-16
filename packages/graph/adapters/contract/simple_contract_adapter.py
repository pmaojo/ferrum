from __future__ import annotations

"""Simple adapter for contract verification with retry support."""

from typing import Any, Dict, List, Tuple

from application.contracts import Contract
from application.ports.contract import ContractPort
from application.use_cases.knowledge_graph.validate_knowledge_graph_use_case import (
    KnowledgeGraphValidatorPort,
)
from adapters.knowledge_graph.rule_based_validator_adapter import (
    RuleBasedValidatorAdapter,
)


class SimpleContractAdapter(ContractPort):
    """Validate contract conditions using a knowledge graph validator.

    The adapter retries verification on failure up to ``max_retries`` times,
    which provides a basic repair mechanism.
    """

    def __init__(
        self,
        validator: KnowledgeGraphValidatorPort | None = None,
        *,
        max_retries: int = 3,
    ) -> None:
        self.validator = validator or RuleBasedValidatorAdapter()
        self.max_retries = max_retries

    def verify(
        self,
        contract: Contract,
        *,
        kg_id: str,
        tenant_id: str,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Verify the contract using the configured validator."""

        return contract.verify(self.validator, kg_id=kg_id, tenant_id=tenant_id)

    def repair(
        self,
        contract: Contract,
        *,
        kg_id: str,
        tenant_id: str,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Retry verification until success or ``max_retries`` is reached."""

        last_details: List[Dict[str, Any]] = []
        for _ in range(self.max_retries):
            is_valid, details = self.verify(
                contract, kg_id=kg_id, tenant_id=tenant_id
            )
            last_details = details
            if is_valid:
                return True, details
        return False, last_details
