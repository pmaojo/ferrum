# Semantic GUI

Semantic GUI is a Dockerized web application providing a graph editor, template marketplace, PermaGraph control panel, and agent management dashboard.

For details on how this service fits into the shared documentation workflow with Kthulu and PermaGraph, see the [documentation flow guide](../../docs/documentation-flow.md).

## Prerequisites

- Docker installed on your system.

## Development

This application uses Node.js. After installing dependencies with `pnpm install`, common scripts like `pnpm dev`, `pnpm build`, `pnpm start`, and `pnpm check` are available (see `package.json`).

### Generar el SDK a partir de la API

Cuando se modifiquen las rutas del servidor, regenera el esquema OpenAPI y el SDK de cliente:

```bash
pnpm openapi:generate
pnpm sdk:generate
```

El primer comando produce `packages/semantic_gui/openapi.json` recorriendo todas las rutas expuestas. El segundo genera `packages/semantic_gui/client/src/sdk.ts` utilizando ese esquema.

## Frontend routes

- `/` – Graph editor
- `/templates` – Template marketplace
- `/permagraph` – PermaGraph control panel
- `/agents` – Agent management dashboard

## Running with Docker

### 1. Build the Docker Image

From the project root directory, run:

```sh
docker build -t semantic-gui .
```

### 2. Run the Docker Container

To run the application, you need to provide two environment variables: `DATABASE_URL` and `GROQ_API_KEY`.

Example:

```sh
docker run -p 5000:5000 \
  -e DATABASE_URL="your_database_connection_string" \
  -e GROQ_API_KEY="your_groq_api_key" \
  --name semantic-gui-container semantic-gui
```

Replace `"your_database_connection_string"` and `"your_groq_api_key"` with your actual credentials.

The application will be accessible at `http://localhost:5000`.

### Environment Variables

- `DATABASE_URL`: (Required) The connection string for your PostgreSQL database.
- `GROQ_API_KEY`: (Required) Your API key for Groq services.
- `PORT`: (Optional) The port on which the server should listen. Defaults to 5000 if not set (the Dockerfile EXPOSEs 5000). The `pnpm start` script (`node dist/server/index.js`) would need to be able to consume this, or it's fixed. The current `index.ts` seems to hardcode 5000 or use a port from `process.env.PORT`.
- `VITE_WS_URL`: (Optional) WebSocket server URL for the frontend. Set this if your WebSocket endpoint differs from the current host. For example, create a `.env` file with `VITE_WS_URL=ws://localhost:1234`.
