"""User interaction helpers using questionary."""

from __future__ import annotations

from typing import Callable, Mapping, MutableMapping

import questionary

PromptFunc = Callable[[str, str], str | None]


def prompt_env_vars(
    defaults: Mapping[str, str], ask: PromptFunc | None = None
) -> MutableMapping[str, str]:
    """Ask the user for environment variables.

    Parameters
    ----------
    defaults:
        Mapping of variable names to default values.
    ask:
        Optional custom prompting function for testing.

    Returns
    -------
    Dict with variable names and user provided values.
    """
    asker = ask or (lambda var, default: questionary.text(f"{var}:", default=default).ask())
    values: MutableMapping[str, str] = {}
    for var, default in defaults.items():
        answer = asker(var, default)
        values[var] = answer if answer is not None else default
    return values
