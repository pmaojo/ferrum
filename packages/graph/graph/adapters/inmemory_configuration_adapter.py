from __future__ import annotations

from typing import Any, Dict, List, Optional

import jsonschema

from application.ports.configuration import ConfigurationPort, ConfigurationScope


class InMemoryConfigurationAdapter(ConfigurationPort):
    """Simple in-memory implementation of :class:`ConfigurationPort`."""

    def __init__(
        self,
        schemas: Optional[Dict[ConfigurationScope, Dict[str, Any]]] = None,
    ) -> None:
        self._schemas = schemas or {
            ConfigurationScope.SYSTEM: {"type": "object"},
            ConfigurationScope.TENANT: {"type": "object"},
            ConfigurationScope.USER: {"type": "object"},
        }
        self._storage: Dict[ConfigurationScope, Dict[str, Any]] = {
            ConfigurationScope.SYSTEM: {},
            ConfigurationScope.TENANT: {},
            ConfigurationScope.USER: {},
        }

    def get_configuration(
        self, scope: ConfigurationScope, scope_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return self._storage.get(scope, {}).get(scope_id or "default", {})

    def update_configuration(
        self,
        scope: ConfigurationScope,
        settings: Dict[str, Any],
        scope_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._storage.setdefault(scope, {})[scope_id or "default"] = settings
        return settings

    def get_configuration_schema(self, scope: ConfigurationScope) -> Dict[str, Any]:
        return self._schemas.get(scope, {"type": "object"})

    def validate_configuration(
        self, scope: ConfigurationScope, settings: Dict[str, Any]
    ) -> List[str]:
        schema = self.get_configuration_schema(scope)
        try:
            jsonschema.validate(instance=settings, schema=schema)
        except jsonschema.ValidationError as exc:
            return [exc.message]
        return []
