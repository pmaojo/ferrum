import { writeFileSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import express from 'express';
import listEndpoints from 'express-list-endpoints';

import { registerRoutes } from '../server/routes';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  const app = express();
  const server = await registerRoutes(app);
  const routes = listEndpoints(app).filter(r => r.path.startsWith('/api/'));

  const openapi: any = {
    openapi: '3.0.0',
    info: {
      title: 'SCG API',
      version: '1.0.0',
    },
    paths: {},
  };

  for (const { path, methods } of routes) {
    openapi.paths[path] = openapi.paths[path] || {};
    for (const method of methods) {
      openapi.paths[path][method.toLowerCase()] = {
        responses: { 200: { description: 'Success' } },
      };
    }
  }

  const specPath = path.resolve(__dirname, '../openapi.json');
  writeFileSync(specPath, JSON.stringify(openapi, null, 2));
  server.close();
}

main();
