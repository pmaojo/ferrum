FROM rustlang/rust:nightly-slim

WORKDIR /app

COPY . .

RUN cargo build -p studio-desktop

CMD ["cargo", "run", "-p", "studio-desktop"]
