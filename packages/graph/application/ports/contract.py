"""Port definitions for contract verification and repair."""

from typing import Any, Dict, List, Protocol, Tuple

from application.contracts import Contract


class ContractPort(Protocol):
    """Port for verifying and repairing contracts."""

    def verify(
        self,
        contract: Contract,
        *,
        kg_id: str,
        tenant_id: str,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Verify contract conditions."""
        ...

    def repair(
        self,
        contract: Contract,
        *,
        kg_id: str,
        tenant_id: str,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Attempt to repair failures by retrying or applying fixes."""
        ...
