"""GraphRAG CLI adapter for local workflows."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from application.ports import GraphRetrieverPort
from domain.entities import Triple
from domain.services import GraphRAGException

logger = logging.getLogger(__name__)


@dataclass
class GraphragCLIClient:
    """Lightweight wrapper around the ``graphrag`` command line interface."""

    root_dir: str
    python_exec: str = sys.executable

    def _run(self, args: List[str], *, error_code: str, error_msg: str) -> None:
        """Execute a CLI command and raise ``GraphRAGException`` on failure."""
        cmd = [self.python_exec, "-m", *args, "--root", self.root_dir]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:  # pragma: no cover - runtime
            logger.error("%s: %s", error_msg, exc.stderr)
            raise GraphRAGException(
                message=error_msg,
                error_code=error_code,
                context={"stderr": exc.stderr},
            ) from exc

    def _is_initialized(self) -> bool:
        """Return ``True`` if the workspace contains required files."""
        settings = os.path.join(self.root_dir, "settings.yaml")
        input_dir = os.path.join(self.root_dir, "input")
        return os.path.isfile(settings) and os.path.isdir(input_dir)

    def index(self) -> None:
        """Run ``graphrag.index`` to ingest documents, initializing if needed."""
        if not self._is_initialized():
            self._run(
                ["graphrag.index", "--init"],
                error_code="CLI_INIT_ERROR",
                error_msg="GraphRAG CLI initialization failed",
            )
        self._run(
            ["graphrag.index"],
            error_code="CLI_INDEX_ERROR",
            error_msg="GraphRAG CLI indexing failed",
        )

    def query(
        self,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Run ``graphrag.query`` and return the raw response.

        Args:
            question: Natural language question to ask.
            kg_id: Knowledge graph identifier used for logging.
            tenant_id: Tenant identifier used for logging.
            opts: Optional CLI parameters. Supported keys include ``method``,
                ``max_hops`` and ``context_tokens``.
        """
        cmd = [
            self.python_exec,
            "-m",
            "graphrag.query",
            "--root",
            self.root_dir,
        ]
        method = opts.get("method", "global") if opts else "global"
        cmd.extend(["--method", method])
        if opts:
            if "max_hops" in opts:
                cmd.extend(["--max-hops", str(opts["max_hops"])])
            if "context_tokens" in opts:
                cmd.extend(["--context-tokens", str(opts["context_tokens"])])
        cmd.append(question)
        logger.info(
            "Executing GraphRAG CLI query for kg_id=%s tenant_id=%s",
            kg_id,
            tenant_id,
        )
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as exc:  # pragma: no cover - runtime
            logger.error("GraphRAG CLI query failed: %s", exc.stderr)
            raise GraphRAGException(
                message="GraphRAG CLI query failed",
                error_code="CLI_QUERY_ERROR",
                context={
                    "stderr": exc.stderr,
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                },
            ) from exc

    def write_documents(self, docs: List[str], tenant_id: str) -> None:
        """Write documents to the expected ``input`` directory."""
        input_dir = os.path.join(self.root_dir, "input")
        os.makedirs(input_dir, exist_ok=True)
        for idx, content in enumerate(docs):
            filename = f"{tenant_id}_{idx}.txt"
            path = os.path.join(input_dir, filename)
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)
            except OSError as exc:  # pragma: no cover - runtime file system errors
                logger.error("Failed to write document %s: %s", path, exc)
                raise GraphRAGException(
                    message="GraphRAG CLI write failed",
                    error_code="CLI_WRITE_ERROR",
                    context={"path": path, "error": str(exc)},
                ) from exc


class GraphRAGCLIAdapter(GraphRetrieverPort):
    """Adapter that delegates indexing and querying to the GraphRAG CLI."""

    def __init__(self, client: GraphragCLIClient) -> None:
        self.client = client

    def index(self, *, docs: List[str], kg_id: str, tenant_id: str) -> List[Triple]:
        self.client.write_documents(docs, tenant_id)
        self.client.index()
        return []

    def run(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, List[Triple]]:
        """Execute a query through the GraphRAG CLI.

        Args:
            question: Natural language question.
            kg_id: Knowledge graph identifier for logging.
            tenant_id: Tenant identifier for logging.
            opts: Optional CLI parameters forwarded to ``graphrag.query``.

        Returns:
            Raw string response from the GraphRAG CLI.
        """
        effective_opts = opts or {}
        logger.debug(
            "GraphRAGCLIAdapter.run question=%s kg_id=%s tenant_id=%s opts=%s",
            question,
            kg_id,
            tenant_id,
            effective_opts,
        )
        return self.client.query(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            opts=effective_opts,
        )
