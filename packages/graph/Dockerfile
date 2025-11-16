
# Build arguments for versioning and metadata
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy project files
COPY pyproject.toml ./pyproject.toml
COPY requirements.txt ./requirements.txt

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir -e .

# Final stage
FROM python:3.11-slim

# Build arguments for versioning and metadata
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    VERSION="${VERSION}"

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy installed dependencies from base image
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code (include infrastructure for startup scripts)
COPY domain/ /app/domain/
COPY application/ /app/application/
COPY adapters/ /app/adapters/
COPY ui_adapters/ /app/ui_adapters/
COPY infrastructure/ /app/infrastructure/
COPY marketplace/ /app/marketplace/
COPY kernel/ /app/kernel/
COPY analytics/ /app/analytics/
COPY permagraph/ /app/permagraph/

# Copy project metadata required for editable install
COPY pyproject.toml ./pyproject.toml
COPY requirements.txt ./requirements.txt

# Install the package in editable mode so modules like `kernel` are importable
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=5 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Command to run the application
CMD ["uvicorn", "ui_adapters.rest_api.server:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
