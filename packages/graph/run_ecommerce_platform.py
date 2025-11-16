#!/usr/bin/env python3
"""
E-commerce Platform Runner
Starts the complete e-commerce and advertising platform.
"""

import asyncio
import threading
import time
import subprocess
import sys
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def start_api_server():
    """Start the REST API server."""
    logger.info("🚀 Starting API Server...")
    subprocess.run([sys.executable, "-m", "marketplace.marketplace_api"])

def start_streamlit_ecommerce():
    """Start Streamlit e-commerce interface."""
    logger.info("🛒 Starting E-commerce Streamlit Interface...")
    subprocess.run([
        sys.executable, "-c", 
        "import streamlit as st; from ui_adapters.streamlit.ecommerce_platform import main; main()"
    ])

def start_event_processing():
    """Start event processing in background."""
    logger.info("📡 Starting Event Processing...")
    from adapters.event_ingestion.kafka_event_adapter import KafkaEventAdapter
    from ui_adapters.rest_api.dependencies import get_context_manager, get_event_adapter
    
    async def run_event_processing():
        event_adapter = get_event_adapter()
        topics = [
            "ecommerce.product.view",
            "ecommerce.cart.add", 
            "ecommerce.purchase",
            "advertising.impression",
            "advertising.click",
            "advertising.conversion",
            "dsp.bid.request",
            "dsp.bid.response"
        ]
        await event_adapter.start_consuming(topics)
    
    def run_async():
        asyncio.run(run_event_processing())
    
    thread = threading.Thread(target=run_async, daemon=True)
    thread.start()

def main():
    """Main function to start all components."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("🏪 Starting E-commerce & Advertising Platform...")
    logger.info("=" * 50)

    # Ensure contract and competency question directories are available
    contracts_dir = Path(__file__).parent / "contracts"
    cqs_dir = Path(__file__).parent / "cqs"
    contracts_dir.mkdir(exist_ok=True)
    cqs_dir.mkdir(exist_ok=True)
    os.environ.setdefault("CONTRACTS_PATH", str(contracts_dir))
    os.environ.setdefault("CQS_PATH", str(cqs_dir))
    
    # Start background event processing
    start_event_processing()
    
    # Start API server in background
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    
    # Give API server time to start
    time.sleep(3)
    
    # Start Streamlit interface (blocking)
    start_streamlit_ecommerce()

if __name__ == "__main__":
    main()
