import asyncio
import yaml
import sys
from types import ModuleType

# Avoid optional heavy dependencies during import
sys.modules.setdefault("numpy", ModuleType("numpy"))
sys.modules.setdefault("PIL", ModuleType("PIL"))
sys.modules.setdefault("torch", ModuleType("torch"))
sys.modules.setdefault("streamlit", ModuleType("streamlit"))
sys.modules["streamlit"].cache_resource = lambda *a, **k: (lambda f: f)
sys.modules.setdefault("requests", ModuleType("requests"))
sys.modules.setdefault("transformers", ModuleType("transformers"))
sys.modules["transformers"].AutoTokenizer = object
sys.modules.setdefault("plotly", ModuleType("plotly"))
sys.modules.setdefault("plotly.express", ModuleType("express"))
sys.modules.setdefault("plotly.graph_objects", ModuleType("graph_objects"))
sys.modules.setdefault("pandas", ModuleType("pandas"))
streamlit_app_stub = ModuleType("streamlit_app")
streamlit_app_stub.create_streamlit_config = lambda *a, **k: {}
sys.modules.setdefault("ui_adapters.streamlit_app", streamlit_app_stub)
redis_mod = ModuleType("redis")
redis_mod.commands = ModuleType("commands")
redis_mod.commands.search = ModuleType("search")
redis_mod.commands.search.field = ModuleType("field")
redis_mod.commands.search.field.TextField = object
redis_mod.commands.search.field.VectorField = object
sys.modules.setdefault("redis", redis_mod)
sys.modules.setdefault("redis.commands", redis_mod.commands)
sys.modules.setdefault("redis.commands.search", redis_mod.commands.search)
sys.modules.setdefault("redis.commands.search.field", redis_mod.commands.search.field)

from marketplace.saas_marketplace import SaaSMarketplace, create_template_from_yaml
from marketplace.deployment_orchestrator import DeploymentOrchestrator
import pytest

SIMPLE_TEMPLATE = """
id: deploy-template
name: Deploy Template
description: For deploy testing
tier_required: free
category: misc
configuration:
  graphrag_sdk: {}
ontology_config: {}
workflow_config:
  workflows: []
ui_adapters: [streamlit]
"""

def create_marketplace(tmp_path, monkeypatch=None):
    marketplace = SaaSMarketplace(str(tmp_path/"templates"), str(tmp_path/"deployments"))
    if monkeypatch:
        import marketplace.saas_marketplace as sm
        monkeypatch.setattr(sm.yaml, "safe_load", yaml.unsafe_load)
    return marketplace

@pytest.mark.asyncio
async def test_successful_deployment(tmp_path, monkeypatch):
    marketplace = create_marketplace(tmp_path, monkeypatch)
    template = create_template_from_yaml(SIMPLE_TEMPLATE)
    marketplace.create_template(template)
    dep_id = marketplace.deploy_template(template.id, "org1")
    orchestrator = DeploymentOrchestrator(marketplace)
    result = await orchestrator.deploy_template(dep_id, domain="127.0.0.1", port=8080)
    assert result["status"] == "deployed"
    status = marketplace.get_deployment_status(dep_id)
    assert status["status"] == "deployed"
    with open(status["config_path"], "r") as f:
        config = yaml.safe_load(f)
    assert config["server"]["port"] == 8080

@pytest.mark.asyncio
async def test_deployment_failure(tmp_path, monkeypatch):
    marketplace = create_marketplace(tmp_path, monkeypatch)
    template = create_template_from_yaml(SIMPLE_TEMPLATE)
    marketplace.create_template(template)
    dep_id = marketplace.deploy_template(template.id, "org1")
    orchestrator = DeploymentOrchestrator(marketplace)
    async def boom(*args, **kwargs):
        raise RuntimeError("fail")
    monkeypatch.setattr(orchestrator, "_setup_ontology", boom)
    with pytest.raises(RuntimeError):
        await orchestrator.deploy_template(dep_id)
    status = marketplace.get_deployment_status(dep_id)
    assert status["status"] == "failed"
    assert "fail" in status["error"]
