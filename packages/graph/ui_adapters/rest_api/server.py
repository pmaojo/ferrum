"""Production-ready REST API for GraphRAG Ontology services."""

from __future__ import annotations

import logging
import os
import time
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt import PyJWTError

try:  # pragma: no cover - optional dependency
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
except Exception:  # pragma: no cover - provide minimal stubs
    from infrastructure.stubs.slowapi import (
        Limiter,
        _rate_limit_exceeded_handler,
        RateLimitExceeded,
    )
    from infrastructure.stubs.slowapi.util import get_remote_address
    from infrastructure.stubs.slowapi.middleware import SlowAPIMiddleware
from prometheus_client import Counter, Histogram

from ui_adapters.rest_api import dependencies
from domain.auth import Role, User
from domain.exceptions import GraphRAGException
from application.exceptions import DependencyError

from pydantic import ValidationError

from .settings import RestApiSettings
from .settings_factory import get_settings as factory_get_settings
from .pydantic_patch import patch_protected_namespaces


def get_settings() -> RestApiSettings:
    return factory_get_settings()


logging.basicConfig(level=logging.INFO)
patch_protected_namespaces()
logger = logging.getLogger(__name__)
settings = get_settings()

# Tenant registry mapping API keys to tenant IDs. In production this would come
# from a persistent store but for now it is configured via the TENANT_REGISTRY
# environment variable containing a JSON object of ``{"api-key": "tenant"}``.
TENANT_REGISTRY: dict[str, str] = json.loads(
    os.environ.get("TENANT_REGISTRY", "{}")
)

REQUEST_COUNT = Counter(
    "api_requests_total", "Total API requests", ["method", "endpoint", "status"]
)
REQUEST_DURATION = Histogram(
    "api_request_duration_seconds", "API request duration", ["method", "endpoint"]
)
SYNC_DURATION = Histogram(
    "permagraph_sync_duration_seconds",
    "Duration of sync operations",
    ["endpoint"],
)
AGENT_OPERATIONS = Counter(
    "permagraph_agent_operations_total",
    "Total agent operations",
    ["endpoint", "status"],
)


def rate_limit_key(request: Request) -> str:
    """Generate a rate limiting key that includes tenant and API key.

    Combining both values provides granular throttling per tenant and API key.
    If no API key is present or it is unknown, we fall back to the client's
    remote address.
    """
    api_key = request.headers.get("X-API-Key")
    tenant_id = TENANT_REGISTRY.get(api_key)
    if tenant_id and api_key:
        return f"{tenant_id}:{api_key}"
    return get_remote_address(request)


limiter = Limiter(key_func=rate_limit_key)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
SECRET_KEY = os.environ.get("JWT_SECRET", "secret")
ALGORITHM = "HS256"

MAX_PAYLOAD_SIZE = 1024 * 1024  # 1MB


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=60))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Decode the JWT token and return the authenticated user."""
    credentials_exception = HTTPException(
        status_code=401, detail="Could not validate credentials"
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
    return User(username=username, role=Role(role))


def require_role(*roles: Role):
    """Dependency factory enforcing user roles."""
    def role_dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return role_dependency


from ui_adapters.rest_api.routes import (
    health,
    ontology_versions,
    query,
    structrag,
    ingestion,
    docs_ingestion,
    repo_ingestion,
    url_ingestion,
    optometry,
    ferrum,
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})[
        "OAuth2"
    ] = {
        "type": "oauth2",
        "flows": {"password": {"tokenUrl": "/token", "scopes": {}}},
    }
    protected_prefixes = ("/api/",)
    public_paths = {"/api/health", "/metrics", "/", "/token"}
    for path, methods in openapi_schema.get("paths", {}).items():
        if path.startswith(protected_prefixes) and path not in public_paths:
            for method in methods.values():
                method.setdefault("security", []).append({"OAuth2": []})
    app.openapi_schema = openapi_schema
    return app.openapi_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting PermaGraph API server...")
    try:
        app.state.container = dependencies.create_default_container(settings=settings)
    except ValidationError as exc:  # pragma: no cover - exercised in tests
        logger.error("Invalid configuration: %s", exc)
        raise RuntimeError("Invalid configuration") from exc
    yield
    app.state.container = None
    logger.info("Shutting down PermaGraph API server...")


app = FastAPI(title="PermaGraph API", version="1.0.0", lifespan=lifespan)
app.openapi = custom_openapi
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Validate the X-API-Key header for event endpoints.

    The tenant registry maps API keys to tenant identifiers. Requests to the
    e-commerce event ingestion endpoints must include a valid API key. When a
    key is valid, the resolved tenant ID is stored on ``request.state`` for
    downstream handlers.
    """
    if request.url.path.startswith("/api/v1/ecommerce"):
        api_key = request.headers.get("X-API-Key")
        tenant_id = TENANT_REGISTRY.get(api_key)
        if tenant_id is None:
            return JSONResponse(
                status_code=401,
                content={"error": "HTTP_401", "message": "Invalid API key"},
            )
        request.state.tenant_id = tenant_id
        request.state.api_key = api_key
    return await call_next(request)


@app.middleware("http")
async def payload_size_limit_middleware(request: Request, call_next):
    body = await request.body()
    if len(body) > MAX_PAYLOAD_SIZE:
        exc = RequestValidationError(
            [{"loc": ("body",), "msg": "Payload too large", "type": "payload_too_large"}]
        )
        return await request_validation_error_handler(request, exc)
    request._body = body
    return await call_next(request)


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Simple token endpoint for OAuth2 password flow."""
    role = form_data.scopes[0] if form_data.scopes else Role.QUERY.value
    token = create_access_token({"sub": form_data.username, "role": role})
    return {"access_token": token, "token_type": "bearer"}


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start = time.time()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
    finally:
        duration = time.time() - start
        REQUEST_COUNT.labels(
            method=request.method, endpoint=request.url.path, status=status_code
        ).inc()
        REQUEST_DURATION.labels(method=request.method, endpoint=request.url.path).observe(
            duration
        )
        if "/sync" in request.url.path:
            SYNC_DURATION.labels(endpoint=request.url.path).observe(duration)
        if "/agent" in request.url.path:
            status_label = "success" if status_code < 400 else "failure"
            AGENT_OPERATIONS.labels(
                endpoint=request.url.path, status=status_label
            ).inc()
        if "response" in locals():
            response.headers["X-Process-Time"] = str(duration)
    return response


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
):
    status = (
        413
        if any(err.get("type") == "payload_too_large" for err in exc.errors())
        else 422
    )
    return JSONResponse(
        status_code=status,
        content={"error": "REQUEST_VALIDATION_ERROR", "message": exc.errors()},
    )


@app.exception_handler(DependencyError)
async def dependency_error_handler(request: Request, exc: DependencyError):
    return JSONResponse(
        status_code=503,  # Service Unavailable
        content={
            "error": exc.error_code,
            "message": exc.message,
            "context": exc.context,
        },
    )


@app.exception_handler(GraphRAGException)
async def graphrag_exception_handler(request: Request, exc: GraphRAGException):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "context": exc.context,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": f"HTTP_{exc.status_code}", "message": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500, content={"error": "INTERNAL_SERVER_ERROR", "message": str(exc)}
    )


# Root route for basic info
@app.get("/")
async def root():
    return {
        "message": "PermaGraph API",
        "version": "1.0.0",
        "documentation": "/docs",
        "openapi": "/openapi.json",
        "redoc": "/redoc",
        "health": "/api/health",
    }


# Include routers -------------------------------------------------------------

# Public endpoints (no auth required)
app.include_router(health.router)

# Protected endpoints (auth required)
app.include_router(ontology_versions.router)  # public for bootstrap
app.include_router(query.router)
app.include_router(structrag.router)
app.include_router(ingestion.router)
app.include_router(docs_ingestion.router)
app.include_router(repo_ingestion.router)
app.include_router(url_ingestion.router)
app.include_router(optometry.router)
app.include_router(ferrum.router)

# Removed extra routers (llm, token_budget, training) in minimal mode

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
