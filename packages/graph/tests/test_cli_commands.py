from typer.testing import CliRunner

from permagraph.cli import main as cli_main
from permagraph.cli import skeleton, env_utils, prompts


runner = CliRunner()


def test_create_app_generates_structure(tmp_path, monkeypatch):
    monkeypatch.setattr(prompts, "prompt_env_vars", lambda defaults: defaults)
    result = runner.invoke(cli_main.app, ["create-app", str(tmp_path)])
    assert result.exit_code == 0
    for folder in skeleton.DEFAULT_FOLDERS:
        folder_path = tmp_path / folder
        assert folder_path.is_dir()
        assert (folder_path / "__init__.py").exists()
    env_file = tmp_path / ".env"
    assert env_file.exists()
    content = env_file.read_text()
    for var in ["OPENAI_API_KEY", "GEMINI_API_KEY", "GRAPHRAG_API_KEY"]:
        assert f"{var}=" in content


def test_check_env_fails_with_missing_variable(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=foo\n")
    for var in env_utils.REQUIRED_VARS:
        monkeypatch.delenv(var, raising=False)
    result = runner.invoke(cli_main.app, ["check-env", "--env-file", str(env_file)])
    assert result.exit_code != 0
    assert "Missing variables" in result.stdout


def test_start_api_invokes_env_utils(monkeypatch):
    called = {}
    monkeypatch.setattr(cli_main.env_utils, "start_api", lambda: called.setdefault("called", True))
    result = runner.invoke(cli_main.app, ["start-api"])
    assert result.exit_code == 0
    assert called.get("called")
