"""Deployment orchestrator for SaaS marketplace."""

from __future__ import annotations

import os
import yaml
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from marketplace.saas_marketplace import SaaSMarketplace, MarketplaceTemplate
from adapters.retrievers.graphrag_sdk_adapter import GraphRAGSDKAdapter
from domain.advanced_workflow_orchestrator import AdvancedWorkflowOrchestrator
from ui_adapters.streamlit_app import create_streamlit_config


class DeploymentOrchestrator:
    """Orchestrates SaaS deployments from marketplace templates."""

    def __init__(self, marketplace: SaaSMarketplace):
        self.marketplace = marketplace

    async def deploy_template(
        self,
        deployment_id: str,
        domain: str = "0.0.0.0",
        port: int = 5000
    ) -> Dict[str, Any]:
        """Deploy a marketplace template."""

        # Load deployment configuration
        deployment = self.marketplace.get_deployment_status(deployment_id)
        template_id = deployment["template_id"]
        template = self.marketplace.load_template(template_id)

        try:
            # Update status
            deployment["status"] = "deploying"
            self._update_deployment_status(deployment_id, deployment)

            # 1. Create GraphRAG configuration
            graphrag_config = await self._create_graphrag_config(
                template, deployment, domain, port
            )

            # 2. Setup ontology
            ontology_path = await self._setup_ontology(
                template.ontology_config, deployment["tenant_id"]
            )

            # 3. Configure workflows
            workflow_config = await self._setup_workflows(
                template.workflow_config, deployment["tenant_id"]
            )

            # 4. Initialize UI adapters
            ui_configs = await self._setup_ui_adapters(
                template.ui_adapters, graphrag_config, deployment
            )

            # 5. Create main configuration file
            main_config = self._create_main_config(
                template, deployment, graphrag_config, ontology_path,
                workflow_config, ui_configs, domain, port
            )

            # Save configuration
            config_path = f"deployments/{deployment_id}/settings.yml"
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            with open(config_path, 'w') as f:
                yaml.dump(main_config, f, default_flow_style=False)

            # Update deployment status
            deployment["status"] = "deployed"
            deployment["config_path"] = config_path
            deployment["url"] = f"http://{domain}:{port}"
            self._update_deployment_status(deployment_id, deployment)

            return {
                "deployment_id": deployment_id,
                "status": "deployed",
                "url": f"http://{domain}:{port}",
                "config_path": config_path,
                "template": template.name
            }

        except Exception as e:
            deployment["status"] = "failed"
            deployment["error"] = str(e)
            self._update_deployment_status(deployment_id, deployment)
            raise

    async def _create_graphrag_config(
        self,
        template: MarketplaceTemplate,
        deployment: Dict[str, Any],
        domain: str,
        port: int
    ) -> Dict[str, Any]:
        """Create GraphRAG SDK configuration."""

        base_config = template.configuration.get("graphrag_sdk", {})

        return {
            "host": domain,
            "port": base_config.get("port", 6379),
            "username": f"${{{deployment['tenant_id'].upper()}_FALKORDB_USER}}",
            "password": f"${{{deployment['tenant_id'].upper()}_FALKORDB_PASSWORD}}",
            "llm_model": base_config.get("llm_model", "gemini-2.0-flash"),
            "embedding_model": base_config.get("embedding_model", "text-embedding-3-small"),
            "api_key": f"${{{deployment['tenant_id'].upper()}_GEMINI_API_KEY}}",
            "max_tokens": base_config.get("max_tokens", 4096),
            "temperature": base_config.get("temperature", 0.1)
        }

    async def _setup_ontology(
        self,
        ontology_config: Dict[str, Any],
        tenant_id: str
    ) -> str:
        """Setup ontology configuration."""

        ontology_path = f"deployments/{tenant_id}/ontology.json"
        os.makedirs(os.path.dirname(ontology_path), exist_ok=True)

        # Create ontology JSON
        ontology_data = {
            "entities": ontology_config.get("entities", []),
            "relationships": ontology_config.get("relationships", []),
            "domain": ontology_config.get("domain", "general"),
            "version": "1.0.0",
            "tenant_id": tenant_id
        }

        import json
        with open(ontology_path, 'w') as f:
            json.dump(ontology_data, f, indent=2)

        return ontology_path

    async def _setup_workflows(
        self,
        workflow_config: Dict[str, Any],
        tenant_id: str
    ) -> Dict[str, Any]:
        """Setup workflow configurations."""

        workflows = workflow_config.get("workflows", [])

        # Convert to workflow orchestrator format
        orchestrator_config = {
            "enable_multi_agent": True,
            "workflows": workflows,
            "tenant_id": tenant_id
        }

        return orchestrator_config

    async def _setup_ui_adapters(
        self,
        ui_adapters: list,
        graphrag_config: Dict[str, Any],
        deployment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Setup UI adapter configurations."""

        ui_configs = {}

        for adapter in ui_adapters:
            if adapter == "streamlit":
                ui_configs["streamlit"] = {
                    "title": f"{deployment.get('template_id', 'GraphRAG')} Dashboard",
                    "port": 8501,
                    "graphrag_config": graphrag_config
                }
            elif adapter == "rest_api":
                ui_configs["rest_api"] = {
                    "port": 8000,
                    "graphrag_config": graphrag_config,
                    "cors_origins": ["*"]
                }
            elif adapter == "chainlit":
                ui_configs["chainlit"] = {
                    "port": 8002,
                    "graphrag_config": graphrag_config
                }
            elif adapter == "autogen":
                ui_configs["autogen"] = {
                    "registry_config": graphrag_config
                }

        return ui_configs

    def _create_main_config(
        self,
        template: MarketplaceTemplate,
        deployment: Dict[str, Any],
        graphrag_config: Dict[str, Any],
        ontology_path: str,
        workflow_config: Dict[str, Any],
        ui_configs: Dict[str, Any],
        domain: str,
        port: int
    ) -> Dict[str, Any]:
        """Create main deployment configuration."""

        return {
            "# SaaS Deployment Configuration": None,
            "deployment_info": {
                "deployment_id": deployment["deployment_id"],
                "template_id": template.id,
                "template_name": template.name,
                "tenant_id": deployment["tenant_id"],
                "organization_id": deployment["organization_id"]
            },

            "# GraphRAG SDK Configuration": None,
            "graphrag_sdk": graphrag_config,

            "# Ontology Configuration": None,
            "ontology": {
                "path": ontology_path,
                "domain": template.ontology_config.get("domain", "general")
            },

            "# Workflow Configuration": None,
            "workflows": workflow_config,

            "# UI Adapters Configuration": None,
            "ui_adapters": ui_configs,

            "# Server Configuration": None,
            "server": {
                "host": domain,
                "port": port,
                "debug": False
            }
        }

    def _update_deployment_status(
        self,
        deployment_id: str,
        deployment: Dict[str, Any]
    ) -> None:
        """Update deployment status."""

        deployment_file = self.marketplace.deployments_dir / f"{deployment_id}.yaml"
        with open(deployment_file, 'w') as f:
            yaml.dump(deployment, f, default_flow_style=False)
