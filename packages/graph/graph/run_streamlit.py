#!/usr/bin/env python3
"""Run the Streamlit interface for PermaGraph."""

import subprocess
import sys
import os
import time
import logging

logger = logging.getLogger(__name__)

def ensure_redis_running():
    """Ensure Redis server is running before starting Streamlit."""
    try:
        import redis
    except ImportError:
        logger.warning("⚠️ Redis module not installed - will run in fallback mode")
        return False

    try:
        # Test if Redis is already running
        client = redis.Redis(host="0.0.0.0", port=6379, socket_connect_timeout=2)
        client.ping()
        logger.info("✅ Redis is already running")
        return True
    except Exception:
        logger.warning("⚠️ Redis not available - will run in fallback mode")
        return False

def main():
    """Run the Streamlit app."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Ensure we're in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Check Redis availability
    ensure_redis_running()

    # Prepare contract and competency question paths
    contracts_dir = os.path.join(os.getcwd(), "contracts")
    cqs_dir = os.path.join(os.getcwd(), "cqs")
    os.makedirs(contracts_dir, exist_ok=True)
    os.makedirs(cqs_dir, exist_ok=True)

    # Run streamlit with Replit-optimized settings
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", os.getcwd())
    env.setdefault("CONTRACTS_PATH", contracts_dir)
    env.setdefault("CQS_PATH", cqs_dir)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "ui_adapters/streamlit_app.py",
            "--server.port",
            "8501",
            "--server.address",
            "0.0.0.0",
            "--server.headless",
            "true",
            "--server.enableCORS",
            "false",
            "--server.enableWebsocketCompression",
            "false",
            "--server.enableXsrfProtection",
            "false",
            "--server.runOnSave",
            "false",
        ],
        env=env,
    )

if __name__ == "__main__":
    main()
