import fs from 'fs';
import { type Server } from 'http';
import path from 'path';

import express, { type Express } from 'express';
import { nanoid } from 'nanoid';
import { createServer as createViteServer, createLogger } from 'vite';

import viteConfig from '../vite.config';

import { LoggerFactory } from './services/logging';

const viteLogger = createLogger();
const logger = LoggerFactory.createLogger('vite');

export function log(message: string, source = 'express') {
  // Use the new logger instead of console.log
  logger.info(message, { source });
}

export async function setupVite(app: Express, server: Server) {
  const serverOptions = {
    middlewareMode: true,
    hmr: { 
      server,
      port: 24678,
      clientPort: 24678,
    },
    ws: {
      port: 24678,
    },
    allowedHosts: true as const,
  };

  const vite = await createViteServer({
    ...viteConfig,
    configFile: false,
    customLogger: {
      ...viteLogger,
      error: (msg, options) => {
        viteLogger.error(msg, options);
        // Don't exit on WebSocket errors
        if (msg.includes('WebSocket') || msg.includes('ws error')) {
          logger.warn(`Vite WebSocket error: ${msg}`, { options });
          return;
        }
        viteLogger.error(msg, options);
        process.exit(1);
      },
    },
    server: serverOptions,
    appType: 'custom',
  });

  app.use(vite.middlewares);
  app.use('*', async (req, res, next) => {
    const url = req.originalUrl;

    try {
      const clientTemplate = path.resolve(
        import.meta.dirname,
        '..',
        'client',
        'index.html'
      );

      // always reload the index.html file from disk incase it changes
      let template = await fs.promises.readFile(clientTemplate, 'utf-8');
      template = template.replace(
        `src="/src/main.tsx"`,
        `src="/src/main.tsx?v=${nanoid()}"`
      );
      const page = await vite.transformIndexHtml(url, template);
      res.status(200).set({ 'Content-Type': 'text/html' }).end(page);
    } catch (e) {
      vite.ssrFixStacktrace(e as Error);
      next(e);
    }
  });
}

export function serveStatic(app: Express) {
  const distPath = path.resolve(import.meta.dirname, '../client');

  if (!fs.existsSync(distPath)) {
    throw new Error(
      `Could not find the build directory: ${distPath}, make sure to build the client first`
    );
  }

  app.use(express.static(distPath));

  // fall through to index.html if the file doesn't exist
  app.use('*', (_req, res) => {
    res.sendFile(path.resolve(distPath, 'index.html'));
  });
}
