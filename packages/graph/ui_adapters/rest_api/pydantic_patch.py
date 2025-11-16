"""Parches de configuración Pydantic para la API REST.

Evita errores al registrar rutas FastAPI cuando existen parámetros o
atributos auxiliares con nombres iniciados por guion bajo, relajando la
protección de nombres reservados en BaseModel.
"""
from __future__ import annotations

from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict


def patch_protected_namespaces() -> None:
    """Relaja protected_namespaces para permitir campos con `_` inicial.

    Esto mitiga el error: "Fields must not use names with leading underscores".
    Solo se aplica una vez y es seguro si se invoca repetidamente.
    """
    # Si ya fue parcheado, no repetir
    current = getattr(_BaseModel, "model_config", None)
    if current and getattr(current, "protected_namespaces", None) == ():  # type: ignore[attr-defined]
        return
    try:
        _BaseModel.model_config = ConfigDict(protected_namespaces=())  # type: ignore[attr-defined]
    except Exception:
        # Fallback silencioso; si falla no bloquea arranque.
        pass
