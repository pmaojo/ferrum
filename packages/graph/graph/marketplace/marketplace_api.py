from __future__ import annotations

"""FastAPI application exposing the SaaS marketplace."""


from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio

from marketplace.saas_marketplace import SaaSMarketplace
from marketplace.deployment_orchestrator import DeploymentOrchestrator
from domain.entities import SubscriptionTier
from adapters.auth.production_auth_factory import AuthenticationFactory
from adapters.auth.production_auth_service import ProductionAuthService
from marketplace.dependencies import get_create_user_use_case
from ui_adapters.rest_api.server import validate_api_key
import logging


app = FastAPI(title="GraphRAG SaaS Marketplace", version="1.0.0")

# Initialize marketplace
marketplace = SaaSMarketplace()
orchestrator = DeploymentOrchestrator(marketplace)


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    tier_required: str
    price_usd: float
    tags: List[str]
    author: str
    version: str
    default_tenant: str


class DeploymentRequest(BaseModel):
    template_id: str
    organization_id: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    custom_config: Optional[Dict[str, Any]] = None


class DeploymentResponse(BaseModel):
    deployment_id: str
    status: str
    url: Optional[str] = None
    config_path: Optional[str] = None
    template: Optional[str] = None


@app.get("/marketplace/templates", response_model=List[TemplateResponse])
async def list_templates(
    category: Optional[str] = None,
    tier: Optional[str] = None,
    tags: Optional[str] = None,
):
    """List available marketplace templates."""

    # Parse filters
    tier_filter = None
    if tier:
        try:
            tier_filter = SubscriptionTier(tier.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")

    tags_filter = None
    if tags:
        tags_filter = [tag.strip() for tag in tags.split(",")]

    # Get templates
    templates = marketplace.list_templates(
        category=category, tier=tier_filter, tags=tags_filter
    )

    return [
        TemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            category=t.category,
            tier_required=t.tier_required.value,
            price_usd=t.price_usd,
            tags=t.tags,
            author=t.author,
            version=t.version,
            default_tenant=t.default_tenant,
        )
        for t in templates
    ]


@app.get("/marketplace/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str):
    """Get a specific template by ID."""

    try:
        template = marketplace.load_template(template_id)
        return TemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            category=template.category,
            tier_required=template.tier_required.value,
            price_usd=template.price_usd,
            tags=template.tags,
            author=template.author,
            version=template.version,
            default_tenant=template.default_tenant,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post(
    "/marketplace/deploy",
    response_model=DeploymentResponse,
    dependencies=[Depends(validate_api_key)],
)
async def deploy_template(request: DeploymentRequest):
    """Deploy a marketplace template."""

    try:
        # Create deployment
        deployment_id = marketplace.deploy_template(
            template_id=request.template_id,
            organization_id=request.organization_id,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            custom_config=request.custom_config,
        )

        # Start deployment in background
        asyncio.create_task(orchestrator.deploy_template(deployment_id))

        return DeploymentResponse(deployment_id=deployment_id, status="deploying")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/marketplace/deployments/{deployment_id}",
    response_model=DeploymentResponse,
    dependencies=[Depends(validate_api_key)],
)
async def get_deployment_status(deployment_id: str):
    """Get deployment status."""

    try:
        deployment = marketplace.get_deployment_status(deployment_id)

        return DeploymentResponse(
            deployment_id=deployment_id,
            status=deployment["status"],
            url=deployment.get("url"),
            config_path=deployment.get("config_path"),
            template=deployment.get("template_id"),
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/marketplace/categories")
async def get_categories():
    """Get available template categories."""

    templates = marketplace.list_templates()
    categories = list(set(t.category for t in templates))

    return {"categories": sorted(categories)}


# Helper function to get create user use case
def get_create_user_use_case():
    """Get CreateUserUseCase with mock dependencies for marketplace API."""
    from infrastructure.storage import get_user_repository
    from application.use_cases.user_org.create_user_use_case import CreateUserUseCase

    # Mock implementations for required services
    class MockOrganizationRepository:
        def get_by_id(self, org_id):
            from domain.entities import Organization, SubscriptionTier

            return Organization(
                id=org_id,
                name=f"Organization-{org_id}",
                subscription_tier=SubscriptionTier.FREE,
                is_active=True,
            )

    class MockPasswordService:
        def hash_password(self, password):
            return f"hashed_{password}"

    class MockAuthorizationService:
        def check_permission(self, user_id, resource_id, action):
            return True

    logger = logging.getLogger(__name__)

    class MockAuditService:
        """Minimal audit service that logs activity."""

        def log_activity(self, **kwargs):
            """Mock implementation that simply logs the activity."""
            logger.info("Audit activity: %s", kwargs)

    class MockTracer:
        """Very simple tracer that logs span lifecycle and metrics."""

        def start_span(self, name, **kwargs):
            logger.debug("Starting span '%s' with %s", name, kwargs)
            return self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            """Log span exit; returning False avoids swallowing errors."""
            logger.debug("Exiting span", exc_info=(exc_type, exc, tb))
            return False

        def record_metric(self, **kwargs):
            """Mock metric recorder that logs the provided data."""
            logger.debug("Metric recorded: %s", kwargs)

    user_repository = get_user_repository()
    organization_repository = MockOrganizationRepository()
    password_service = MockPasswordService()
    authorization_service = MockAuthorizationService()
    audit_service = MockAuditService()
    tracer = MockTracer()

    return CreateUserUseCase(
        user_repository,
        organization_repository,
        password_service,
        authorization_service,
        audit_service,
        tracer,
    )


@app.post("/auth/register", dependencies=[Depends(validate_api_key)])
async def register_user(
    registration_data: dict,
    create_user_use_case=Depends(get_create_user_use_case),
):
    """Register new user."""
    try:
        auth_service = ProductionAuthService(create_user_use_case)
        result = await auth_service.register_user(registration_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/register/complete", dependencies=[Depends(validate_api_key)])
async def register_user_complete(
    registration_data: dict,
    create_user_use_case=Depends(get_create_user_use_case),
):
    """Register new user with complete ERP and backend integration."""
    try:
        integrated_service = AuthenticationFactory.create_integrated_service(
            create_user_use_case
        )
        result = await integrated_service.register_user_complete(registration_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/auth/profile/complete/{user_id}", dependencies=[Depends(validate_api_key)])
async def get_complete_profile(
    user_id: str,
    create_user_use_case=Depends(get_create_user_use_case),
):
    """Get complete user profile from all integrated systems."""
    try:
        integrated_service = AuthenticationFactory.create_integrated_service(
            create_user_use_case
        )
        profile = await integrated_service.get_complete_user_profile(user_id)
        return profile
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with platform information."""
    return {
        "name": "PermaGraph SaaS Marketplace",
        "version": "1.0.0",
        "description": "Enterprise GraphRAG Platform with Multi-Modal AI",
        "authentication": "Replit Auth Integrated",
        "features": [
            "GraphRAG SDK Integration",
            "Multi-Modal Processing",
            "Enterprise Templates",
            "Real-time Analytics",
            "Marketplace Deployment",
            "Auto User Registration",
        ],
    }


@app.post("/auth/replit/register")
async def register_replit_user(request: Request):
    """Auto-register Replit users when they first access the platform."""
    try:
        # Extract Replit user info from headers
        user_id = request.headers.get("X-Replit-User-Id")
        username = request.headers.get("X-Replit-User-Name", "replit-user")

        if not user_id:
            raise HTTPException(
                status_code=401, detail="Replit authentication required"
            )

        # Generate tenant ID from user context
        tenant_id = f"replit-org-{user_id}"  # Each Replit user gets their own tenant

        # Auto-create user with default settings
        registration_data = {
            "email": f"{username}@replit.user",
            "name": username,
            "password": "replit-managed",
            "organization_name": f"{username}-org",
            "subscription_tier": "free",
            "auth_method": "replit",
        }

        integrated_service = AuthenticationFactory.create_integrated_service(
            get_create_user_use_case()
        )
        result = await integrated_service.register_user_complete(registration_data)

        return {
            "success": True,
            "message": "Replit user registered successfully",
            "user_id": result.get("user", {}).get("id"),
            "organization": result.get("user", {}).get("organization_id"),
        }

    except Exception:
        # Return existing user if already registered
        return {
            "success": True,
            "message": "User already exists or registration completed",
            "user_id": f"replit-{user_id}",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
