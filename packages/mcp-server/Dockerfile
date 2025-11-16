# Multi-stage Dockerfile for MCP Server with Docker integration

FROM node:18-alpine AS base

# Install system dependencies for Docker integration
RUN apk add --no-cache \
    curl \
    docker-cli \
    bash \
    git \
    && rm -rf /var/cache/apk/*

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S mcp -u 1001 -G nodejs

# Copy application code
COPY --chown=mcp:nodejs . .

# Create necessary directories
RUN mkdir -p /data /app/logs /app/config && \
    chown -R mcp:nodejs /data /app/logs /app/config

# Development stage
FROM base AS development

# Install development dependencies
RUN npm ci && npm cache clean --force

# Install nodemon globally for development
RUN npm install -g nodemon

USER mcp

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["npm", "run", "dev"]

# Production stage
FROM base AS production

# Remove development files
RUN rm -rf test-* *.md

USER mcp

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["npm", "start"]