"""Tests for the hydra CLI command."""

from typer.testing import CliRunner

from permagraph.cli import main as cli_main


def test_hydra_command_runs(tmp_path):
    doc = tmp_path / "doc.txt"
    doc.write_text("demo")

    runner = CliRunner()
    result = runner.invoke(
        cli_main.app,
        [
            "hydra",
            "--description",
            "demo domain",
            "--document",
            str(doc),
            "--contract",
        ],
    )

    assert result.exit_code == 0
    stdout = result.stdout
    assert "Personas" in stdout
    assert "Scope document" in stdout
    assert "Competency Questions" in stdout
    assert "Verification report" in stdout
    assert "Evaluation metrics" in stdout

