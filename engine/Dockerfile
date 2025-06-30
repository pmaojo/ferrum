FROM rust:1.75-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y pkg-config libssl-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the Cargo.toml and source code
COPY Cargo.toml ./
COPY src/ ./src/

# Create directories for shared-models
RUN mkdir -p /shared-models

# Build the application
# Note: We'll mount the shared-models directory at runtime via Docker Compose volume

EXPOSE 3000

CMD ["cargo", "run", "--release"]
