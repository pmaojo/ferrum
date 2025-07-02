FROM rust:slim AS builder
WORKDIR /app
COPY backend ./backend
RUN cargo build --release --manifest-path backend/Cargo.toml

FROM debian:stable-slim
WORKDIR /app
COPY --from=builder /app/target/release/backend ./backend
CMD ["./backend"]
