FROM rust:slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential pkg-config libssl-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY backend ./backend
RUN cargo build --release --manifest-path backend/Cargo.toml

FROM debian:stable-slim
WORKDIR /app
COPY --from=builder /app/target/release/backend ./backend
CMD ["./backend"]
