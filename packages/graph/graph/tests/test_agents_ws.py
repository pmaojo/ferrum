import asyncio
import sys
import types
from types import SimpleNamespace
import importlib.util
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from application.ports.agent import AgentManagementPort

# ---------------------------------------------------------------------------
# Stub dependencies module to avoid heavy imports
# ---------------------------------------------------------------------------

dependencies_stub = types.ModuleType("ui_adapters.rest_api.dependencies")

class ServiceContainer(SimpleNamespace):
    pass

def get_container():
    return ServiceContainer()

def create_default_container(*args, **kwargs):
    return ServiceContainer()

dependencies_stub.ServiceContainer = ServiceContainer
dependencies_stub.get_container = get_container
dependencies_stub.create_default_container = create_default_container
sys.modules["ui_adapters.rest_api.dependencies"] = dependencies_stub

# Load agents route module directly to avoid importing full package
agents_path = Path(__file__).resolve().parents[1] / "ui_adapters/rest_api/routes/agents.py"
spec = importlib.util.spec_from_file_location("agents", agents_path)
agents = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agents)

# ---------------------------------------------------------------------------
# In-memory agent service implementation for tests
# ---------------------------------------------------------------------------

class InMemoryAgentService(AgentManagementPort):
    def __init__(self) -> None:
        self.agents: dict[str, str] = {}
        self.subscribers: list[asyncio.Queue] = []
        self.loop: asyncio.AbstractEventLoop | None = None

    async def list_agents(self) -> list[str]:
        return list(self.agents.keys())

    async def start_agent(self, name: str) -> None:
        self.agents[name] = "running"
        await self._publish("started", f"agent {name} started", name)

    async def stop_agent(self, name: str) -> None:
        self.agents[name] = "stopped"
        await self._publish("stopped", f"agent {name} stopped", name)

    def log(self, name: str, message: str) -> None:
        if self.loop is not None:
            asyncio.run_coroutine_threadsafe(
                self._publish("log", message, name), self.loop
            )

    def subscribe(self):  # type: ignore[override]
        queue: asyncio.Queue = asyncio.Queue()
        self.subscribers.append(queue)
        if self.loop is None:
            self.loop = asyncio.get_event_loop()

        async def _iterator():
            try:
                while True:
                    yield await queue.get()
            finally:
                self.subscribers.remove(queue)

        return _iterator()

    async def _publish(self, status: str, message: str, agent: str) -> None:
        event = {"status": status, "message": message, "agent": agent}
        for q in list(self.subscribers):
            await q.put(event)


@pytest.fixture
def agent_service() -> InMemoryAgentService:
    return InMemoryAgentService()


@pytest.fixture
def client(agent_service: InMemoryAgentService):
    app = FastAPI()
    container = ServiceContainer(agent_service=agent_service)
    app.state.container = container
    app.dependency_overrides[dependencies_stub.get_container] = lambda: container
    app.include_router(agents.router)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_agent_websocket_flow(client: TestClient, agent_service: InMemoryAgentService):
    with client.websocket_connect("/ws") as ws:
        resp = client.post("/api/v1/agents/demo/start")
        assert resp.status_code == 200
        event = ws.receive_json()
        assert event["event"] == "agents.event"
        assert event["status"] == "started"
        assert event["agent"] == "demo"

        agent_service.log("demo", "running")
        event = ws.receive_json()
        assert event["status"] == "log"
        assert event["message"] == "running"

        resp = client.post("/api/v1/agents/demo/stop")
        assert resp.status_code == 200
        event = ws.receive_json()
        assert event["status"] == "stopped"
        assert event["agent"] == "demo"
