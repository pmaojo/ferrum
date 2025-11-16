"""Compatibility layer for Hypothesis datetime strategies."""
from hypothesis import strategies as st

__all__ = ["datetimes"]

datetimes = st.datetimes
