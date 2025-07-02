FROM rust:1.75-slim

# Install build dependencies for the desktop app
RUN apt-get update && apt-get install -y pkg-config libssl-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# Launch the Bevy desktop studio
CMD ["cargo", "run", "-p", "studio-desktop"]
