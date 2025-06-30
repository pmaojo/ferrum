# syntax=docker/dockerfile:1

FROM rust:1.73-slim as builder
WORKDIR /app

# Required for Diesel PostgreSQL bindings
RUN apt-get update \
    && apt-get install -y libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Pre-cache dependencies
COPY Cargo.toml Cargo.lock ./
COPY cli/Cargo.toml cli/Cargo.toml
COPY compiler/Cargo.toml compiler/Cargo.toml
COPY engine/Cargo.toml engine/Cargo.toml
COPY shared-models/Cargo.toml shared-models/Cargo.toml
RUN mkdir src && echo "fn main(){}" > src/main.rs
RUN cargo build --release --locked --bin ferrum || true
RUN rm -r src

# Build actual binary
COPY . .
RUN cargo build --release --locked --bin ferrum

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/ferrum /usr/local/bin/ferrum
ENTRYPOINT ["ferrum"]
CMD ["--help"]
