"""Configuration ports for system configuration management."""

from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class ConfigurationScope(str, Enum):
    """Scope of configuration settings."""

    SYSTEM = "system"
    TENANT = "tenant"
    USER = "user"


class ConfigurationPort(Protocol):
    """Port for configuration management operations."""

    def get_configuration(
        self, scope: ConfigurationScope, scope_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get configuration for a specific scope.

        Args:
            scope: The configuration scope (system, tenant, user)
            scope_id: The identifier for tenant or user scope (not needed for system scope)

        Returns:
            Dictionary of configuration settings
        """
        ...

    def update_configuration(
        self,
        scope: ConfigurationScope,
        settings: Dict[str, Any],
        scope_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update configuration for a specific scope.

        Args:
            scope: The configuration scope (system, tenant, user)
            settings: Dictionary of settings to update
            scope_id: The identifier for tenant or user scope (not needed for system scope)

        Returns:
            Updated configuration dictionary
        """
        ...

    def get_configuration_schema(self, scope: ConfigurationScope) -> Dict[str, Any]:
        """Get JSON schema for configuration validation.

        Args:
            scope: The configuration scope (system, tenant, user)

        Returns:
            JSON schema for validating configuration
        """
        ...

    def validate_configuration(
        self, scope: ConfigurationScope, settings: Dict[str, Any]
    ) -> List[str]:
        """Validate configuration against schema.

        Args:
            scope: The configuration scope (system, tenant, user)
            settings: Dictionary of settings to validate

        Returns:
            List of validation errors (empty if valid)
        """
        ...
