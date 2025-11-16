from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from application.ports.agent import AgentManagementPort
from ui_adapters.rest_api.dependencies import ServiceContainer, get_container

router = APIRouter()


async def get_agent_service(
    container: ServiceContainer = Depends(get_container),
) -> AgentManagementPort:
    service: Any = getattr(container, "agent_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Agent service not configured")
    return service


@router.get("/api/v1/agents")
async def list_agents(
    agent_service: AgentManagementPort = Depends(get_agent_service),
) -> Dict[str, List[str]]:
    agents = await agent_service.list_agents()
    return {"agents": agents}


@router.post("/api/v1/agents/{name}/start")
async def start_agent(
    name: str,
    agent_service: AgentManagementPort = Depends(get_agent_service),
) -> Dict[str, str]:
    await agent_service.start_agent(name)
    return {"status": "started", "agent": name}


@router.post("/api/v1/agents/{name}/stop")
async def stop_agent(
    name: str,
    agent_service: AgentManagementPort = Depends(get_agent_service),
) -> Dict[str, str]:
    await agent_service.stop_agent(name)
    return {"status": "stopped", "agent": name}


@router.websocket("/ws")
async def agents_ws(
    websocket: WebSocket,
    agent_service: AgentManagementPort = Depends(get_agent_service),
) -> None:
    await websocket.accept()
    try:
        async for event in agent_service.subscribe():
            await websocket.send_json({"event": "agents.event", **event})
    except WebSocketDisconnect:
        pass
