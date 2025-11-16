from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml

from application.ports import LLMPort
from application.ports.configuration import ConfigurationPort, ConfigurationScope


logger = logging.getLogger(__name__)


class ConfigTemplateService:
    """Assemble tenant configuration templates using an ontology assistant."""

    QUESTIONS: List[str] = [
        "Provide GraphRAG SDK configuration as YAML",
        "Provide ontology configuration as YAML",
        "Provide workflow configuration as YAML",
    ]

    def __init__(self, llm: LLMPort, configuration_port: ConfigurationPort) -> None:
        self._llm = llm
        self._config_port = configuration_port

    def _ask(self, question: str, tenant_id: str) -> Dict[str, Any]:
        """Ask the LLM a question and parse the YAML response.

        Parameters
        ----------
        question: str
            Prompt sent to the LLM.
        tenant_id: str
            Identifier for the tenant issuing the request.

        Returns
        -------
        Dict[str, Any]
            Parsed configuration data. Returns an empty dictionary when the
            response cannot be parsed as valid YAML or is not a mapping.

        Raises
        ------
        None
            All parsing errors are caught and logged.
        """

        answer = self._llm.generate(prompt=question, tenant_id=tenant_id)
        try:
            data = yaml.safe_load(answer) or {}
        except yaml.YAMLError as exc:
            logger.error("Failed to parse YAML response: %s", exc)
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    def assemble_configuration(self, tenant_id: str) -> Dict[str, Any]:
        """Assemble a configuration dictionary for a tenant.

        Parameters
        ----------
        tenant_id: str
            Identifier for the tenant whose configuration is assembled.

        Returns
        -------
        Dict[str, Any]
            Combined configuration generated from LLM responses.

        Raises
        ------
        ValueError
            If configuration validation fails.
        """

        config: Dict[str, Any] = {}
        for question in self.QUESTIONS:
            config.update(self._ask(question, tenant_id))
        errors = self._config_port.validate_configuration(
            ConfigurationScope.TENANT, config
        )
        if errors:
            raise ValueError("; ".join(errors))
        return config

    def generate_yaml(self, tenant_id: str) -> str:
        """Generate YAML configuration for a tenant.

        Parameters
        ----------
        tenant_id: str
            Identifier for the tenant whose configuration is generated.

        Returns
        -------
        str
            YAML representation of the assembled configuration.

        Raises
        ------
        ValueError
            Propagated from :meth:`assemble_configuration` if validation fails.
        """

        config = self.assemble_configuration(tenant_id)
        return yaml.safe_dump(config, sort_keys=False)


TEMPLATES_ROOT = Path(__file__).resolve().parents[4] / "templates"


def load_template(template_path: str) -> Dict[str, Any]:
    """Load a template file from the repository's templates directory."""
    full_path = TEMPLATES_ROOT / template_path
    if full_path.suffix in {".yml", ".yaml"}:
        with full_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    with full_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_templates(subdir: str = "") -> List[str]:
    """List template files within the templates directory."""
    dir_path = TEMPLATES_ROOT / subdir
    if not dir_path.exists():
        return []
    return sorted(
        [
            p.name
            for p in dir_path.iterdir()
            if p.suffix in {".json", ".yml", ".yaml"}
        ]
    )
