from permagraph.cli import env_utils


def test_start_api_with_callable(monkeypatch):
    called = {}

    def fake_main():
        called['called'] = True

    env_utils.start_api(fake_main)

    assert called.get('called')


def test_start_api_default(monkeypatch):
    called = {}
    import infrastructure.start_api as start_api_module

    def fake_main():
        called['called'] = True

    monkeypatch.setattr(start_api_module, 'main', fake_main)
    env_utils.start_api()

    assert called.get('called')
