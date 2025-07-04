FROM rustlang/rust:nightly-slim

# Install build dependencies for the desktop app
RUN apt-get update && apt-get install -y pkg-config libssl-dev perl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN cargo install cargo-leptos && cargo build -p studio-desktop


CMD ["cargo", "run", "-p", "studio-desktop"]
