from ai.agents import validator


class FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def run(self, *args, **kwargs):
        class R:
            def single(self_inner):
                return {}
        return R()


class FakeDriver:
    def session(self):
        return FakeSession()

    def close(self):
        pass


def test_invalid_structure_returns_false(monkeypatch):
    monkeypatch.setattr(validator, "_get_graph_driver", lambda: FakeDriver())
    result = validator.validate_yaml_with_graph("- just\n- a\n- list")
    assert result is False
