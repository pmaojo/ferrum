"""Environment validation and helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Iterable, Mapping

from dotenv import dotenv_values

REQUIRED_VARS: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GRAPHRAG_API_KEY",
    "HYDRA_LLM_MODEL",
    "HYDRA_TEMPERATURE",
    "HYDRA_MAX_TOKENS",
)


def load_env(env_file: Path | None = None) -> Mapping[str, str]:
    """Load environment variables from the OS and optional ``env_file``."""
    env: dict[str, str] = {key: value for key, value in os.environ.items()}
    if env_file:
        file_values = {k: v for k, v in dotenv_values(env_file).items() if v is not None}
        env.update(file_values)
    return env


def validate_required_vars(required: Iterable[str] = REQUIRED_VARS, env_file: Path | None = None) -> list[str]:
    """Return a list of missing variables from ``required``."""
    env = load_env(env_file)
    missing = [var for var in required if not env.get(var)]
    return missing


def start_api(start_main: Callable[[], None] | None = None) -> None:
    """Start the REST API using the provided callable.

    Parameters
    ----------
    start_main:
        Callable that launches the API. Defaults to
        :func:`infrastructure.start_api.main` when ``None``.
    """
    if start_main is None:
        from infrastructure.start_api import main as start_main

    start_main()
