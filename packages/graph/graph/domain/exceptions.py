"""Domain exceptions for GraphRAG Ontology Application.

This module defines typed exceptions for the application, providing
structured error handling and consistent error reporting across the system.
"""

from typing import Any, Dict, Optional


class GraphRAGException(Exception):
    """Base exception for GraphRAG application errors."""

    def __init__(
        self, message: str, error_code: str, context: Optional[Dict[str, Any]] = None
    ):
        """Initialize GraphRAGException.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            context: Optional context information for debugging
        """
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(message)


class LLMException(GraphRAGException):
    """Base exception for LLM-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        model: str,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize LLMException.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            model: LLM model identifier
            tenant_id: Tenant identifier
            context: Optional context information for debugging
        """
        self.model = model
        self.tenant_id = tenant_id
        super().__init__(
            message=message,
            error_code=error_code,
            context={"model": model, "tenant_id": tenant_id, **(context or {})},
        )


class QuotaExceededException(LLMException):
    """Exception raised when LLM API quota is exceeded."""

    def __init__(
        self,
        model: str,
        tenant_id: str,
        quota_type: str = "tokens",  # "tokens", "requests", "cost"
        reset_time: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize QuotaExceededException.

        Args:
            model: LLM model identifier
            tenant_id: Tenant identifier
            quota_type: Type of quota exceeded
            reset_time: Optional time when quota will reset
            context: Optional context information for debugging
        """
        self.quota_type = quota_type
        self.reset_time = reset_time

        message = f"API quota exceeded for model {model} ({quota_type})"
        if reset_time:
            message += f", resets at {reset_time}"

        super().__init__(
            message=message,
            error_code="QUOTA_EXCEEDED",
            model=model,
            tenant_id=tenant_id,
            context={
                "quota_type": quota_type,
                "reset_time": reset_time,
                **(context or {}),
            },
        )


class RateLimitedException(LLMException):
    """Exception raised when LLM API rate limit is exceeded."""

    def __init__(
        self,
        model: str,
        tenant_id: str,
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize RateLimitedException.

        Args:
            model: LLM model identifier
            tenant_id: Tenant identifier
            retry_after: Optional seconds to wait before retry
            context: Optional context information for debugging
        """
        self.retry_after = retry_after

        message = f"API rate limit exceeded for model {model}"
        if retry_after:
            message += f", retry after {retry_after} seconds"

        super().__init__(
            message=message,
            error_code="RATE_LIMITED",
            model=model,
            tenant_id=tenant_id,
            context={"retry_after": retry_after, **(context or {})},
        )


class InvalidRequestException(LLMException):
    """Exception raised when LLM request is invalid."""

    def __init__(
        self,
        model: str,
        tenant_id: str,
        param: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize InvalidRequestException.

        Args:
            model: LLM model identifier
            tenant_id: Tenant identifier
            param: Optional parameter that caused the error
            context: Optional context information for debugging
        """
        self.param = param

        message = f"Invalid request for model {model}"
        if param:
            message += f", invalid parameter: {param}"

        super().__init__(
            message=message,
            error_code="INVALID_REQUEST",
            model=model,
            tenant_id=tenant_id,
            context={"param": param, **(context or {})},
        )


class AuthenticationException(LLMException):
    """Exception raised when LLM API authentication fails."""

    def __init__(
        self, model: str, tenant_id: str, context: Optional[Dict[str, Any]] = None
    ):
        """Initialize AuthenticationException.

        Args:
            model: LLM model identifier
            tenant_id: Tenant identifier
            context: Optional context information for debugging
        """
        super().__init__(
            message=f"Authentication failed for model {model}",
            error_code="AUTHENTICATION_ERROR",
            model=model,
            tenant_id=tenant_id,
            context=context,
        )


class ServiceUnavailableException(LLMException):
    """Exception raised when LLM service is unavailable."""

    def __init__(
        self,
        model: str,
        tenant_id: str,
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize ServiceUnavailableException.

        Args:
            model: LLM model identifier
            tenant_id: Tenant identifier
            retry_after: Optional seconds to wait before retry
            context: Optional context information for debugging
        """
        self.retry_after = retry_after

        message = f"Service unavailable for model {model}"
        if retry_after:
            message += f", retry after {retry_after} seconds"

        super().__init__(
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            model=model,
            tenant_id=tenant_id,
            context={"retry_after": retry_after, **(context or {})},
        )


class ContentFilteredException(LLMException):
    """Exception raised when content is filtered by safety systems."""

    def __init__(
        self,
        model: str,
        tenant_id: str,
        categories: Optional[Dict[str, float]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize ContentFilteredException.

        Args:
            model: LLM model identifier
            tenant_id: Tenant identifier
            categories: Optional dictionary of filtered categories and scores
            context: Optional context information for debugging
        """
        self.categories = categories or {}

        message = f"Content filtered by safety systems for model {model}"
        if categories:
            categories_str = ", ".join(f"{k}: {v}" for k, v in categories.items())
            message += f" ({categories_str})"

        super().__init__(
            message=message,
            error_code="CONTENT_FILTERED",
            model=model,
            tenant_id=tenant_id,
            context={"categories": categories, **(context or {})},
        )


class ValidationError(GraphRAGException):
    """Exception raised when validation fails."""

    def __init__(
        self,
        message: str,
        param: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize ValidationError.

        Args:
            message: Human-readable error message
            param: Optional parameter that failed validation
            context: Optional context information for debugging
        """
        self.param = param

        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            context={"param": param, **(context or {})},
        )


class OntologyException(GraphRAGException):
    """Exception raised for ontology-related errors."""

    def __init__(
        self,
        message: str,
        ontology_version_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize OntologyException.

        Args:
            message: Human-readable error message
            ontology_version_id: Optional ontology version identifier
            context: Optional context information for debugging
        """
        self.ontology_version_id = ontology_version_id

        super().__init__(
            message=message,
            error_code="ONTOLOGY_ERROR",
            context={"ontology_version_id": ontology_version_id, **(context or {})},
        )


class VersioningException(GraphRAGException):
    """Exception raised for versioning-related errors."""

    def __init__(
        self,
        message: str,
        version_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize VersioningException.

        Args:
            message: Human-readable error message
            version_id: Optional version identifier
            context: Optional context information for debugging
        """
        self.version_id = version_id

        super().__init__(
            message=message,
            error_code="VERSIONING_ERROR",
            context={"version_id": version_id, **(context or {})},
        )


class TranslationError(GraphRAGException):
    """Exception raised when query translation fails."""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize TranslationError.

        Args:
            message: Human-readable error message
            query: Optional query that failed translation
            context: Optional context information for debugging
        """
        self.query = query

        super().__init__(
            message=message,
            error_code="TRANSLATION_ERROR",
            context={"query": query, **(context or {})},
        )


class StreamingError(GraphRAGException):
    """Exception raised when streaming operations fail."""

    def __init__(
        self,
        message: str,
        event_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize StreamingError.

        Args:
            message: Human-readable error message
            event_type: Optional event type that failed
            context: Optional context information for debugging
        """
        self.event_type = event_type

        super().__init__(
            message=message,
            error_code="STREAMING_ERROR",
            context={"event_type": event_type, **(context or {})},
        )


class BufferOverflowError(StreamingError):
    """Exception raised when streaming buffer overflows."""

    def __init__(
        self,
        buffer_size: int,
        event_count: int,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize BufferOverflowError.

        Args:
            buffer_size: Maximum buffer size
            event_count: Actual event count
            context: Optional context information for debugging
        """
        self.buffer_size = buffer_size
        self.event_count = event_count

        super().__init__(
            message=f"Buffer overflow: {event_count} events exceed buffer size {buffer_size}",
            event_type="buffer_overflow",
            context={
                "buffer_size": buffer_size,
                "event_count": event_count,
                **(context or {}),
            },
        )


class PublishError(GraphRAGException):
    """Exception raised when message publishing fails."""

    def __init__(
        self,
        message: str,
        topic: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize PublishError.

        Args:
            message: Human-readable error message
            topic: Optional topic that failed publishing
            context: Optional context information for debugging
        """
        self.topic = topic

        super().__init__(
            message=message,
            error_code="PUBLISH_ERROR",
            context={"topic": topic, **(context or {})},
        )


class SubscriptionError(GraphRAGException):
    """Exception raised when message subscription fails."""

    def __init__(
        self,
        message: str,
        topic: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize SubscriptionError.

        Args:
            message: Human-readable error message
            topic: Optional topic that failed subscription
            context: Optional context information for debugging
        """
        self.topic = topic

        super().__init__(
            message=message,
            error_code="SUBSCRIPTION_ERROR",
            context={"topic": topic, **(context or {})},
        )


class TracingError(GraphRAGException):
    """Exception raised when tracing operations fail."""

    def __init__(
        self,
        message: str,
        span_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize TracingError.

        Args:
            message: Human-readable error message
            span_name: Optional span name that failed
            context: Optional context information for debugging
        """
        self.span_name = span_name

        super().__init__(
            message=message,
            error_code="TRACING_ERROR",
            context={"span_name": span_name, **(context or {})},
        )


class MetricsError(GraphRAGException):
    """Exception raised when metrics recording fails."""

    def __init__(
        self,
        message: str,
        metric_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize MetricsError.

        Args:
            message: Human-readable error message
            metric_name: Optional metric name that failed
            context: Optional context information for debugging
        """
        self.metric_name = metric_name

        super().__init__(
            message=message,
            error_code="METRICS_ERROR",
            context={"metric_name": metric_name, **(context or {})},
        )


class ClusteringError(GraphRAGException):
    """Exception raised when clustering operations fail."""

    def __init__(
        self,
        message: str,
        algorithm: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize ClusteringError.

        Args:
            message: Human-readable error message
            algorithm: Optional clustering algorithm that failed
            context: Optional context information for debugging
        """
        self.algorithm = algorithm

        super().__init__(
            message=message,
            error_code="CLUSTERING_ERROR",
            context={"algorithm": algorithm, **(context or {})},
        )


class BudgetExceededException(GraphRAGException):
    """Exception raised when token budget is exceeded."""

    def __init__(
        self,
        tenant_id: str,
        budget_usd: float,
        current_usage_usd: float,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize BudgetExceededException.

        Args:
            tenant_id: Tenant identifier
            budget_usd: Budget limit in USD
            current_usage_usd: Current usage in USD
            context: Optional context information for debugging
        """
        self.tenant_id = tenant_id
        self.budget_usd = budget_usd
        self.current_usage_usd = current_usage_usd

        message = (
            f"Token budget exceeded for tenant {tenant_id}: "
            f"${current_usage_usd:.2f} of ${budget_usd:.2f} budget"
        )

        super().__init__(
            message=message,
            error_code="BUDGET_EXCEEDED",
            context={
                "tenant_id": tenant_id,
                "budget_usd": budget_usd,
                "current_usage_usd": current_usage_usd,
                **(context or {}),
            },
        )


class AnalyticsError(GraphRAGException):
    """Exception raised when analytics operations fail."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize AnalyticsError.

        Args:
            message: Human-readable error message
            operation: Optional analytics operation that failed
            context: Optional context information for debugging
        """
        self.operation = operation

        super().__init__(
            message=message,
            error_code="ANALYTICS_ERROR",
            context={"operation": operation, **(context or {})},
        )


class VisualizationError(GraphRAGException):
    """Exception raised when visualization operations fail."""

    def __init__(
        self,
        message: str,
        visualization_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize VisualizationError.

        Args:
            message: Human-readable error message
            visualization_type: Optional visualization type that failed
            context: Optional context information for debugging
        """
        self.visualization_type = visualization_type

        super().__init__(
            message=message,
            error_code="VISUALIZATION_ERROR",
            context={"visualization_type": visualization_type, **(context or {})},
        )


class ExportError(GraphRAGException):
    """Exception raised when export operations fail."""

    def __init__(
        self,
        message: str,
        export_format: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize ExportError.

        Args:
            message: Human-readable error message
            export_format: Optional export format that failed
            context: Optional context information for debugging
        """
        self.export_format = export_format

        super().__init__(
            message=message,
            error_code="EXPORT_ERROR",
            context={"export_format": export_format, **(context or {})},
        )


class ConversionError(GraphRAGException):
    """Exception raised when data conversion operations fail."""

    def __init__(
        self,
        message: str,
        source_format: Optional[str] = None,
        target_format: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize ConversionError.

        Args:
            message: Human-readable error message
            source_format: Optional source format
            target_format: Optional target format
            context: Optional context information for debugging
        """
        self.source_format = source_format
        self.target_format = target_format

        super().__init__(
            message=message,
            error_code="CONVERSION_ERROR",
            context={
                "source_format": source_format,
                "target_format": target_format,
                **(context or {}),
            },
        )


class AuthorizationError(GraphRAGException):
    """Exception raised when authorization fails."""

    def __init__(
        self,
        message: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize AuthorizationError.

        Args:
            message: Human-readable error message
            user_id: Optional user identifier
            resource_type: Optional resource type
            action: Optional action attempted
            context: Optional context information for debugging
        """
        self.user_id = user_id
        self.resource_type = resource_type
        self.action = action

        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            context={
                "user_id": user_id,
                "resource_type": resource_type,
                "action": action,
                **(context or {}),
            },
        )


class QueryProcessingError(GraphRAGException):
    """Exception raised when query processing fails."""

    def __init__(
        self,
        message: str,
        *,
        kg_id: str,
        tenant_id: str,
        query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize QueryProcessingError.

        Args:
            message: Human-readable error message
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            query: Natural language query that triggered the error
            context: Optional extra debugging information
        """
        self.kg_id = kg_id
        self.tenant_id = tenant_id
        self.query = query

        super().__init__(
            message=message,
            error_code="QUERY_PROCESSING_ERROR",
            context={
                "kg_id": kg_id,
                "tenant_id": tenant_id,
                "query": query,
                **(context or {}),
            },
        )


class NotFoundError(GraphRAGException):
    """Exception raised when a requested resource is not found."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize NotFoundError.

        Args:
            message: Human-readable error message
            resource_type: Optional resource type that was not found
            resource_id: Optional resource identifier that was not found
            context: Optional context information for debugging
        """
        self.resource_type = resource_type
        self.resource_id = resource_id

        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            context={
                "resource_type": resource_type,
                "resource_id": resource_id,
                **(context or {}),
            },
        )
