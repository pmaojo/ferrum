FROM node:18-slim

# Install Rust
RUN apt-get update && apt-get install -y curl build-essential pkg-config libssl-dev \
    && curl https://sh.rustup.rs -sSf | bash -s -- -y \
    && rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

COPY . .

# Install frontend dependencies
RUN npm --prefix studio install

EXPOSE 3001
CMD ["npm", "run", "--prefix", "studio", "server"]
