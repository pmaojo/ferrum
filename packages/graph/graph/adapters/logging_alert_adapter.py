"""Simple alerting adapter that logs alert messages."""

import logging
from typing import Any, Dict, Optional

from application.ports import AlertingPort

logger = logging.getLogger(__name__)


class LoggingAlertAdapter(AlertingPort):
    """Default alerting adapter that logs alerts."""

    def send_alert(
        self, *, message: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        logger.warning("ALERT: %s | context=%s", message, context or {})
