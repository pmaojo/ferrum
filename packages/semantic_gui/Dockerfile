# Use Node.js 20 LTS as the base image with optimizations
FROM --platform=linux/amd64 node:20.18-alpine AS base

# Install build dependencies in single layer
RUN apk add --no-cache \
    postgresql-client \
    python3 \
    make \
    g++ \
    && npm install -g pnpm@latest

# Set working directory
WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./
COPY pnpm-lock.yaml* ./
COPY tsconfig.json ./
COPY vite.config.ts ./
COPY tailwind.config.ts ./
COPY components.json .

# Install dependencies with optimizations
ENV NODE_ENV=production
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

RUN pnpm config set store-dir /pnpm/.pnpm-store && \
    pnpm install --frozen-lockfile --prod=false && \
    pnpm add --save-dev @rollup/rollup-linux-x64-musl @esbuild/linux-x64

# Copy the rest of the application code
COPY . .

# Build the application with optimizations
RUN NODE_OPTIONS="--max-old-space-size=2048" pnpm run build

# Verify build output exists
RUN ls -la dist/

# Production stage - optimized runtime
FROM --platform=linux/amd64 node:20.18-alpine AS production

# Install minimal runtime dependencies
RUN apk add --no-cache \
    postgresql-client \
    dumb-init \
    && npm install -g pnpm@latest

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S scg -u 1001 -G nodejs

WORKDIR /app

# Copy package files and install production dependencies only
COPY --from=base /app/package*.json ./
COPY --from=base /app/pnpm-lock.yaml* ./

# Install only production dependencies
RUN pnpm config set store-dir /pnpm/.pnpm-store && \
    pnpm install --frozen-lockfile --prod

# Copy built files from the base stage
COPY --from=base --chown=scg:nodejs /app/dist/client/ ./dist/
COPY --from=base --chown=scg:nodejs /app/server/ ./server/
COPY --from=base --chown=scg:nodejs /app/templates/ ./templates/
COPY --from=base --chown=scg:nodejs /app/wait-for-postgres.sh ./wait-for-postgres.sh

# Make the wait script executable
RUN chmod +x /wait-for-postgres.sh

# Switch to non-root user
USER scg

# Expose the port the app runs on
EXPOSE 5000

# Use dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Start the application with the wait script
CMD ["/wait-for-postgres.sh", "postgres", "pnpm", "start"]
