"""Use case for managing system configuration."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from application.exceptions import ApplicationError, AuthorizationError, ValidationError
from application.ports import AuthorizationPort, TracingPort
from application.ports.configuration import ConfigurationPort, ConfigurationScope
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseRequestDTO, BaseResponseDTO


@dataclass
class GetSystemConfigurationRequest(BaseRequestDTO):
    """Request to get system configuration."""

    user_id: str
    scope: str = "system"  # system, tenant, user
    scope_id: Optional[str] = None  # Required for tenant and user scopes


@dataclass
class UpdateSystemConfigurationRequest(BaseRequestDTO):
    """Request to update system configuration."""

    user_id: str
    settings: Dict[str, Any]
    scope: str = "system"  # system, tenant, user
    scope_id: Optional[str] = None  # Required for tenant and user scopes


@dataclass
class SystemConfigurationDTO:
    """DTO for system configuration."""

    settings: Dict[str, Any]
    scope: str
    scope_id: Optional[str] = None
    last_updated: datetime = None


@dataclass
class GetSystemConfigurationResponse(BaseResponseDTO):
    """Response containing system configuration."""

    configuration: Optional[SystemConfigurationDTO] = None


@dataclass
class UpdateSystemConfigurationResponse(BaseResponseDTO):
    """Response after updating system configuration."""

    configuration: Optional[SystemConfigurationDTO] = None
    validation_errors: List[str] = None


class ManageSystemConfigurationUseCase(BaseUseCase):
    """Use case for managing system configuration."""

    def __init__(
        self,
        configuration_port: ConfigurationPort,
        authorization_port: AuthorizationPort,
        tracer: TracingPort,
    ):
        super().__init__()
        self.configuration_port = configuration_port
        self.authorization_port = authorization_port
        self.tracer = tracer

    def _validate_get_request(self, request: GetSystemConfigurationRequest) -> None:
        """Validate get configuration request."""
        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

        try:
            scope = ConfigurationScope(request.scope)
        except ValueError:
            raise ValidationError(
                message=f"Invalid scope: {request.scope}. Must be one of: {', '.join([s.value for s in ConfigurationScope])}",
                field="scope",
            )

        if scope != ConfigurationScope.SYSTEM and not request.scope_id:
            raise ValidationError(
                message=f"Scope ID is required for {request.scope} scope",
                field="scope_id",
            )

    def _validate_update_request(
        self, request: UpdateSystemConfigurationRequest
    ) -> None:
        """Validate update configuration request."""
        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

        if not request.settings:
            raise ValidationError(message="Settings cannot be empty", field="settings")

        try:
            scope = ConfigurationScope(request.scope)
        except ValueError:
            raise ValidationError(
                message=f"Invalid scope: {request.scope}. Must be one of: {', '.join([s.value for s in ConfigurationScope])}",
                field="scope",
            )

        if scope != ConfigurationScope.SYSTEM and not request.scope_id:
            raise ValidationError(
                message=f"Scope ID is required for {request.scope} scope",
                field="scope_id",
            )

    async def get_configuration(
        self, request: GetSystemConfigurationRequest
    ) -> GetSystemConfigurationResponse:
        """Get system configuration."""
        start_time = datetime.utcnow()
        with self.tracer.start_span(
            name="get_system_configuration",
            user_id=request.user_id,
            scope=request.scope,
            scope_id=request.scope_id,
        ):
            try:
                # Validate request
                self._validate_get_request(request)

                # Convert string scope to enum
                scope = ConfigurationScope(request.scope)

                # Check authorization
                permission = f"view_{request.scope}_configuration"
                try:
                    self.authorization_port.check_permission(
                        user_id=request.user_id,
                        resource_type="configuration",
                        permission=permission,
                    )
                except Exception as e:
                    raise AuthorizationError(
                        message=f"User does not have permission to view {request.scope} configuration",
                        user_id=request.user_id,
                        resource_type="configuration",
                        permission=permission,
                    ) from e

                # Get configuration
                settings = self.configuration_port.get_configuration(
                    scope=scope, scope_id=request.scope_id
                )

                # Create response
                config_dto = SystemConfigurationDTO(
                    settings=settings,
                    scope=request.scope,
                    scope_id=request.scope_id,
                    last_updated=datetime.utcnow(),  # Ideally this would come from the configuration store
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="system_configuration_get", value=1, scope=request.scope
                )

                return GetSystemConfigurationResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    configuration=config_dto,
                )
            except Exception as e:
                self.tracer.record_metric(
                    name="system_configuration_get_errors",
                    value=1,
                    error_type=type(e).__name__,
                )
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                if isinstance(e, (ValidationError, AuthorizationError)):
                    return GetSystemConfigurationResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )
                raise ApplicationError(
                    message=f"Failed to get system configuration: {e}",
                    error_code="CONFIG_GET_FAILED",
                ) from e

    async def update_configuration(
        self, request: UpdateSystemConfigurationRequest
    ) -> UpdateSystemConfigurationResponse:
        """Update system configuration."""
        start_time = datetime.utcnow()
        with self.tracer.start_span(
            name="update_system_configuration",
            user_id=request.user_id,
            scope=request.scope,
            scope_id=request.scope_id,
        ):
            try:
                # Validate request
                self._validate_update_request(request)

                # Convert string scope to enum
                scope = ConfigurationScope(request.scope)

                # Check authorization
                permission = f"manage_{request.scope}_configuration"
                try:
                    self.authorization_port.check_permission(
                        user_id=request.user_id,
                        resource_type="configuration",
                        permission=permission,
                    )
                except Exception as e:
                    raise AuthorizationError(
                        message=f"User does not have permission to manage {request.scope} configuration",
                        user_id=request.user_id,
                        resource_type="configuration",
                        permission=permission,
                    ) from e

                # Validate configuration against schema
                validation_errors = self.configuration_port.validate_configuration(
                    scope=scope, settings=request.settings
                )

                if validation_errors:
                    processing_time = (
                        datetime.utcnow() - start_time
                    ).total_seconds() * 1000
                    return UpdateSystemConfigurationResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message="Configuration validation failed",
                        validation_errors=validation_errors,
                    )

                # Update configuration
                updated_settings = self.configuration_port.update_configuration(
                    scope=scope, settings=request.settings, scope_id=request.scope_id
                )

                # Create response
                config_dto = SystemConfigurationDTO(
                    settings=updated_settings,
                    scope=request.scope,
                    scope_id=request.scope_id,
                    last_updated=datetime.utcnow(),
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="system_configuration_update",
                    value=1,
                    scope=request.scope,
                    setting_count=len(request.settings),
                )

                return UpdateSystemConfigurationResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    configuration=config_dto,
                )
            except Exception as e:
                self.tracer.record_metric(
                    name="system_configuration_update_errors",
                    value=1,
                    error_type=type(e).__name__,
                )
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                if isinstance(e, (ValidationError, AuthorizationError)):
                    return UpdateSystemConfigurationResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )
                raise ApplicationError(
                    message=f"Failed to update system configuration: {e}",
                    error_code="CONFIG_UPDATE_FAILED",
                ) from e
