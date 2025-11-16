import { useState, useEffect, useRef, useCallback } from 'react';
import { useToast } from './use-toast';
import { useFeatureFlag } from '@/context/ConfigContext';
import { createLogger } from '../utils/logger';

interface SyncEvent {
  eventType:
    | 'file_changed'
    | 'graph_updated'
    | 'validation_completed'
    | 'agent_triggered'
    | 'sync_error'
    | 'sync_started'
    | 'sync_completed'
    | 'cli.progress'
    | 'cli.done'
    | 'graph.updated'
    | 'permagraph.synced';
  timestamp: string;
  projectId: string;
  data: any;
  source?: string;
  correlationId?: string;
}

interface SyncMetrics {
  totalSyncs: number;
  successfulSyncs: number;
  failedSyncs: number;
  averageSyncTime: number;
  lastSyncTime?: string;
  filesProcessed: number;
  triplesUpdated: number;
  violationsDetected: number;
}

interface RealtimeSyncState {
  isConnected: boolean;
  isConnecting: boolean;
  lastEvent: SyncEvent | null;
  metrics: SyncMetrics | null;
  connectedClients: number;
  events: SyncEvent[];
  error: string | null;
}

interface UseRealtimeSyncOptions {
  projectId: string;
  autoConnect?: boolean;
  maxEvents?: number;
  subscriptions?: string[];
  onEvent?: (event: SyncEvent) => void;
  onMetricsUpdate?: (metrics: SyncMetrics) => void;
  onConnectionChange?: (connected: boolean) => void;
}

/**
 * @kthulu:extend - Real-time synchronization hook for Kthulu-PermaGraph integration
 * Provides WebSocket connection for real-time sync events and metrics
 */
export function useRealtimeSync({
  projectId,
  autoConnect = true,
  maxEvents = 100,
  subscriptions = ['*'],
  onEvent,
  onMetricsUpdate,
  onConnectionChange,
}: UseRealtimeSyncOptions) {
  const { toast } = useToast();
  const cliStreamingEnabled = useFeatureFlag('cliStreaming');
  const logger = createLogger('useRealtimeSync');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);

  interface OutgoingMessage {
    type: string;
    [key: string]: any;
  }

  // Queue messages while the socket is disconnected and flush on reconnect
  const messageQueueRef = useRef<OutgoingMessage[]>([]);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000;

  const [state, setState] = useState<RealtimeSyncState>({
    isConnected: false,
    isConnecting: false,
    lastEvent: null,
    metrics: null,
    connectedClients: 0,
    events: [],
    error: null,
  });

  const addEvent = useCallback(
    (event: SyncEvent) => {
      setState((prev) => ({
        ...prev,
        lastEvent: event,
        events: [event, ...prev.events.slice(0, maxEvents - 1)],
      }));

      // Call external event handler
      onEvent?.(event);
    },
    [maxEvents, onEvent]
  );

  const updateMetrics = useCallback(
    (metrics: SyncMetrics) => {
      setState((prev) => ({ ...prev, metrics }));
      onMetricsUpdate?.(metrics);
    },
    [onMetricsUpdate]
  );

  const setConnectionState = useCallback(
    (connected: boolean, connecting: boolean = false) => {
      setState((prev) => ({
        ...prev,
        isConnected: connected,
        isConnecting: connecting,
        error: connected ? null : prev.error,
      }));

      onConnectionChange?.(connected);
    },
    [onConnectionChange]
  );

  const flushQueue = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      while (messageQueueRef.current.length > 0) {
        wsRef.current.send(JSON.stringify(messageQueueRef.current.shift()));
      }
    }
  }, []);

  const queueMessage = useCallback((msg: OutgoingMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    } else {
      messageQueueRef.current.push(msg);
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionState(false, true);

    try {
      const wsUrl = `ws://localhost:8081?projectId=${encodeURIComponent(projectId)}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        logger.info('Connected to real-time sync', { projectId });
        setConnectionState(true, false);
        reconnectAttempts.current = 0;

        // Subscribe to events
        if (subscriptions.length > 0) {
          queueMessage({
            type: 'subscribe',
            eventTypes: subscriptions,
          });
        }

        // Request initial metrics
        queueMessage({
          type: 'get_metrics',
          projectId,
        });

        flushQueue();

        // Start heartbeat
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (
            (message.type === 'cli.progress' || message.type === 'cli.done') &&
            !cliStreamingEnabled
          ) {
            return;
          }

          switch (message.type) {
            case 'connection_established':
              updateMetrics(message.data.metrics);
              setState((prev) => ({
                ...prev,
                connectedClients: message.data.connectedClients || 0,
              }));
              break;

            case 'sync_event':
              addEvent({
                eventType: message.eventType,
                timestamp: message.data.timestamp,
                projectId: message.data.projectId,
                data: message.data,
                source: message.data.source,
                correlationId: message.data.correlationId,
              });

              // Show toast notifications for important events
              if (message.eventType === 'sync_completed') {
                if (message.data.success) {
                  toast({
                    title: 'Sync Completed',
                    description: `Processed ${message.data.filesProcessed} files in ${message.data.duration.toFixed(2)}s`,
                  });
                } else {
                  toast({
                    title: 'Sync Failed',
                    description: 'Synchronization encountered errors',
                    variant: 'destructive',
                  });
                }
              } else if (message.eventType === 'validation_completed') {
                if (
                  !message.data.isConsistent &&
                  message.data.violationCount > 0
                ) {
                  toast({
                    title: 'Validation Issues',
                    description: `Found ${message.data.violationCount} architectural violations`,
                    variant: 'destructive',
                  });
                }
              } else if (message.eventType === 'sync_error') {
                toast({
                  title: 'Sync Error',
                  description: message.data.error,
                  variant: 'destructive',
                });
              }
              break;

            case 'metrics_update':
            case 'metrics_broadcast':
              updateMetrics(message.data.metrics);
              setState((prev) => ({
                ...prev,
                connectedClients: message.data.connectedClients || 0,
              }));
              break;

            case 'subscription_confirmed':
              console.log(
                `📝 Subscribed to events: ${message.data.eventTypes.join(', ')}`
              );
              break;

            case 'force_sync_initiated':
              toast({
                title: 'Force Sync Started',
                description: 'Manual synchronization initiated',
              });
              break;

            case 'pong':
              // Heartbeat response
              break;

            case 'graph_events':
              if (Array.isArray(message.events)) {
                for (const evt of message.events) {
                  const aggregated: any = {
                    nodes: [],
                    edges: [],
                    totalChanges: 1,
                  };
                  switch (evt.event_type) {
                    case 'NODE_ADDED':
                    case 'NODE_UPDATED':
                      aggregated.nodes.push(evt.data);
                      break;
                    case 'EDGE_ADDED':
                    case 'EDGE_UPDATED':
                      aggregated.edges.push(evt.data);
                      break;
                  }

                  addEvent({
                    eventType: 'graph.updated',
                    timestamp: evt.timestamp || new Date().toISOString(),
                    projectId: evt.kg_id || message.projectId || projectId,
                    data: aggregated,
                  });
                }
              }
              break;

            case 'cli.progress':
            case 'cli.done':
            case 'graph.updated':
            case 'permagraph.synced':
              addEvent({
                eventType: message.type,
                timestamp: message.timestamp,
                projectId: message.projectId,
                data: message.data,
              });
              break;

            default:
              console.log('📨 Received message:', message);
          }
        } catch (error) {
          console.error('❌ Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = (event) => {
        console.log(
          `🔌 Disconnected from real-time sync: ${event.code} ${event.reason}`
        );
        setConnectionState(false, false);

        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }

        // Attempt reconnection if not a clean close
        if (
          event.code !== 1000 &&
          reconnectAttempts.current < maxReconnectAttempts
        ) {
          const delay = reconnectDelay * Math.pow(2, reconnectAttempts.current);
          console.log(
            `🔄 Attempting reconnection in ${delay}ms (attempt ${reconnectAttempts.current + 1}/${maxReconnectAttempts})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setState((prev) => ({
            ...prev,
            error: 'Failed to reconnect after multiple attempts',
          }));

          toast({
            title: 'Connection Lost',
            description: 'Unable to reconnect to real-time sync service',
            variant: 'destructive',
          });
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        setState((prev) => ({
          ...prev,
          error: 'WebSocket connection error',
        }));
      };
    } catch (error) {
      console.error('❌ Error creating WebSocket connection:', error);
      setConnectionState(false, false);
      setState((prev) => ({
        ...prev,
        error: 'Failed to create WebSocket connection',
      }));
    }
  }, [
    projectId,
    subscriptions,
    addEvent,
    updateMetrics,
    setConnectionState,
    queueMessage,
    flushQueue,
    toast,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }

    setConnectionState(false, false);
    messageQueueRef.current = [];
  }, [setConnectionState]);

  const subscribe = useCallback(
    (eventTypes: string[]) => {
      queueMessage({
        type: 'subscribe',
        eventTypes,
      });
    },
    [queueMessage]
  );

  const unsubscribe = useCallback(
    (eventTypes: string[]) => {
      queueMessage({
        type: 'unsubscribe',
        eventTypes,
      });
    },
    [queueMessage]
  );

  const forceSync = useCallback(() => {
    queueMessage({
      type: 'force_sync',
      projectId,
    });
  }, [projectId, queueMessage]);

  const requestMetrics = useCallback(() => {
    queueMessage({
      type: 'get_metrics',
      projectId,
    });
  }, [projectId, queueMessage]);

  const clearEvents = useCallback(() => {
    setState((prev) => ({
      ...prev,
      events: [],
      lastEvent: null,
    }));
  }, []);

  const getEventsByType = useCallback(
    (eventType: string) => {
      return state.events.filter((event) => event.eventType === eventType);
    },
    [state.events]
  );

  const getRecentEvents = useCallback(
    (count: number = 10) => {
      return state.events.slice(0, count);
    },
    [state.events]
  );

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect && projectId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [projectId, autoConnect]); // Note: connect and disconnect are not in deps to avoid reconnection loops

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  return {
    // Connection state
    isConnected: state.isConnected,
    isConnecting: state.isConnecting,
    error: state.error,

    // Events and metrics
    lastEvent: state.lastEvent,
    events: state.events,
    metrics: state.metrics,
    connectedClients: state.connectedClients,

    // Connection control
    connect,
    disconnect,

    // Subscription management
    subscribe,
    unsubscribe,

    // Actions
    forceSync,
    requestMetrics,
    clearEvents,

    // Utilities
    getEventsByType,
    getRecentEvents,

    // Computed properties
    successRate: state.metrics
      ? state.metrics.totalSyncs > 0
        ? (state.metrics.successfulSyncs / state.metrics.totalSyncs) * 100
        : 100
      : 0,
    isHealthy: state.isConnected && !state.error,
    hasRecentActivity: state.lastEvent
      ? new Date().getTime() - new Date(state.lastEvent.timestamp).getTime() <
        300000
      : false, // 5 minutes
  };
}

// Convenience hooks for specific event types
export function useRealtimeSyncEvents(
  projectId: string,
  eventTypes: string[] = ['*']
) {
  return useRealtimeSync({
    projectId,
    subscriptions: eventTypes,
    maxEvents: 50,
  });
}

export function useRealtimeSyncMetrics(projectId: string) {
  const [metrics, setMetrics] = useState<SyncMetrics | null>(null);

  const { isConnected, metrics: hookMetrics } = useRealtimeSync({
    projectId,
    subscriptions: ['sync_completed', 'validation_completed', 'metrics_update'],
    onMetricsUpdate: setMetrics,
  });

  return { isConnected, metrics: hookMetrics };
}

export function useRealtimeSyncStatus(projectId: string) {
  const { isConnected, isConnecting, error, lastEvent, metrics } =
    useRealtimeSync({
      projectId,
      subscriptions: ['sync_started', 'sync_completed', 'sync_error'],
      maxEvents: 20,
    });

  const isSyncing =
    lastEvent?.eventType === 'sync_started' &&
    (!metrics ||
      new Date().getTime() - new Date(lastEvent.timestamp).getTime() < 30000);

  return {
    isConnected,
    isConnecting,
    isSyncing,
    error,
    lastSyncTime: metrics?.lastSyncTime,
    successRate: metrics
      ? metrics.totalSyncs > 0
        ? (metrics.successfulSyncs / metrics.totalSyncs) * 100
        : 100
      : 0,
  };
}
