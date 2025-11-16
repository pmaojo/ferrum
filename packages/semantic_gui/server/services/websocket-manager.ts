import type { Server } from 'node:http';

import { WebSocketServer, WebSocket } from 'ws';

import type { WebSocketGraphStreamAdapter } from './graphStreamAdapter';

export interface WebSocketMessage {
  [key: string]: any;
}

interface UserSession {
  userId: string;
  userName: string;
  userEmail?: string;
  projectId: string;
  ws: WebSocket;
  isOnline: boolean;
  lastSeen: string;
  currentFile?: string;
  cursor?: { line: number; column: number };
}

interface EditLock {
  id: string;
  userId: string;
  userName: string;
  resourceType: string;
  resourceId: string;
  resourceName: string;
  projectId: string;
  timestamp: string;
  expiresAt: string;
}

interface CollaborationRoom {
  projectId: string;
  users: Set<string>;
  locks: Set<string>;
  lastActivity: string;
}

export class WebSocketManager {
  private wss: WebSocketServer;
  private clients: Map<string, Set<WebSocket>> = new Map();
  private userSessions: Map<string, UserSession> = new Map();
  private editLocks: Map<string, EditLock> = new Map();
  private collaborationRooms: Map<string, CollaborationRoom> = new Map();
  private permagraphSockets: Map<string, WebSocket> = new Map();

  constructor(
    server: Server,
    private graphStream?: WebSocketGraphStreamAdapter
  ) {
    this.wss = new WebSocketServer({ server });
    this.setupWebSocketServer();
  }

  private setupWebSocketServer(): void {
    this.wss.on('connection', (ws: WebSocket, _req: any) => {
      console.log('New WebSocket connection established');

      ws.on('message', (message: string) => {
        try {
          const data = JSON.parse(message);
          this.handleMessage(ws, data);
        } catch (error) {
          console.error('Invalid WebSocket message:', error);
        }
      });

      ws.on('close', () => {
        console.log('WebSocket connection closed');
        this.removeClient(ws);
      });

      ws.on('error', (error: any) => {
        console.error('WebSocket error:', error);
        this.removeClient(ws);
      });
    });
  }

  private handleMessage(ws: WebSocket, message: any): void {
    switch (message.type) {
      case 'subscribe':
        if (message.projectId) {
          this.subscribeToProject(
            ws,
            message.projectId,
            message.userId,
            message.userName,
            message.userEmail
          );
        }
        break;
      case 'unsubscribe':
        if (message.projectId) {
          this.unsubscribeFromProject(ws, message.projectId);
        }
        break;
      case 'ping':
        this.sendToClient(ws, {
          type: 'pong',
          timestamp: new Date().toISOString(),
        });
        break;
      case 'user-presence':
        this.handleUserPresence(ws, message);
        break;
      case 'request-edit-lock':
        this.handleEditLockRequest(ws, message);
        break;
      case 'release-edit-lock':
        this.handleEditLockRelease(ws, message);
        break;
      case 'cursor-update':
        this.handleCursorUpdate(ws, message);
        break;
      case 'file-change':
        this.handleFileChange(ws, message);
        break;
    }
  }

  private subscribeToProject(
    ws: WebSocket,
    projectId: string,
    userId?: string,
    userName?: string,
    userEmail?: string
  ): void {
    if (!this.clients.has(projectId)) {
      this.clients.set(projectId, new Set());
    }
    this.clients.get(projectId)!.add(ws);

    // Ensure PermaGraph proxy connection
    this.setupPermagraphProxy(projectId);

    // Create or update user session
    if (userId && userName) {
      const sessionId = `${projectId}-${userId}`;
      const session: UserSession = {
        userId,
        userName,
        userEmail,
        projectId,
        ws,
        isOnline: true,
        lastSeen: new Date().toISOString(),
      };

      this.userSessions.set(sessionId, session);

      this.graphStream?.register_client({
        tenant_id: projectId,
        client_id: sessionId,
        send: payload => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(payload));
          }
        },
      });

      // Create or join collaboration room
      if (!this.collaborationRooms.has(projectId)) {
        this.collaborationRooms.set(projectId, {
          projectId,
          users: new Set(),
          locks: new Set(),
          lastActivity: new Date().toISOString(),
        });
      }

      const room = this.collaborationRooms.get(projectId)!;
      room.users.add(userId);
      room.lastActivity = new Date().toISOString();

      // Notify other users about new user joining
      this.sendUserPresenceUpdate(projectId, session);
    }

    this.sendToClient(ws, {
      type: 'subscribed',
      projectId,
      timestamp: new Date().toISOString(),
    });
  }

  private setupPermagraphProxy(projectId: string): void {
    if (this.permagraphSockets.has(projectId)) {
      return;
    }
    const base = process.env.PERMAGRAPH_API_URL || 'http://localhost:8000';
    const wsUrl = `${base.replace(/^http/, 'ws')}/ws`;
    const proxy = new WebSocket(`${wsUrl}?projectId=${projectId}`);
    this.permagraphSockets.set(projectId, proxy);

    proxy.on('message', msg => {
      try {
        const data = JSON.parse(msg.toString());
        this.broadcastToProject(projectId, data);
      } catch (err) {
        console.error('PermaGraph proxy parse error', err);
      }
    });

    const cleanup = () => {
      this.permagraphSockets.delete(projectId);
    };

    proxy.on('close', cleanup);
    proxy.on('error', err => {
      console.error('PermaGraph proxy error', err);
      proxy.close();
    });
  }

  private unsubscribeFromProject(ws: WebSocket, projectId: string): void {
    const projectClients = this.clients.get(projectId);
    if (projectClients) {
      projectClients.delete(ws);
      if (projectClients.size === 0) {
        this.clients.delete(projectId);
        const proxy = this.permagraphSockets.get(projectId);
        proxy?.close();
        this.permagraphSockets.delete(projectId);
      }
    }

    // Remove session and unregister from graph stream
    this.userSessions.forEach((session, key) => {
      if (session.ws === ws && session.projectId === projectId) {
        this.graphStream?.unregister_client({
          tenant_id: projectId,
          client_id: key,
        });
        this.userSessions.delete(key);
      }
    });
  }

  /**
   * Unsubscribe all WebSocket clients from a project
   */
  unsubscribeProject(projectId: string): void {
    const projectClients = this.clients.get(projectId);
    if (projectClients) {
      projectClients.forEach(ws => {
        this.sendToClient(ws, {
          type: 'unsubscribed',
          projectId,
          timestamp: new Date().toISOString(),
        });
        this.unsubscribeFromProject(ws, projectId);
      });
    }

    // Cleanup project-specific data
    this.userSessions.forEach((session, key) => {
      if (session.projectId === projectId) {
        this.graphStream?.unregister_client({
          tenant_id: projectId,
          client_id: key,
        });
        this.userSessions.delete(key);
      }
    });
    this.editLocks.forEach((lock, key) => {
      if (lock.projectId === projectId) {
        this.editLocks.delete(key);
      }
    });
    this.collaborationRooms.delete(projectId);
  }

  /**
   * Unsubscribe all clients from all projects
   */
  unsubscribeAll(): void {
    for (const projectId of Array.from(this.clients.keys())) {
      this.unsubscribeProject(projectId);
    }
  }

  private removeClient(ws: WebSocket): void {
    this.clients.forEach((clientSet, projectId) => {
      if (clientSet.has(ws)) {
        this.unsubscribeFromProject(ws, projectId);
      }
    });
  }

  private sendToClient(ws: WebSocket, message: any): void {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    }
  }

  /**
   * Broadcast message to all clients subscribed to a project
   */
  broadcastToProject(projectId: string, message: WebSocketMessage): void {
    const projectClients = this.clients.get(projectId);
    if (projectClients) {
      const messageStr = JSON.stringify(message);
      projectClients.forEach(ws => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(messageStr);
        }
      });
    }
  }

  /**
   * Broadcast message to all connected clients
   */
  broadcastToAll(message: WebSocketMessage): void {
    const messageStr = JSON.stringify(message);
    this.wss.clients.forEach(ws => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(messageStr);
      }
    });
  }

  /**
   * Send Kthulu-specific events
   */
  sendKthuluEvent(projectId: string, eventType: string, data: any): void {
    this.broadcastToProject(projectId, {
      type: 'kthulu-event',
      projectId,
      data: {
        eventType,
        ...data,
      },
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Send code change notifications
   */
  sendCodeChangeEvent(projectId: string, change: any): void {
    this.sendKthuluEvent(projectId, 'code-changed', change);
  }

  /**
   * Send module creation notifications
   */
  sendModuleCreatedEvent(projectId: string, module: any): void {
    this.sendKthuluEvent(projectId, 'module-created', module);
  }

  /**
   * Send validation result notifications
   */
  sendValidationEvent(projectId: string, validation: any): void {
    this.sendKthuluEvent(projectId, 'validation-result', validation);
  }

  /**
   * Send graph update notifications
   */
  sendGraphUpdateEvent(projectId: string, update: any): void {
    this.broadcastToProject(projectId, {
      type: 'graph.updated',
      projectId,
      data: update,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Handle user presence updates
   */
  private handleUserPresence(ws: WebSocket, message: any): void {
    const { projectId, userId, currentFile, cursor } = message;
    const sessionId = `${projectId}-${userId}`;
    const session = this.userSessions.get(sessionId);

    if (session) {
      session.currentFile = currentFile;
      session.cursor = cursor;
      session.lastSeen = new Date().toISOString();

      this.sendUserPresenceUpdate(projectId, session);
    }
  }

  /**
   * Handle edit lock requests
   */
  private handleEditLockRequest(ws: WebSocket, message: any): void {
    const {
      projectId,
      userId,
      userName,
      resourceType,
      resourceId,
      resourceName,
    } = message;
    const lockId = `${projectId}-${resourceType}-${resourceId}`;

    // Check if resource is already locked
    const existingLock = this.editLocks.get(lockId);
    if (existingLock && existingLock.userId !== userId) {
      this.sendToClient(ws, {
        type: 'edit-lock-denied',
        projectId,
        data: {
          lockId,
          reason: 'Resource already locked',
          lockedBy: existingLock.userName,
          expiresAt: existingLock.expiresAt,
        },
        timestamp: new Date().toISOString(),
      });
      return;
    }

    // Create new lock
    const lock: EditLock = {
      id: lockId,
      userId,
      userName,
      resourceType,
      resourceId,
      resourceName,
      projectId,
      timestamp: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 5 * 60 * 1000).toISOString(), // 5 minutes
    };

    this.editLocks.set(lockId, lock);

    // Set auto-release timer
    setTimeout(
      () => {
        if (this.editLocks.has(lockId)) {
          this.handleEditLockRelease(ws, { lockId, projectId, userId });
        }
      },
      5 * 60 * 1000
    );

    // Notify all users in the project
    this.broadcastToProject(projectId, {
      event: 'edit-lock-acquired',
      ...lock,
    });
  }

  /**
   * Handle edit lock releases
   */
  private handleEditLockRelease(ws: WebSocket, message: any): void {
    const { lockId, projectId, userId } = message;
    const lock = this.editLocks.get(lockId);

    if (lock && lock.userId === userId) {
      this.editLocks.delete(lockId);

      // Notify all users in the project
      this.broadcastToProject(projectId, {
        event: 'edit-lock-released',
        lockId,
        userId,
        resourceName: lock.resourceName,
        timestamp: new Date().toISOString(),
      });
    }
  }

  /**
   * Handle cursor position updates
   */
  private handleCursorUpdate(ws: WebSocket, message: any): void {
    const { projectId, userId, cursor, file } = message;
    const sessionId = `${projectId}-${userId}`;
    const session = this.userSessions.get(sessionId);

    if (session) {
      session.cursor = cursor;
      session.currentFile = file;

      // Broadcast cursor update to other users
      this.broadcastToProject(projectId, {
        event: 'cursor-updated',
        userId,
        userName: session.userName,
        cursor,
        file,
        timestamp: new Date().toISOString(),
      });
    }
  }

  /**
   * Handle file change notifications
   */
  private handleFileChange(ws: WebSocket, message: any): void {
    const {
      projectId,
      userId,
      fileName,
      changeType,
      content: _content,
    } = message;

    // Detect potential conflicts
    const conflictingUsers = Array.from(this.userSessions.values()).filter(
      session =>
        session.projectId === projectId &&
        session.userId !== userId &&
        session.currentFile === fileName
    );

    if (conflictingUsers.length > 0) {
      const conflictId = `conflict-${Date.now()}`;
      this.broadcastToProject(projectId, {
        event: 'edit-conflict-detected',
        conflictId,
        conflictType: 'concurrent_edit',
        resourceType: 'file',
        resourceId: fileName,
        resourceName: fileName,
        users: [userId, ...conflictingUsers.map(u => u.userId)],
        description: `Multiple users editing ${fileName} simultaneously`,
        timestamp: new Date().toISOString(),
      });
    }

    // Broadcast file change to other users
    this.broadcastToProject(projectId, {
      event: 'code-changed',
      userId,
      fileName,
      changeType,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Send user presence update to all users in project
   */
  private sendUserPresenceUpdate(
    projectId: string,
    session: UserSession
  ): void {
    this.broadcastToProject(projectId, {
      event: 'user-presence-updated',
      userId: session.userId,
      userName: session.userName,
      userEmail: session.userEmail,
      isOnline: session.isOnline,
      currentFile: session.currentFile,
      cursor: session.cursor,
      timestamp: session.lastSeen,
    });
  }

  /**
   * Send real-time violation notifications
   */
  sendViolationNotification(projectId: string, violation: any): void {
    this.broadcastToProject(projectId, {
      event: 'violation-found',
      ...violation,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Send agent heartbeat updates
   */
  sendAgentHeartbeat(
    projectId: string,
    agentId: string,
    healthy: boolean
  ): void {
    this.broadcastToProject(projectId, {
      event: 'agent-heartbeat',
      agentId,
      healthy,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Send system event notifications
   */
  sendSystemEvent(projectId: string, eventType: string, data: any): void {
    this.broadcastToProject(projectId, {
      event: 'system-event',
      eventType,
      ...data,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Get collaboration statistics
   */
  getCollaborationStats(projectId: string): any {
    const room = this.collaborationRooms.get(projectId);
    const activeSessions = Array.from(this.userSessions.values()).filter(
      session => session.projectId === projectId && session.isOnline
    );
    const projectLocks = Array.from(this.editLocks.values()).filter(
      lock => lock.projectId === projectId
    );

    return {
      activeUsers: activeSessions.length,
      totalUsers: room?.users.size || 0,
      activeLocks: projectLocks.length,
      lastActivity: room?.lastActivity,
      users: activeSessions.map(session => ({
        userId: session.userId,
        userName: session.userName,
        currentFile: session.currentFile,
        lastSeen: session.lastSeen,
      })),
      locks: projectLocks.map(lock => ({
        resourceName: lock.resourceName,
        userName: lock.userName,
        expiresAt: lock.expiresAt,
      })),
    };
  }

  /**
   * Get connection statistics
   */
  getStats(): {
    totalConnections: number;
    projectSubscriptions: Record<string, number>;
    collaborationRooms: number;
  } {
    const projectSubscriptions: Record<string, number> = {};
    this.clients.forEach((clientSet, projectId) => {
      projectSubscriptions[projectId] = clientSet.size;
    });

    return {
      totalConnections: this.wss.clients.size,
      projectSubscriptions,
      collaborationRooms: this.collaborationRooms.size,
    };
  }
}
