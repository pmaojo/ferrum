FROM rust:1.75-slim as builder

WORKDIR /app

# Install dependencies
RUN apt-get update && \
    apt-get install -y pkg-config libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Install cargo-watch for development hot-reload and typeshare CLI
RUN cargo install cargo-watch typeshare-cli

# Copy the Cargo.toml and Cargo.lock files
COPY Cargo.toml Cargo.lock ./

# Create dummy source files to build dependencies
RUN mkdir -p src && \
    echo "fn main() {}" > src/main.rs

# Build dependencies
RUN cargo build

# Copy the actual source code
COPY . .

# Build the application
RUN cargo build

# Runtime stage
FROM debian:bullseye-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy the binary from the builder stage
COPY --from=builder /app/target/debug/ferrum-backend /app/ferrum-backend

# Set the entry point
CMD ["./ferrum-backend"]
