"""Application layer use cases organized by domain.

Import use cases using their domain package to keep concerns modular::

    from application.use_cases.<domain>.<module> import <UseCaseClass>

The thin modules at this level exist for backwards compatibility only.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Explicit export list populated conditionally
__all__: list[str] = []

# Knowledge graph domain

# Ontology domain

# User & organization domain

# Search domain
try:  # Optional search features may have unmet dependencies
    from .search import *  # noqa: F401,F403
    from .search import __all__ as _search_all

    __all__ += _search_all
except Exception as exc:  # pragma: no cover - import guards
    logger.warning("Search use cases unavailable: %s", exc)

# Analytics domain

# Subscription domain

# Visualization domain
# Data retention domain

# Indexing domain

# Multimodal domain
try:  # Optional multimodal features may have unmet dependencies
    from .multimodal.cross_modal_retrieval_use_case import (
        CrossModalRetrievalUseCase,
        CrossModalRetrievalRequestDTO,
        CrossModalResultDTO,
        CrossModalRetrievalResponseDTO,
    )
    from .multimodal.index_multimedia_use_case import (
        IndexMultimediaUseCase,
        IndexMultimediaRequestDTO,
        IndexMultimediaResponseDTO,
    )
    from .multimodal.process_multimodal_content_use_case import (
        MultimodalEntityDTO,
        ProcessMultimodalContentRequestDTO,
        ProcessMultimodalContentResponseDTO,
        ProcessMultimodalContentUseCase,
    )

    __all__ += [
        "CrossModalRetrievalUseCase",
        "CrossModalRetrievalRequestDTO",
        "CrossModalResultDTO",
        "CrossModalRetrievalResponseDTO",
        "IndexMultimediaUseCase",
        "IndexMultimediaRequestDTO",
        "IndexMultimediaResponseDTO",
        "ProcessMultimodalContentUseCase",
        "ProcessMultimodalContentRequestDTO",
        "ProcessMultimodalContentResponseDTO",
        "MultimodalEntityDTO",
    ]
except Exception as exc:  # pragma: no cover - import guards
    logger.warning("Multimodal use cases unavailable: %s", exc)

# Agent coordination domain
try:  # Optional agent features may have unmet dependencies
    from .agent.create_coordination_session_use_case import (
        CoordinationSessionDTO,
        CreateCoordinationSessionRequestDTO,
        CreateCoordinationSessionResponseDTO,
        CreateCoordinationSessionUseCase,
    )

    __all__ += [
        "CreateCoordinationSessionUseCase",
        "CreateCoordinationSessionRequestDTO",
        "CreateCoordinationSessionResponseDTO",
        "CoordinationSessionDTO",
    ]
except Exception as exc:  # pragma: no cover - import guards
    logger.warning("Agent coordination use cases unavailable: %s", exc)

# Security domain - commented out until security module is implemented
# from .security.create_api_key_use_case import CreateAPIKeyUseCase
# from .security.audit_log_query_use_case import AuditLogQueryUseCase
