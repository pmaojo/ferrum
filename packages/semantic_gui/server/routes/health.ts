import { Router } from 'express';

import type { WebSocketManager } from '../services/websocket-manager';

export function createHealthRouter(wsManager: WebSocketManager) {
  const router = Router();

  router.get('/health', (req, res) => {
    const stats = wsManager.getStats();
    res.json({
      status: 'healthy',
      websocket: {
        connections: stats.totalConnections,
        rooms: stats.collaborationRooms,
      },
      timestamp: new Date().toISOString(),
    });
  });

  router.get('/health/websocket', (req, res) => {
    const stats = wsManager.getStats();
    res.json({
      status: 'healthy',
      ...stats,
      timestamp: new Date().toISOString(),
    });
  });

  return router;
}
