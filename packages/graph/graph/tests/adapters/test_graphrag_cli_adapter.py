import subprocess
import sys
from types import ModuleType
from unittest.mock import patch
import importlib.util
from pathlib import Path

import pytest

# Avoid optional heavy dependencies during import
sys.modules.setdefault("numpy", ModuleType("numpy"))
sys.modules.setdefault("PIL", ModuleType("PIL"))

MODULE_PATH = Path(__file__).parents[2] / "adapters" / "retrievers" / "graphrag_cli_adapter.py"
spec = importlib.util.spec_from_file_location("graphrag_cli_adapter", MODULE_PATH)
graphrag_cli_adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = graphrag_cli_adapter
spec.loader.exec_module(graphrag_cli_adapter)
GraphRAGCLIAdapter = graphrag_cli_adapter.GraphRAGCLIAdapter
GraphragCLIClient = graphrag_cli_adapter.GraphragCLIClient


def test_index_invokes_cli(tmp_path):
    client = GraphragCLIClient(root_dir=str(tmp_path))
    adapter = GraphRAGCLIAdapter(client)
    with patch("subprocess.run") as run_mock:
        adapter.index(docs=["text"], kg_id="kg", tenant_id="t")
        run_mock.assert_called()


def test_run_invokes_cli(tmp_path):
    client = GraphragCLIClient(root_dir=str(tmp_path))
    adapter = GraphRAGCLIAdapter(client)
    completed = subprocess.CompletedProcess([], 0, stdout="answer", stderr="")
    with patch("subprocess.run", return_value=completed) as run_mock:
        result = adapter.run(
            question="hi", kg_id="kg", tenant_id="t", opts={"method": "local"}
        )
        run_mock.assert_called()
        cmd = run_mock.call_args[0][0]
        assert "--method" in cmd and "local" in cmd
        assert result == "answer"

        
def test_index_initializes_workspace_when_missing(tmp_path):
    client = GraphragCLIClient(root_dir=str(tmp_path))
    adapter = GraphRAGCLIAdapter(client)
    with patch("subprocess.run") as run_mock:
        adapter.index(docs=["text"], kg_id="kg", tenant_id="t")
        init_cmd = [
            sys.executable,
            "-m",
            "graphrag.index",
            "--init",
            "--root",
            str(tmp_path),
        ]
        index_cmd = [
            sys.executable,
            "-m",
            "graphrag.index",
            "--root",
            str(tmp_path),
        ]
        run_mock.assert_any_call(
            init_cmd, check=True, capture_output=True, text=True
        )
        run_mock.assert_any_call(
            index_cmd, check=True, capture_output=True, text=True
        )

def test_write_documents_error(tmp_path):
    client = GraphragCLIClient(root_dir=str(tmp_path))
    with patch("builtins.open", side_effect=OSError("boom")):
        with pytest.raises(graphrag_cli_adapter.GraphRAGException) as excinfo:
            client.write_documents(["doc"], tenant_id="t")
    assert excinfo.value.error_code == "CLI_WRITE_ERROR"

