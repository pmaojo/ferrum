#!/usr/bin/env python3
"""Script to create and deploy SaaS configurations from YAML templates."""

import argparse
import asyncio
import yaml
from pathlib import Path

from marketplace.saas_marketplace import SaaSMarketplace, create_template_from_yaml
from marketplace.deployment_orchestrator import DeploymentOrchestrator


async def create_deployment_from_yaml(
    yaml_file: str,
    organization_id: str,
    tenant_id: str | None,
    user_id: str,
    domain: str = "0.0.0.0",
    port: int = 5000,
):
    """Create and deploy a SaaS configuration from YAML."""

    print(f"🚀 Creating SaaS deployment from {yaml_file}")

    # Initialize marketplace
    marketplace = SaaSMarketplace()
    orchestrator = DeploymentOrchestrator(marketplace)

    # Load and create template
    with open(yaml_file, "r") as f:
        yaml_content = f.read()

    template = create_template_from_yaml(yaml_content)
    template_id = marketplace.create_template(template)
    tenant_id = tenant_id or template.default_tenant

    print(f"✅ Created template: {template.name} ({template_id})")

    # Deploy template
    deployment_id = marketplace.deploy_template(
        template_id=template_id,
        organization_id=organization_id,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    print(f"📦 Created deployment: {deployment_id}")
    print("🔄 Starting deployment process...")

    # Execute deployment
    result = await orchestrator.deploy_template(
        deployment_id=deployment_id, domain=domain, port=port
    )

    print(f"✅ Deployment completed!")
    print(f"🌐 URL: {result['url']}")
    print(f"📄 Config: {result['config_path']}")

    return result


def main():
    """Main CLI entry point."""

    parser = argparse.ArgumentParser(
        description="Deploy GraphRAG SaaS configurations from YAML"
    )
    parser.add_argument("yaml_file", help="Path to YAML template file")
    parser.add_argument("--organization-id", required=True, help="Organization ID")
    parser.add_argument(
        "--tenant-id", required=False, help="Tenant ID (defaults to template value)"
    )
    parser.add_argument("--user-id", required=True, help="User ID")
    parser.add_argument(
        "--domain", default="0.0.0.0", help="Deployment domain (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Deployment port (default: 5000)"
    )

    args = parser.parse_args()

    # Run deployment
    asyncio.run(
        create_deployment_from_yaml(
            yaml_file=args.yaml_file,
            organization_id=args.organization_id,
            tenant_id=args.tenant_id,
            user_id=args.user_id,
            domain=args.domain,
            port=args.port,
        )
    )


if __name__ == "__main__":
    main()
