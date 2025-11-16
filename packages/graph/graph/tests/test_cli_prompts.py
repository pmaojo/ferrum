from permagraph.cli.prompts import prompt_env_vars

def test_prompt_env_vars_custom_ask(monkeypatch):
    answers = {"A": "1", "B": "2"}
    def fake_ask(var: str, default: str) -> str:
        return answers[var]
    result = prompt_env_vars({"A": "", "B": ""}, ask=fake_ask)
    assert result == answers
