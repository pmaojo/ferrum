from typer.testing import CliRunner

from permagraph.cli import main as cli_main
from permagraph.cli import prompts, env_utils, skeleton

runner = CliRunner()


def test_wizard_creates_project_and_validates(tmp_path, monkeypatch):
    env_values = {
        "OPENAI_API_KEY": "1",
        "GEMINI_API_KEY": "2",
        "GRAPHRAG_API_KEY": "3",
    }
    monkeypatch.setattr(prompts, "prompt_env_vars", lambda defaults: env_values)
    called = {}

    def fake_validate(required=env_utils.REQUIRED_VARS, env_file=None):
        called["env_file"] = env_file
        return []

    monkeypatch.setattr(env_utils, "validate_required_vars", fake_validate)
    result = runner.invoke(cli_main.app, ["wizard", str(tmp_path)])
    assert result.exit_code == 0
    for folder in skeleton.DEFAULT_FOLDERS:
        assert (tmp_path / folder).is_dir()
    env_file = tmp_path / ".env"
    assert env_file.read_text() == "OPENAI_API_KEY=1\nGEMINI_API_KEY=2\nGRAPHRAG_API_KEY=3\n"
    assert called["env_file"] == env_file
    assert "Project created at" in result.stdout
    assert "All required variables are set" in result.stdout


def test_wizard_reports_missing_vars(tmp_path, monkeypatch):
    env_values = {
        "OPENAI_API_KEY": "",
        "GEMINI_API_KEY": "x",
        "GRAPHRAG_API_KEY": "",
    }
    monkeypatch.setattr(prompts, "prompt_env_vars", lambda defaults: env_values)

    def fake_validate(required=env_utils.REQUIRED_VARS, env_file=None):
        return ["OPENAI_API_KEY"]

    monkeypatch.setattr(env_utils, "validate_required_vars", fake_validate)
    result = runner.invoke(cli_main.app, ["wizard", str(tmp_path)])
    assert result.exit_code != 0
    assert "Missing variables: OPENAI_API_KEY" in result.stdout
