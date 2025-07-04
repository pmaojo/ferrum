import importlib
import types
import sys
from pathlib import Path

def test_import_team_as_script(tmp_path, monkeypatch):
    # Simulate running from ai/ directory with modules at top level
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    monkeypatch.syspath_prepend(str(root))

    # Stub toolset to avoid heavy dependencies
    toolset = types.ModuleType('toolset')
    toolset.Toolset = object
    sys.modules['toolset'] = toolset

    mod = importlib.import_module('agents.team')
    assert hasattr(mod, 'BackendExpert')
    assert hasattr(mod, 'FrontendExpert')
    assert hasattr(mod, 'UXDesigner')
    assert hasattr(mod, 'Coach')

    sys.path.remove(str(root))
