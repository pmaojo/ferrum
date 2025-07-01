import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

from services.llm_client import call_llm
from agents.validator import validate_yaml
from agents.filler import fetch_context


class Toolset:
    """Collection of helper tools for AI agents."""

    def analyze_graph(self, yaml: str) -> Dict[str, Any]:
        """Return analysis info for a YAML graph using the CLI."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "grafo.yaml"
            path.write_text(yaml)
            cmd = [
                "cargo",
                "run",
                "--quiet",
                "--",
                "analyze",
                str(path),
                "--json",
            ]
            out = subprocess.check_output(cmd, cwd=Path(__file__).resolve().parents[1])
            return json.loads(out)

    def get_node_context(self, node_id: str) -> Dict[str, Any]:
        """Fetch dependency context for a node from Neo4j."""
        context = fetch_context(node_id)
        return {"context": context}

    def validate_yaml(self, yaml: str) -> bool:
        """Validate the YAML structure."""
        return validate_yaml(yaml)

    def call_llm(self, user: str, system: str, model: str | None = None) -> str:
        """Call the configured LLM client."""
        return call_llm(user, system, model)

    def suggest_refactor(self, yaml: str, model: str | None = None) -> str:
        """Suggest refactors for a grafo YAML."""
        prompt = f"Sugerencias de refactor para este YAML:\n{yaml}"
        return call_llm(prompt, "Eres un asistente de refactorización de Ferrum", model)

    def get_ast(self, node_id: str) -> Dict[str, Any]:
        """Return AST info for a node using Neo4j context."""
        return fetch_context(node_id)

    def simulate_flow(self, yaml: str, model: str | None = None) -> str:
        """Simulate execution flow for a given YAML."""
        prompt = f"Simula el flujo de ejecución para este YAML:\n{yaml}"
        return call_llm(prompt, "Eres un simulador de flujos Ferrum", model)
