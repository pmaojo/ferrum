"""LLM status monitoring endpoints."""

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException

from ui_adapters.rest_api.dependencies import get_llm
from application.ports import LLMPort

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM Status"])


@router.get("/status")
async def get_llm_status(
    llm: LLMPort = Depends(get_llm),
) -> Dict[str, Any]:
    """Get the status of LLM adapters and fallback chain.

    Returns information about adapter health, performance metrics,
    and current fallback configuration.
    """
    try:
        # Check if this is an intelligent fallback adapter
        if hasattr(llm, 'get_adapter_status'):
            status = llm.get_adapter_status()
            status["adapter_type"] = "intelligent_fallback"
            return status

        # Check if this is a transformers server adapter
        elif hasattr(llm, 'server_config'):
            health_status = await llm._health_check() if hasattr(llm, '_health_check') else True
            return {
                "adapter_type": "transformers_server",
                "server_url": llm.server_config.base_url,
                "model_name": llm.server_config.model_name,
                "embedding_model": llm.embedding_model,
                "healthy": health_status,
                "timeout_seconds": llm.server_config.timeout_seconds,
                "max_retries": llm.server_config.max_retries,
            }

        # Standard adapter (OpenAI, Gemini, etc.)
        else:
            adapter_name = type(llm).__name__.replace("Adapter", "").replace("LLM", "")
            return {
                "adapter_type": adapter_name.lower(),
                "healthy": True,  # Assume healthy if no specific health check
                "generation_model": getattr(llm, 'generation_model', 'unknown'),
                "embedding_model": getattr(llm, 'embedding_model', 'unknown'),
            }

    except Exception as e:
        logger.error(f"Failed to get LLM status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get LLM status: {str(e)}"
        )


@router.get("/health")
async def check_llm_health(
    llm: LLMPort = Depends(get_llm),
) -> Dict[str, Any]:
    """Perform a health check on the LLM adapter.

    Makes a simple test request to verify the LLM is responding.
    """
    try:
        start_time = __import__('time').time()

        # Simple test generation
        test_result = llm.generate(
            prompt="test",
            tenant_id="health_check",
            opts={"max_tokens": 1}
        )

        latency_ms = (__import__('time').time() - start_time) * 1000

        return {
            "healthy": True,
            "latency_ms": round(latency_ms, 2),
            "test_successful": test_result is not None,
            "timestamp": __import__('datetime').datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": __import__('datetime').datetime.now().isoformat(),
        }


@router.post("/test")
async def test_llm_generation(
    prompt: str = "Hello, how are you?",
    tenant_id: str = "test",
    max_tokens: int = 50,
    llm: LLMPort = Depends(get_llm),
) -> Dict[str, Any]:
    """Test LLM generation with a custom prompt.

    Useful for testing specific adapters and configurations.
    """
    try:
        start_time = __import__('time').time()

        result = llm.generate(
            prompt=prompt,
            tenant_id=tenant_id,
            opts={"max_tokens": max_tokens}
        )

        latency_ms = (__import__('time').time() - start_time) * 1000

        return {
            "success": True,
            "prompt": prompt,
            "response": result,
            "latency_ms": round(latency_ms, 2),
            "token_count": llm.get_token_count(text=prompt),
        }

    except Exception as e:
        logger.error(f"LLM test generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Test generation failed: {str(e)}"
        )
