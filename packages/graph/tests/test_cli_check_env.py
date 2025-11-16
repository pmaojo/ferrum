from pathlib import Path

from typer.testing import CliRunner

from permagraph.cli.main import app


def test_check_env_uses_os(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("")

    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("GRAPHRAG_API_KEY", "test-graphrag")

    runner = CliRunner()
    result = runner.invoke(app, ["check-env", "--env-file", str(env_file)])

    assert result.exit_code == 0
    assert "All required variables are set" in result.stdout
