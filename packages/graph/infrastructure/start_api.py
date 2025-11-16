#!/usr/bin/env python3
"""Startup script for the REST API with proper error handling."""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _enforce_pydantic_v2() -> None:
    """Ensure Pydantic 2.x is installed."""
    try:
        import pydantic  # type: ignore
    except Exception as exc:  # pragma: no cover - fatal at startup
        raise RuntimeError(
            "Pydantic is not installed. Install dependencies with 'pip install -e .' or 'poetry install'"
        ) from exc

    version = getattr(pydantic, "__version__", "")
    if not version.startswith("2."):
        raise RuntimeError(
            f"Pydantic {version} detected. Install Pydantic 2.x with 'pip install -e .' or 'poetry install'."
        )

def check_redis():
    """Check if Redis is available."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
        r.ping()
        return True
    except Exception:
        return False


def main():
    """Start the API server with proper setup."""
    logger.info("Starting PermaGraph API...")
    _enforce_pydantic_v2()

    # Check Redis availability
    if not check_redis():
        logger.error(
            "Redis server is not running on localhost:6379. "
            "Please start Redis before launching the API."
        )
        raise RuntimeError(
            "Redis not available. Start the Redis service and try again."
        )

    # Start the API server
    try:
        import uvicorn
        from ui_adapters.rest_api.server import app

        port = int(os.environ.get("PORT", 5000))
        logger.info(f"Starting server on 0.0.0.0:{port}")

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
