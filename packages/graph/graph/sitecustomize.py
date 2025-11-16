# sitecustomize.py - Custom site initialization for the application
from __future__ import annotations

import importlib.util
import os
import sys
import types

# Register ``hypothesis.extra.datetime`` only when the Hypothesis library is
# available. This avoids runtime errors in environments where Hypothesis is not
# installed, while still providing the compatibility layer for tests when it is
# present.

# Ensure 'hypothesis.extra.datetime' is available even if the installed
# Hypothesis version does not provide it.

extra_dir = os.path.join(
    os.path.dirname(__file__), "infrastructure", "stubs", "hypothesis", "extra"
)


module_path = os.path.join(extra_dir, "datetime.py")

if importlib.util.find_spec("hypothesis") and os.path.isfile(module_path):
    spec = importlib.util.spec_from_file_location(
        "hypothesis.extra.datetime", module_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    package = types.ModuleType("hypothesis.extra")
    package.__path__ = [extra_dir]
    sys.modules.setdefault("hypothesis.extra", package)
    sys.modules["hypothesis.extra.datetime"] = module

# Provide pytest.ANY for older pytest versions
try:
    import pytest
    from unittest.mock import ANY as _ANY
    if not hasattr(pytest, "ANY"):
        pytest.ANY = _ANY
except Exception:
    pass

# Suppress Hypothesis health check for function-scoped fixtures
try:
    import hypothesis
    from hypothesis import HealthCheck, settings

    hypothesis.settings.register_profile(
        "codex", settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    )
    hypothesis.settings.load_profile("codex")
except Exception:
    pass
