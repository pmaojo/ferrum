# syntax=docker/dockerfile:1
FROM rustlang/rust:nightly-slim

# Instala dependencias necesarias para build y debug
RUN apt-get update && apt-get install -y perl pkg-config libssl-dev make curl bash

WORKDIR /workspace/studio-web

# ... el resto del Dockerfile ... 