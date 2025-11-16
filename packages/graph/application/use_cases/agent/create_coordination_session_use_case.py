"""Use case for creating multi-agent coordination sessions."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from application.exceptions import AuthorizationError, NotFoundError, ValidationError
from application.ports import (
    AgentCoordinationPort,
    AgentRepositoryPort,
    AuditLoggingPort,
    AuthorizationPort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO
from domain.entities import CoordinationStrategy

logger = logging.getLogger(__name__)


@dataclass
class CreateCoordinationSessionRequestDTO:
    """Request DTO for creating coordination session."""

    tenant_id: str
    user_id: str
    kg_id: str
    strategy: str  # Will be converted to CoordinationStrategy
    participating_agent_ids: List[str]
    session_goal: str
    session_parameters: Dict[str, Any]


@dataclass
class CoordinationSessionDTO:
    """DTO for coordination session response."""

    id: str
    strategy: str
    participating_agents_count: int
    session_goal: str
    status: str
    started_at: str  # ISO format datetime


@dataclass
class CreateCoordinationSessionResponseDTO(BaseResponseDTO):
    """Response DTO for creating coordination session."""

    session: Optional[CoordinationSessionDTO] = None


class CreateCoordinationSessionUseCase(
    BaseUseCase[
        CreateCoordinationSessionRequestDTO, CreateCoordinationSessionResponseDTO
    ]
):
    """Use case for creating agent coordination sessions."""

    def __init__(
        self,
        coordination_port: AgentCoordinationPort,
        agent_repository_port: AgentRepositoryPort,
        authorization_port: AuthorizationPort,
        audit_logging_port: AuditLoggingPort,
    ):
        """Initialize the coordination session creation use case."""
        super().__init__()
        self.coordination = coordination_port
        self.agent_repo = agent_repository_port
        self.authz = authorization_port
        self.audit = audit_logging_port

    async def _execute_internal(
        self, request: CreateCoordinationSessionRequestDTO
    ) -> CreateCoordinationSessionResponseDTO:
        """Execute coordination session creation operation."""
        logger.info(
            f"Creating coordination session for kg_id={request.kg_id}, strategy={request.strategy}"
        )

        # Check authorization
        if not await self.authz.check_permission(
            request.user_id, request.kg_id, "write"
        ):
            raise AuthorizationError(
                message=f"User {request.user_id} lacks write permission for knowledge graph {request.kg_id}",
                user_id=request.user_id,
                resource_type="knowledge_graph",
                resource_id=request.kg_id,
                required_permission="write",
            )

        # Validate coordination strategy
        try:
            strategy = CoordinationStrategy(request.strategy.lower())
        except ValueError:
            raise ValidationError(
                message=f"Invalid coordination strategy: {request.strategy}",
                param="strategy",
            )

        # Validate participating agents exist and are active
        for agent_id in request.participating_agent_ids:
            agent = await self.agent_repo.get_agent_by_id(agent_id, request.tenant_id)
            if not agent:
                raise NotFoundError(
                    message=f"Agent {agent_id} not found",
                    resource_type="agent",
                    resource_id=agent_id,
                )
            if not agent.is_active:
                raise ValidationError(
                    message=f"Agent {agent_id} is not active",
                    param="participating_agent_ids",
                )

        # Select orchestrator agent (first agent for now, could be more sophisticated)
        request.participating_agent_ids[0]

        try:
            # Create coordination session
            session = await self.coordination.create_coordination_session(
                tenant_id=request.tenant_id,
                kg_id=request.kg_id,
                strategy=strategy,
                participating_agents=request.participating_agent_ids,
                session_goal=request.session_goal,
                created_by=request.user_id,
            )

            # Log the action
            await self.audit.log_action(
                tenant_id=request.tenant_id,
                action="create_coordination_session",
                resource_type="coordination_session",
                resource_id=session.id,
                details={
                    "strategy": request.strategy,
                    "participating_agents": request.participating_agent_ids,
                    "session_goal": request.session_goal,
                    "kg_id": request.kg_id,
                },
                user_id=request.user_id,
            )

            # Convert to DTO
            session_dto = CoordinationSessionDTO(
                id=session.id,
                strategy=session.strategy.value,
                participating_agents_count=len(session.participating_agents),
                session_goal=session.session_goal,
                status=session.status,
                started_at=session.started_at.isoformat(),
            )

            return CreateCoordinationSessionResponseDTO(
                success=True,
                session=session_dto,
            )

        except Exception as e:
            logger.error(f"Failed to create coordination session: {str(e)}")
            raise ValidationError(
                f"Coordination session creation failed: {str(e)}"
            ) from e
