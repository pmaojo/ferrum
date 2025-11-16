#!/usr/bin/env python3
"""Example using ``GraphRAGCLIAdapter`` for local graphs.

This script writes a couple of documents to the GraphRAG CLI workspace and
executes a question using the CLI.  It expects an initialized workspace (see
``graphrag.index --init``).  If the workspace is missing it will attempt to
create it automatically.  The :meth:`GraphRAGCLIAdapter.run` method requires a
knowledge-graph identifier (``kg_id``) and ``tenant_id`` for logging and routing
and accepts additional CLI options via the ``opts`` parameter.
"""

from __future__ import annotations

import os
import subprocess
import sys
from adapters.retrievers.graphrag_cli_adapter import (
    GraphragCLIAdapter,
    GraphragCLIClient,
)


def _workspace_ready(path: str) -> bool:
    """Return ``True`` if a minimal GraphRAG workspace exists."""

    required = ("settings.yaml", "input")
    return all(os.path.exists(os.path.join(path, item)) for item in required)


def _initialize_workspace(path: str, python_exec: str = sys.executable) -> None:
    """Initialize GraphRAG workspace using the CLI."""

    cmd = [python_exec, "-m", "graphrag.index", "--init", "--root", path]
    subprocess.run(cmd, check=True)


def main() -> None:
    client = GraphragCLIClient(root_dir=os.getenv("GRAPHRAG_ROOT", "rag"))

    if not _workspace_ready(client.root_dir):
        print(
            f"\u26a0\ufe0f Workspace not found in '{client.root_dir}'. "
            "Initializing using graphrag.index --init..."
        )
        try:
            _initialize_workspace(client.root_dir, client.python_exec)
            print("\u2705 Workspace initialized successfully")
        except Exception as exc:  # pragma: no cover - runtime only
            raise SystemExit(
                "Failed to initialize GraphRAG workspace\n"
                f"Run `python -m graphrag.index --init --root {client.root_dir}` "
                "and ensure the GraphRAG package is installed."
            ) from exc

    adapter = GraphRAGCLIAdapter(client)

    docs = [
        "GraphRAG allows building knowledge graphs locally using language models.",
        "Ollama can serve both LLMs and embedding models for full offline use.",
    ]
    adapter.index(docs=docs, kg_id="local", tenant_id="demo")

    answer = adapter.run(
        question="What does the corpus mention?",
        kg_id="local",
        tenant_id="demo",
        opts={"method": "local"},
    )
    print(f"Answer: {answer}")


if __name__ == "__main__":
    main()
