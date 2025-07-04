FROM rustlang/rust:nightly-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y build-essential pkg-config libssl-dev perl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN cargo install cargo-leptos

# Copy the Cargo.toml and source code
COPY Cargo.toml ./
COPY src/ ./src/

# Create directories for shared-models
RUN mkdir -p /shared-models

# Build the application
# Note: We'll mount the shared-models directory at runtime via Docker Compose volume

# Command that will keep the container running instead of trying to run cargo
# since we're using this as a development environment
CMD ["tail", "-f", "/dev/null"]

EXPOSE 3000
