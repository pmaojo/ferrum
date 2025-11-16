"""Connection manager for FalkorDB using redis-py.

This class handles Redis connection setup and Lua script loading while keeping
FalkorGraphAdapter focused on high level operations.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Dict, Optional

import redis

logger = logging.getLogger(__name__)


class FalkorDBConnectionManager:
    """Manage Redis connections and pre-loaded Lua scripts."""

    def __init__(
        self,
        connection_string: str,
        *,
        pool_size: int = 20,
        scripts_path: Optional[Path] = None,
    ) -> None:
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.pool: Optional[redis.ConnectionPool] = None
        self.client = self._create_client()
        self.scripts: Dict[str, str] = {}
        self.script_sources: Dict[str, str] = {}
        if scripts_path is not None:
            self.load_lua_scripts_with_retry(scripts_path)

    # Connection -----------------------------------------------------
    def _create_client(self) -> redis.Redis:
        """Create and verify a Redis client."""
        try:
            self.pool = redis.ConnectionPool.from_url(
                self.connection_string,
                max_connections=self.pool_size,
                decode_responses=True,
            )
            client = redis.Redis(connection_pool=self.pool)
            client.ping()
            return client
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to connect to FalkorDB: %s", exc, exc_info=True)
            raise

    # Lua script loading --------------------------------------------
    def load_lua_scripts(self, scripts_path: Path) -> None:
        """Load Lua scripts from the given directory."""
        logger.info("Loading Lua scripts from: %s", scripts_path)
        if not scripts_path.exists():
            raise FileNotFoundError(f"Scripts directory not found: {scripts_path}")

        self.scripts.clear()
        self.script_sources.clear()
        lua_files = list(scripts_path.glob("*.lua"))
        for script_file in lua_files:
            name = script_file.stem
            script_body = script_file.read_text()
            sha = self.client.script_load(script_body)
            self.scripts[name] = sha
            self.script_sources[name] = script_body
        if hasattr(self.client, "scripts"):
            self.client.scripts = self.scripts
        logger.info("Successfully loaded %s Lua scripts", len(self.scripts))

    def load_lua_scripts_with_retry(
        self,
        scripts_path: Path,
        *,
        max_attempts: int = 3,
        delay: float = 1.0,
    ) -> None:
        """Attempt to load Lua scripts with retry logic."""
        for attempt in range(max_attempts):
            try:
                self.load_lua_scripts(scripts_path)
                return
            except Exception as exc:  # pragma: no cover - logging only
                if attempt == max_attempts - 1:
                    logger.error("Failed to load Lua scripts: %s", exc, exc_info=True)
                    raise
                logger.warning(
                    "Lua script loading attempt %s failed: %s", attempt + 1, exc
                )
                time.sleep(delay)

    # Script helpers ------------------------------------------------
    def get_script_sha(self, name: str) -> Optional[str]:
        """Return the SHA of a loaded Lua script."""
        return self.scripts.get(name)

    def reload_script(self, name: str) -> str:
        """Reload a single Lua script by name and return its SHA."""
        body = self.script_sources.get(name)
        if body is None:
            raise KeyError(f"Lua script body for '{name}' not found")
        sha = self.client.script_load(body)
        self.scripts[name] = sha
        return sha
