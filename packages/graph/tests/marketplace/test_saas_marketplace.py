import yaml
from datetime import datetime
import marketplace.saas_marketplace as sm
from marketplace.saas_marketplace import (
    SaaSMarketplace,
    create_template_from_yaml,
    MarketplaceTemplate,
)
from domain.entities import SubscriptionTier
import pytest


SIMPLE_TEMPLATE = """
id: test-template
name: Test Template
description: Simple template
tier_required: free
category: misc
configuration:
  graphrag_sdk:
    port: 1234
"""

def create_marketplace(tmp_path, monkeypatch=None):
    templates = tmp_path / "templates"
    deployments = tmp_path / "deployments"
    marketplace = SaaSMarketplace(str(templates), str(deployments))
    if monkeypatch:
        monkeypatch.setattr(sm.yaml, "safe_load", yaml.unsafe_load)
    return marketplace

def test_create_and_load_template(tmp_path, monkeypatch):
    marketplace = create_marketplace(tmp_path, monkeypatch)
    template = create_template_from_yaml(SIMPLE_TEMPLATE)
    marketplace.create_template(template)
    loaded = marketplace.load_template(template.id)
    assert loaded.name == template.name
    assert loaded.configuration["graphrag_sdk"]["port"] == 1234

def test_list_templates_filtering(tmp_path, monkeypatch):
    marketplace = create_marketplace(tmp_path, monkeypatch)
    t1 = create_template_from_yaml(SIMPLE_TEMPLATE)
    t2_yaml = SIMPLE_TEMPLATE.replace("test-template", "other").replace("misc", "ai")
    t2 = create_template_from_yaml(t2_yaml)
    marketplace.create_template(t1)
    marketplace.create_template(t2)
    all_templates = marketplace.list_templates()
    assert len(all_templates) == 2
    ai_templates = marketplace.list_templates(category="ai")
    assert [t.id for t in ai_templates] == [t2.id]


def test_deploy_and_status(tmp_path, monkeypatch):
    marketplace = create_marketplace(tmp_path, monkeypatch)
    template = create_template_from_yaml(SIMPLE_TEMPLATE)
    marketplace.create_template(template)
    dep_id = marketplace.deploy_template(template.id, "org1", custom_config={"x": 1})
    status = marketplace.get_deployment_status(dep_id)
    assert status["status"] == "pending"
    assert status["configuration"]["x"] == 1


def test_missing_template(tmp_path, monkeypatch):
    marketplace = create_marketplace(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        marketplace.load_template("missing")


def test_invalid_yaml():
    bad_yaml = "id: 1\nname: n"
    with pytest.raises(ValueError):
        create_template_from_yaml(bad_yaml)


def test_missing_deployment(tmp_path, monkeypatch):
    marketplace = create_marketplace(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        marketplace.get_deployment_status("none")
