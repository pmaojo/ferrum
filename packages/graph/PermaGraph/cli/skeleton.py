"""Project scaffolding utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping


DEFAULT_FOLDERS: tuple[str, ...] = (
    "application",
    "adapters",
    "ui_adapters",
    "infrastructure",
    "domain",
    "database",
)


def create_project_skeleton(base_path: Path, folders: Iterable[str] = DEFAULT_FOLDERS) -> None:
    """Create project folders with ``__init__`` files."""
    for folder in folders:
        path = base_path / folder
        path.mkdir(parents=True, exist_ok=True)
        init_file = path / "__init__.py"
        if not init_file.exists():
            init_file.write_text("\n")


def write_env_file(base_path: Path, values: Mapping[str, str]) -> None:
    """Write environment variables to ``.env``."""
    env_lines = [f"{key}={value}" for key, value in values.items()]
    (base_path / ".env").write_text("\n".join(env_lines) + "\n")
