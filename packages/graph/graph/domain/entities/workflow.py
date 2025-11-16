import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Set
from ..exceptions import ValidationError, VersioningException
from .enums import ScientificDomain

class WorkflowType(Enum):
    """Types of workflows that can be executed."""

    INGESTION = "ingestion"
    QUERY = "query"
    ANALYTICS = "analytics"
    EXPORT = "export"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"


class JobStatus(Enum):
    """Status of job execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
class GraphBackup:
    """Backup metadata for a knowledge graph."""
    id: str
    kg_id: str
    tenant_id: str
    location: str
    created_at: datetime

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(message="Backup ID must be a non-empty string", param="id")
        if not self.kg_id or not isinstance(self.kg_id, str):
            raise ValidationError(message="Knowledge graph ID must be a non-empty string", param="kg_id")
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(message="Tenant ID must be a non-empty string", param="tenant_id")
        if not self.location or not isinstance(self.location, str):
            raise ValidationError(message="Location must be a non-empty string", param="location")
        if not isinstance(self.created_at, datetime):
            raise ValidationError(message="Created at must be a datetime object", param="created_at")

    @classmethod
    def create(cls, *, kg_id: str, tenant_id: str, location: str) -> "GraphBackup":
        backup_id = str(uuid.uuid4())
        now = datetime.utcnow()
        return cls(id=backup_id, kg_id=kg_id, tenant_id=tenant_id, location=location, created_at=now)


@dataclass
class Workflow:
    """Workflow entity for managing long-running operations."""

    id: str
    name: str
    description: Optional[str]
    tenant_id: str
    definition: Dict[str, Any]  # Workflow definition (steps, parameters, etc.)
    workflow_type: WorkflowType
    version: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    def __post_init__(self):
        """Validate the workflow after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate the workflow entity.

        Raises:
            ValidationError: If any validation fails
        """
        # Validate id - must be non-empty string
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(
                message="Workflow ID must be a non-empty string", param="id"
            )

        # Validate name - must be non-empty string
        if not self.name or not isinstance(self.name, str):
            raise ValidationError(
                message="Workflow name must be a non-empty string", param="name"
            )

        # Validate tenant_id - must be non-empty string
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(
                message="Tenant ID must be a non-empty string", param="tenant_id"
            )

        # Validate definition - must be non-empty dict
        if not isinstance(self.definition, dict) or not self.definition:
            raise ValidationError(
                message="Workflow definition must be a non-empty dictionary",
                param="definition",
            )

        # Validate workflow_type - must be a valid WorkflowType
        if not isinstance(self.workflow_type, WorkflowType):
            raise ValidationError(
                message="Workflow type must be a valid WorkflowType",
                param="workflow_type",
            )

        # Validate version - must be non-empty string
        if not self.version or not isinstance(self.version, str):
            raise ValidationError(
                message="Version must be a non-empty string", param="version"
            )

        # Validate created_by - must be non-empty string
        if not self.created_by or not isinstance(self.created_by, str):
            raise ValidationError(
                message="Created by must be a non-empty string", param="created_by"
            )

        # Validate timestamps
        if not isinstance(self.created_at, datetime):
            raise ValidationError(
                message="Created at must be a datetime object", param="created_at"
            )

        if not isinstance(self.updated_at, datetime):
            raise ValidationError(
                message="Updated at must be a datetime object", param="updated_at"
            )

        # Validate is_active - must be boolean
        if not isinstance(self.is_active, bool):
            raise ValidationError(
                message="is_active must be a boolean value", param="is_active"
            )

        # Validate updated_at is not before created_at
        if self.updated_at < self.created_at:
            raise ValidationError(
                message="Updated at cannot be before created at", param="updated_at"
            )

    @classmethod
    def create(
        cls,
        name: str,
        tenant_id: str,
        definition: Dict[str, Any],
        workflow_type: WorkflowType,
        created_by: str,
        description: Optional[str] = None,
        version: str = "1.0.0",
    ) -> "Workflow":
        """Create a new workflow with auto-generated ID and timestamps.

        Args:
            name: Workflow name
            tenant_id: Tenant identifier for multi-tenant isolation
            definition: Workflow definition dictionary
            workflow_type: Type of workflow
            created_by: User ID who created the workflow
            description: Optional workflow description
            version: Workflow version (default: "1.0.0")

        Returns:
            A new Workflow instance

        Raises:
            ValidationError: If any parameter is invalid
        """
        now = datetime.utcnow()
        workflow_id = str(uuid.uuid4())

        return cls(
            id=workflow_id,
            name=name,
            description=description,
            tenant_id=tenant_id,
            definition=definition,
            workflow_type=workflow_type,
            version=version,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            is_active=True,
        )

    def deactivate(self) -> None:
        """Deactivate the workflow."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate the workflow."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def update_definition(self, definition: Dict[str, Any]) -> None:
        """Update the workflow definition.

        Args:
            definition: New workflow definition

        Raises:
            ValidationError: If definition is invalid
        """
        if not isinstance(definition, dict) or not definition:
            raise ValidationError(
                message="Workflow definition must be a non-empty dictionary",
                param="definition",
            )

        self.definition = definition
        self.updated_at = datetime.utcnow()


@dataclass
class Job:
    """Job entity for tracking workflow execution."""

    id: str
    workflow_id: str
    tenant_id: str
    status: JobStatus
    input_parameters: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    progress_percentage: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_by: str
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        """Validate the job after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate the job entity.

        Raises:
            ValidationError: If any validation fails
        """
        # Validate id - must be non-empty string
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(
                message="Job ID must be a non-empty string", param="id"
            )

        # Validate workflow_id - must be non-empty string
        if not self.workflow_id or not isinstance(self.workflow_id, str):
            raise ValidationError(
                message="Workflow ID must be a non-empty string", param="workflow_id"
            )

        # Validate tenant_id - must be non-empty string
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(
                message="Tenant ID must be a non-empty string", param="tenant_id"
            )

        # Validate status - must be a valid JobStatus
        if not isinstance(self.status, JobStatus):
            raise ValidationError(
                message="Status must be a valid JobStatus", param="status"
            )

        # Validate input_parameters - must be dict
        if not isinstance(self.input_parameters, dict):
            raise ValidationError(
                message="Input parameters must be a dictionary",
                param="input_parameters",
            )

        # Validate output_data - must be dict or None
        if self.output_data is not None and not isinstance(self.output_data, dict):
            raise ValidationError(
                message="Output data must be a dictionary or None", param="output_data"
            )

        # Validate error_message - must be string or None
        if self.error_message is not None and not isinstance(self.error_message, str):
            raise ValidationError(
                message="Error message must be a string or None", param="error_message"
            )

        # Validate progress_percentage - must be between 0 and 100
        if not isinstance(self.progress_percentage, (int, float)) or not (
            0 <= self.progress_percentage <= 100
        ):
            raise ValidationError(
                message="Progress percentage must be a number between 0 and 100",
                param="progress_percentage",
            )

        # Validate created_by - must be non-empty string
        if not self.created_by or not isinstance(self.created_by, str):
            raise ValidationError(
                message="Created by must be a non-empty string", param="created_by"
            )

        # Validate timestamps
        if not isinstance(self.created_at, datetime):
            raise ValidationError(
                message="Created at must be a datetime object", param="created_at"
            )

        if not isinstance(self.updated_at, datetime):
            raise ValidationError(
                message="Updated at must be a datetime object", param="updated_at"
            )

        if self.started_at is not None and not isinstance(self.started_at, datetime):
            raise ValidationError(
                message="Started at must be a datetime object or None",
                param="started_at",
            )

        if self.completed_at is not None and not isinstance(
            self.completed_at, datetime
        ):
            raise ValidationError(
                message="Completed at must be a datetime object or None",
                param="completed_at",
            )

        # Validate retry counts - must be non-negative integers
        if not isinstance(self.retry_count, int) or self.retry_count < 0:
            raise ValidationError(
                message="Retry count must be a non-negative integer",
                param="retry_count",
            )

        if not isinstance(self.max_retries, int) or self.max_retries < 0:
            raise ValidationError(
                message="Max retries must be a non-negative integer",
                param="max_retries",
            )

        # Validate updated_at is not before created_at
        if self.updated_at < self.created_at:
            raise ValidationError(
                message="Updated at cannot be before created at", param="updated_at"
            )

        # Validate completed_at is not before started_at if both exist
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValidationError(
                message="Completed at cannot be before started at", param="completed_at"
            )

    @classmethod
    def create(
        cls,
        workflow_id: str,
        tenant_id: str,
        input_parameters: Dict[str, Any],
        created_by: str,
        max_retries: int = 3,
    ) -> "Job":
        """Create a new job with auto-generated ID and timestamps.

        Args:
            workflow_id: Workflow identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            input_parameters: Input parameters for job execution
            created_by: User ID who created the job
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            A new Job instance

        Raises:
            ValidationError: If any parameter is invalid
        """
        now = datetime.utcnow()
        job_id = str(uuid.uuid4())

        return cls(
            id=job_id,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            status=JobStatus.PENDING,
            input_parameters=input_parameters,
            output_data=None,
            error_message=None,
            progress_percentage=0.0,
            started_at=None,
            completed_at=None,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            retry_count=0,
            max_retries=max_retries,
        )

    def start(self) -> None:
        """Mark the job as started."""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def complete(self, output_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark the job as completed.

        Args:
            output_data: Optional output data from job execution
        """
        self.status = JobStatus.COMPLETED
        self.progress_percentage = 100.0
        self.output_data = output_data
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def fail(self, error_message: str) -> None:
        """Mark the job as failed.

        Args:
            error_message: Error message describing the failure
        """
        self.status = JobStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def cancel(self) -> None:
        """Cancel the job."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def retry(self) -> bool:
        """Attempt to retry the job.

        Returns:
            True if retry is allowed, False if max retries exceeded
        """
        if self.retry_count >= self.max_retries:
            return False

        self.retry_count += 1
        self.status = JobStatus.RETRYING
        self.error_message = None
        self.started_at = None
        self.completed_at = None
        self.progress_percentage = 0.0
        self.updated_at = datetime.utcnow()
        return True

    def update_progress(self, percentage: float, message: Optional[str] = None) -> None:
        """Update job progress.

        Args:
            percentage: Progress percentage (0-100)
            message: Optional progress message

        Raises:
            ValidationError: If percentage is invalid
        """
        if not isinstance(percentage, (int, float)) or not (0 <= percentage <= 100):
            raise ValidationError(
                message="Progress percentage must be a number between 0 and 100",
                param="percentage",
            )

        self.progress_percentage = percentage
        if message:
            # Store progress message in output_data if it exists, otherwise create it
            if self.output_data is None:
                self.output_data = {}
            self.output_data["progress_message"] = message

        self.updated_at = datetime.utcnow()

    def can_retry(self) -> bool:
        """Check if the job can be retried.

        Returns:
            True if job can be retried, False otherwise
        """
        return self.status == JobStatus.FAILED and self.retry_count < self.max_retries

    def is_terminal(self) -> bool:
        """Check if the job is in a terminal state.

        Returns:
            True if job is in a terminal state, False otherwise
        """
        return self.status in [
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        ]


class WebhookStatus(Enum):
    """Status of a webhook subscription."""

    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class Webhook:
    """Webhook entity for outbound event notifications."""

    id: str
    tenant_id: str
    url: str
    events: List[str]
    secret: str
    status: WebhookStatus
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(
                message="Webhook ID must be a non-empty string", param="id"
            )

        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(
                message="Tenant ID must be a non-empty string", param="tenant_id"
            )

        if not self.url or not isinstance(self.url, str):
            raise ValidationError(
                message="Webhook URL must be a non-empty string", param="url"
            )

        if not isinstance(self.events, list) or not all(
            isinstance(e, str) and e for e in self.events
        ):
            raise ValidationError(
                message="Webhook events must be a non-empty list of strings",
                param="events",
            )

        if not self.secret or not isinstance(self.secret, str):
            raise ValidationError(
                message="Webhook secret must be a non-empty string", param="secret"
            )

        if not isinstance(self.status, WebhookStatus):
            raise ValidationError(
                message="Status must be a valid WebhookStatus", param="status"
            )

        if not isinstance(self.created_at, datetime) or not isinstance(
            self.updated_at, datetime
        ):
            raise ValidationError(
                message="Timestamps must be datetime objects", param="timestamps"
            )

        if self.updated_at < self.created_at:
            raise ValidationError(
                message="updated_at cannot be before created_at", param="updated_at"
            )

    @classmethod
    def create(
        cls, *, tenant_id: str, url: str, events: List[str], secret: str
    ) -> "Webhook":
        now = datetime.utcnow()
        return cls(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            url=url,
            events=events,
            secret=secret,
            status=WebhookStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )


@dataclass
class SharingLink:
    """Link entity for sharing knowledge graphs."""

    id: str
    kg_id: str
    tenant_id: str
    token: str
    permissions: List[str]
    expires_at: Optional[datetime]
    created_by: str
    created_at: datetime
    updated_at: datetime
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None
    is_active: bool = True
    share_type: str = "specific_users"  # "public", "organization", "specific_users"
    shared_with_user_ids: Optional[List[str]] = None
    share_url: str = ""
    access_token: str = ""

    def __post_init__(self) -> None:
        """Validate the sharing link after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate the sharing link entity."""
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(message="Sharing link ID must be a non-empty string", param="id")
        if not self.kg_id or not isinstance(self.kg_id, str):
            raise ValidationError(message="Knowledge graph ID must be a non-empty string", param="kg_id")
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(message="Tenant ID must be a non-empty string", param="tenant_id")
        if not self.token or not isinstance(self.token, str):
            raise ValidationError(message="Token must be a non-empty string", param="token")
        if not isinstance(self.permissions, list) or not self.permissions:
            raise ValidationError(message="Permissions must be a non-empty list", param="permissions")
        if self.expires_at is not None and not isinstance(self.expires_at, datetime):
            raise ValidationError(message="expires_at must be a datetime or None", param="expires_at")
        if not self.created_by or not isinstance(self.created_by, str):
            raise ValidationError(message="created_by must be a non-empty string", param="created_by")
        if not isinstance(self.created_at, datetime):
            raise ValidationError(message="created_at must be a datetime", param="created_at")
        if not isinstance(self.updated_at, datetime):
            raise ValidationError(message="updated_at must be a datetime", param="updated_at")
        if not isinstance(self.access_count, int) or self.access_count < 0:
            raise ValidationError(message="access_count must be a non-negative integer", param="access_count")
        if not isinstance(self.is_active, bool):
            raise ValidationError(message="is_active must be a boolean", param="is_active")
        if self.share_type not in ["public", "organization", "specific_users"]:
            raise ValidationError(message="share_type must be one of: public, organization, specific_users", param="share_type")
        if self.shared_with_user_ids is not None and not isinstance(self.shared_with_user_ids, list):
            raise ValidationError(message="shared_with_user_ids must be a list or None", param="shared_with_user_ids")
        if not isinstance(self.share_url, str):
            raise ValidationError(message="share_url must be a string", param="share_url")
        if not isinstance(self.access_token, str):
            raise ValidationError(message="access_token must be a string", param="access_token")

    @classmethod
    def create(
        cls,
        kg_id: str,
        tenant_id: str,
        token: str,
        permissions: List[str],
        created_by: str,
        expires_at: Optional[datetime] = None,
        share_type: str = "specific_users",
        shared_with_user_ids: Optional[List[str]] = None,
        share_url: str = "",
        access_token: str = "",
    ) -> "SharingLink":
        """Create a new sharing link with auto-generated ID."""
        now = datetime.utcnow()
        link_id = str(uuid.uuid4())
        return cls(
            id=link_id,
            kg_id=kg_id,
            tenant_id=tenant_id,
            token=token,
            permissions=permissions,
            expires_at=expires_at,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            access_count=0,
            last_accessed_at=None,
            is_active=True,
            share_type=share_type,
            shared_with_user_ids=shared_with_user_ids,
            share_url=share_url,
            access_token=access_token,
        )

    def record_access(self) -> None:
        """Record an access to this sharing link."""
        self.access_count += 1
        self.last_accessed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the sharing link."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def is_expired(self) -> bool:
        """Check if the sharing link has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class AgentType(Enum):
    """Types of AI agents in the multi-agent system."""

    LITERATURE_REVIEW = "literature_review"
    DATA_EXTRACTION = "data_extraction"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    CITATION_ANALYSIS = "citation_analysis"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    REASONING = "reasoning"
    ORCHESTRATOR = "orchestrator"
    EXPLANATION = "explanation"


class AgentStatus(Enum):
    """Status of an agent."""

    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class CoordinationStrategy(Enum):
    """Coordination strategies for multi-agent systems."""

    HIERARCHICAL = "hierarchical"
    COMPETITIVE = "competitive"
    COLLABORATIVE = "collaborative"
    PIPELINE = "pipeline"


@dataclass
class Agent:
    """AI Agent entity for multi-agent GraphRAG orchestration."""

    id: str
    name: str
    agent_type: AgentType
    tenant_id: str
    status: AgentStatus
    capabilities: List[str]
    specialization_domain: ScientificDomain
    current_task_id: Optional[str]
    performance_metrics: Dict[str, float]
    created_at: datetime
    updated_at: datetime
    last_active_at: Optional[datetime]
    configuration: Dict[str, Any]
    is_active: bool = True

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate the agent entity."""
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(message="Agent ID must be a non-empty string", param="id")
        if not self.name or not isinstance(self.name, str):
            raise ValidationError(message="Agent name must be a non-empty string", param="name")
        if not isinstance(self.agent_type, AgentType):
            raise ValidationError(message="Agent type must be a valid AgentType", param="agent_type")
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(message="Tenant ID must be a non-empty string", param="tenant_id")
        if not isinstance(self.status, AgentStatus):
            raise ValidationError(message="Status must be a valid AgentStatus", param="status")
        if not isinstance(self.capabilities, list):
            raise ValidationError(message="Capabilities must be a list", param="capabilities")
        if not isinstance(self.specialization_domain, ScientificDomain):
            raise ValidationError(message="Specialization domain must be a valid ScientificDomain", param="specialization_domain")
        if not isinstance(self.performance_metrics, dict):
            raise ValidationError(message="Performance metrics must be a dictionary", param="performance_metrics")
        if not isinstance(self.configuration, dict):
            raise ValidationError(message="Configuration must be a dictionary", param="configuration")
        if not isinstance(self.created_at, datetime):
            raise ValidationError(message="created_at must be a datetime", param="created_at")
        if not isinstance(self.updated_at, datetime):
            raise ValidationError(message="updated_at must be a datetime", param="updated_at")
        if not isinstance(self.is_active, bool):
            raise ValidationError(message="is_active must be a boolean", param="is_active")

    @classmethod
    def create(
        cls,
        name: str,
        agent_type: AgentType,
        tenant_id: str,
        specialization_domain: ScientificDomain,
        capabilities: List[str],
        configuration: Optional[Dict[str, Any]] = None,
    ) -> "Agent":
        """Create a new agent with auto-generated ID and timestamps."""
        now = datetime.utcnow()
        agent_id = str(uuid.uuid4())

        return cls(
            id=agent_id,
            name=name,
            agent_type=agent_type,
            tenant_id=tenant_id,
            status=AgentStatus.IDLE,
            capabilities=capabilities,
            specialization_domain=specialization_domain,
            current_task_id=None,
            performance_metrics={},
            created_at=now,
            updated_at=now,
            last_active_at=None,
            configuration=configuration or {},
            is_active=True,
        )

    def assign_task(self, task_id: str) -> None:
        """Assign a task to the agent."""
        self.current_task_id = task_id
        self.status = AgentStatus.BUSY
        self.last_active_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def complete_task(self) -> None:
        """Mark the current task as completed."""
        self.current_task_id = None
        self.status = AgentStatus.IDLE
        self.updated_at = datetime.utcnow()

    def update_performance_metrics(self, metrics: Dict[str, float]) -> None:
        """Update agent performance metrics."""
        self.performance_metrics.update(metrics)
        self.updated_at = datetime.utcnow()


@dataclass
class CoordinationSession:
    """Multi-agent coordination session."""

    id: str
    tenant_id: str
    kg_id: str
    strategy: CoordinationStrategy
    participating_agents: List[str]  # Agent IDs
    orchestrator_agent_id: str
    session_goal: str
    status: str  # active, completed, failed, cancelled
    started_at: datetime
    completed_at: Optional[datetime]
    created_by: str
    results: Optional[Dict[str, Any]]
    performance_summary: Optional[Dict[str, float]]

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate the coordination session entity."""
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(message="Session ID must be a non-empty string", param="id")
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(message="Tenant ID must be a non-empty string", param="tenant_id")
        if not self.kg_id or not isinstance(self.kg_id, str):
            raise ValidationError(message="Knowledge graph ID must be a non-empty string", param="kg_id")
        if not isinstance(self.strategy, CoordinationStrategy):
            raise ValidationError(message="Strategy must be a valid CoordinationStrategy", param="strategy")
        if not isinstance(self.participating_agents, list) or not self.participating_agents:
            raise ValidationError(message="Participating agents must be a non-empty list", param="participating_agents")
        if not self.session_goal or not isinstance(self.session_goal, str):
            raise ValidationError(message="Session goal must be a non-empty string", param="session_goal")

    @classmethod
    def create(
        cls,
        tenant_id: str,
        kg_id: str,
        strategy: CoordinationStrategy,
        participating_agents: List[str],
        orchestrator_agent_id: str,
        session_goal: str,
        created_by: str,
    ) -> "CoordinationSession":
        """Create a new coordination session."""
        now = datetime.utcnow()
        session_id = str(uuid.uuid4())

        return cls(
            id=session_id,
            tenant_id=tenant_id,
            kg_id=kg_id,
            strategy=strategy,
            participating_agents=participating_agents,
            orchestrator_agent_id=orchestrator_agent_id,
            session_goal=session_goal,
            status="active",
            started_at=now,
            completed_at=None,
            created_by=created_by,
            results=None,
            performance_summary=None,
        )

