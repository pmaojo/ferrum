"""SaaS Marketplace for GraphRAG configurations."""

from __future__ import annotations

import yaml
import uuid
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

from domain.entities import SubscriptionTier
from application.use_cases.subscription.create_subscription_use_case import (
    CreateSubscriptionUseCase,
)
from application.use_cases.knowledge_graph.create_knowledge_graph_use_case import (
    CreateKnowledgeGraphUseCase,
)
from application.use_cases.ontology.create_ontology_use_case import (
    CreateOntologyUseCase,
)


@dataclass
class MarketplaceTemplate:
    """Marketplace template configuration."""

    id: str
    name: str
    description: str
    category: str
    tier_required: SubscriptionTier
    price_usd: float
    configuration: Dict[str, Any]
    ontology_config: Dict[str, Any]
    workflow_config: Dict[str, Any]
    ui_adapters: List[str]
    tags: List[str]
    author: str
    version: str
    created_at: datetime
    default_tenant: str


class SaaSMarketplace:
    """SaaS Marketplace for GraphRAG configurations."""

    def __init__(
        self,
        templates_dir: str = "marketplace/templates",
        deployments_dir: str = "marketplace/deployments",
    ):
        self.templates_dir = Path(templates_dir)
        self.deployments_dir = Path(deployments_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.deployments_dir.mkdir(parents=True, exist_ok=True)

    def load_template(self, template_id: str) -> MarketplaceTemplate:
        """Load a marketplace template by ID."""
        template_file = self.templates_dir / f"{template_id}.yaml"

        if not template_file.exists():
            raise ValueError(f"Template {template_id} not found")

        with open(template_file, "r") as f:
            data = yaml.safe_load(f)

        return MarketplaceTemplate(**data)

    def create_template(self, template: MarketplaceTemplate) -> str:
        """Save a new marketplace template."""
        template_file = self.templates_dir / f"{template.id}.yaml"

        with open(template_file, "w") as f:
            yaml.dump(asdict(template), f, default_flow_style=False)

        return template.id

    def list_templates(
        self,
        category: Optional[str] = None,
        tier: Optional[SubscriptionTier] = None,
        tags: Optional[List[str]] = None,
    ) -> List[MarketplaceTemplate]:
        """List available templates with optional filtering."""
        templates = []

        for template_file in self.templates_dir.glob("*.yaml"):
            try:
                template = self.load_template(template_file.stem)

                # Apply filters
                if category and template.category != category:
                    continue
                if tier and template.tier_required != tier:
                    continue
                if tags and not any(tag in template.tags for tag in tags):
                    continue

                templates.append(template)
            except Exception:
                continue  # Skip invalid templates

        return sorted(templates, key=lambda t: t.created_at, reverse=True)

    def deploy_template(
        self,
        template_id: str,
        organization_id: str,
        tenant_id: Optional[str] = None,
        user_id: str | None = None,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Deploy a template for an organization."""
        template = self.load_template(template_id)
        deployment_id = str(uuid.uuid4())
        tenant_id = tenant_id or template.default_tenant

        # Merge custom configuration
        final_config = template.configuration.copy()
        if custom_config:
            final_config.update(custom_config)

        # Create deployment configuration
        deployment_config = {
            "deployment_id": deployment_id,
            "template_id": template_id,
            "organization_id": organization_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "configuration": final_config,
            "ontology_config": template.ontology_config,
            "workflow_config": template.workflow_config,
            "ui_adapters": template.ui_adapters,
            "status": "pending",
        }

        # Save deployment
        deployment_file = self.deployments_dir / f"{deployment_id}.yaml"
        with open(deployment_file, "w") as f:
            yaml.dump(deployment_config, f, default_flow_style=False)

        return deployment_id

    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get status of a deployment."""
        deployment_file = self.deployments_dir / f"{deployment_id}.yaml"

        if not deployment_file.exists():
            raise ValueError(f"Deployment {deployment_id} not found")

        with open(deployment_file, "r") as f:
            return yaml.safe_load(f)


# Marketplace template creator
def create_template_from_yaml(yaml_content: str) -> MarketplaceTemplate:
    """Create a marketplace template from YAML content."""
    data = yaml.safe_load(yaml_content)

    # Validate required fields
    required_fields = ["id", "name", "description", "category", "configuration"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Set defaults
    data.setdefault("tier_required", SubscriptionTier.FREE)
    data.setdefault("price_usd", 0.0)
    data.setdefault("ontology_config", {})
    data.setdefault("workflow_config", {})
    data.setdefault("ui_adapters", [])
    data.setdefault("tags", [])
    data.setdefault("author", "unknown")
    data.setdefault("version", "1.0.0")
    data.setdefault("created_at", datetime.utcnow())
    data.setdefault("default_tenant", f"{data['id']}-tenant")

    # Convert tier string to enum if needed
    if isinstance(data["tier_required"], str):
        data["tier_required"] = SubscriptionTier(data["tier_required"].lower())

    return MarketplaceTemplate(**data)
