"""Additional utilities for Hypothesis provided for compatibility."""
from hypothesis import strategies as st
import importlib.util
import os
import sys

# Re-export common strategies if needed
__all__ = ["datetimes"]

def datetimes(*args, **kwargs):
    return st.datetimes(*args, **kwargs)

# Ensure `hypothesis.extra.datetime` is available even if the installed
# Hypothesis package lacks it.
module_path = os.path.join(os.path.dirname(__file__), "datetime.py")
spec = importlib.util.spec_from_file_location(
    "hypothesis.extra.datetime", module_path
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.modules.setdefault("hypothesis.extra.datetime", module)
