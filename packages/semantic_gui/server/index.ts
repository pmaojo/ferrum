import { randomUUID } from 'crypto';

import express, {
  type Request,
  type Response,
  type NextFunction,
} from 'express';

import { registerRoutes } from './routes';
import { LoggerFactory } from './services/logging';
import { storage } from './storage';
import { setupVite, serveStatic, log } from './vite';

const app = express();
const serverLogger = LoggerFactory.createLogger('server');

app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use((req, res, next) => {
  const traceId = (req.headers['x-correlation-id'] as string) || randomUUID();
  res.setHeader('X-Correlation-Id', traceId);
  req.traceId = traceId;
  next();
});
app.use((_, res, next) => {
  res.setHeader('X-API-Version', 'v1');
  next();
});

app.use((req, res, next) => {
  const start = Date.now();
  const { path } = req;
  let capturedJsonResponse: Record<string, unknown> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    if (res.statusCode >= 400 && bodyJson && typeof bodyJson === 'object') {
      const message = bodyJson.message ?? bodyJson.error ?? 'Error';
      const code = bodyJson.code ?? res.statusCode;
      const { details } = bodyJson;
      const traceId = res.getHeader('X-Correlation-Id');
      bodyJson = { code, message, details, traceId };
    }
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on('finish', () => {
    const duration = Date.now() - start;
    if (path.startsWith('/api')) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }

      if (logLine.length > 80) {
        logLine = `${logLine.slice(0, 79)}…`;
      }

      log(logLine);
    }
  });

  next();
});

await (async () => {
  serverLogger.info('Starting server initialization', {
    nodeEnv: process.env.NODE_ENV,
    logLevel: process.env.LOG_LEVEL,
  });

  await storage.init();
  serverLogger.info('Storage initialized successfully');

  const server = await registerRoutes(app);
  serverLogger.info('Routes registered successfully');

  app.use((err: unknown, req: Request, res: Response, _next: NextFunction) => {
    const errorObj = err as any; // Type assertion for error object
    const status = Number(errorObj?.status ?? errorObj?.statusCode ?? 500);
    const message = errorObj?.message ?? 'Internal Server Error';
    const code = errorObj?.code ?? status;
    const details = errorObj?.details;
    const traceId = res.getHeader('X-Correlation-Id') ?? req.traceId;

    // Log the error with proper context
    serverLogger.error(
      'Request error',
      err instanceof Error ? err : new Error(String(err)),
      {
        method: req.method,
        path: req.path,
        status,
        traceId,
        userAgent: req.get('User-Agent'),
        ip: req.ip,
      }
    );

    res.status(status).json({ code, message, details, traceId });
    throw err;
  });

  // importantly only setup vite in development and after
  // setting up all the other routes so the catch-all route
  // doesn't interfere with the other routes
  if (app.get('env') === 'development') {
    await setupVite(app, server);
  } else {
    serveStatic(app);
  }

  // Use PORT env variable if provided, otherwise default to 3000.
  // This serves both the API and the client.
  // Port 3000 is the only port that is not firewalled by default.
  const port = Number(process.env.PORT) || 3000;
  // HOST defaults to 0.0.0.0 so containerised deployments keep listening on
  // every interface; set HOST=127.0.0.1 to bind loopback only.
  const host = process.env.HOST || '0.0.0.0';
  // SO_REUSEPORT is opt-in: it is only useful when several cluster workers
  // share a port, and it is not supported everywhere (macOS and Windows
  // reject the socket option outright with ENOTSUP/EINVAL, which crashes the
  // process at startup). Set REUSE_PORT=true to enable it explicitly.
  const reusePort = process.env.REUSE_PORT === 'true';
  server.listen(
    {
      port,
      host,
      reusePort,
    },
    () => {
      serverLogger.info(`Server started successfully`, {
        port,
        host,
        reusePort,
        environment: app.get('env'),
        nodeVersion: process.version,
      });
      log(`serving on port ${port}`);
    }
  );
})();
