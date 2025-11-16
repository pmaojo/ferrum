import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { createLogger } from '../utils/logger';

export interface Violation {
  id?: string;
  message?: string;
  [key: string]: unknown;
}

export interface SyncSummary {
  triplesAdded?: number;
  violations?: Violation[];
}

export interface AgentStatusInfo {
  status?: string;
  healthy?: boolean;
  lastHeartbeat?: string;
}

export interface PermaGraphMessage extends SyncSummary {
  event: string;
  projectId?: string;
  agentId?: string;
  queryId?: string;
  agent?: AgentStatusInfo;
  status?: string;
  lastHeartbeat?: string;
  healthy?: boolean;
  timestamp?: string;
  stats?: unknown;
  [key: string]: unknown;
}

/**
 * @kthulu:extend - WebSocket hook for real-time PermaGraph updates
 * Handles ontology updates, agent status changes, and validation results
 */
export function usePermaGraphWebSocket(projectId: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<PermaGraphMessage | null>(null);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [syncSummary, setSyncSummary] = useState<SyncSummary | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();
  const logger = createLogger('usePermaGraphWebSocket');

  useEffect(() => {
    if (!projectId) return;

    // Create WebSocket connection directly to PermaGraph
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/permagraph/ws?projectId=${projectId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      logger.info('PermaGraph WebSocket connected', { projectId, wsUrl });
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const message: PermaGraphMessage = JSON.parse(event.data);
        if (message.projectId && message.projectId !== projectId) {
          return;
        }
        setLastMessage(message);
        handlePermaGraphEvent(message);
      } catch (error) {
        logger.error('Failed to parse PermaGraph WebSocket message', error instanceof Error ? error : new Error(String(error)), {
          rawData: event.data,
          projectId
        });
      }
    };

    ws.onclose = () => {
      logger.info('PermaGraph WebSocket disconnected', { projectId });
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      logger.error('PermaGraph WebSocket error occurred', error instanceof Error ? error : new Error('WebSocket error'), {
        projectId
      });
      setIsConnected(false);
    };

    // Cleanup on unmount
    return () => {
      ws.close();
    };
  }, [projectId]);

  const handlePermaGraphEvent = (event: PermaGraphMessage) => {
    logger.debug('PermaGraph event received', { eventType: event.event, projectId });

    switch (event.event) {
      case 'ontology-loaded':
        // Invalidate metrics and graph
        queryClient.invalidateQueries({
          queryKey: [`/api/v1/projects/${projectId}/permagraph/metrics`],
        });
        queryClient.invalidateQueries({
          queryKey: [`/api/v1/projects/${projectId}/graph`],
        });
        break;

      case 'ontology-updated':
        // Invalidate ontology-related queries
        queryClient.invalidateQueries({
          queryKey: [`/api/v1/projects/${projectId}/permagraph/metrics`],
        });
        queryClient.invalidateQueries({
          queryKey: [`/api/v1/projects/${projectId}/graph`],
        });
        break;

      case 'agent-started':
      case 'agent-stopped':
      case 'agents.status':
        // Invalidate agent queries
        queryClient.invalidateQueries({
          queryKey: ['/api/v1/agents', projectId],
        });
        queryClient.invalidateQueries({
          queryKey: ['/api/v1/status', projectId],
        });
        break;

      case 'synced':
        // Refresh overall PermaGraph status after sync
        queryClient.invalidateQueries({
          queryKey: ['/api/v1/status', projectId],
        });
        break;
      case 'permagraph.synced':
        handlePermagraphSynced(event);
        break;

      case 'validation-completed':
        // Invalidate validation queries
        queryClient.invalidateQueries({
          queryKey: ['/api/v1/validation', projectId],
        });
        // Could also show a toast notification here
        break;

      case 'violation-found':
        setViolations((prev) => [...prev, event as Violation]);
        break;

      case 'sparql-result':
        // Handle SPARQL query results if needed
        logger.debug('SPARQL query completed', { queryId: event.queryId, projectId });
        break;

      default:
        logger.warn('Unknown PermaGraph event type received', { eventType: event.event, projectId });
    }
  };

  const handlePermagraphSynced = (summary: SyncSummary) => {
    logger.info('PermaGraph sync completed', {
      triplesAdded: summary.triplesAdded,
      violationsCount: summary.violations?.length || 0,
      projectId
    });
    setSyncSummary(summary);
    queryClient.invalidateQueries({
      queryKey: ['/api/v1/status', projectId],
    });
    if (Array.isArray(summary?.violations)) {
      setViolations(summary.violations);
    }
  };

  const sendMessage = (message: PermaGraphMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  };

  return {
    isConnected,
    lastMessage,
    sendMessage,
    violations,
    syncSummary,
  };
}

/**
 * Hook for listening to specific PermaGraph events
 */
export function usePermaGraphEventListener(
  projectId: string,
  eventType: string,
  callback: (data: PermaGraphMessage) => void
) {
  const { lastMessage } = usePermaGraphWebSocket(projectId);

  useEffect(() => {
    if (
      lastMessage &&
      lastMessage.event === eventType &&
      (!lastMessage.projectId || lastMessage.projectId === projectId)
    ) {
      callback(lastMessage);
    }
  }, [lastMessage, projectId, eventType, callback]);
}

/**
 * Hook for real-time agent status updates
 */
export function usePermaGraphAgentStatus(projectId: string) {
  const [agentStatuses, setAgentStatuses] = useState<
    Record<string, AgentStatusInfo>
  >({});

  usePermaGraphEventListener(projectId, 'agents.status', (data) => {
    if (data.agentId) {
      setAgentStatuses((prev) => ({
        ...prev,
        [data.agentId]: {
          ...(prev[data.agentId] || {}),
          status: data.agent?.status || data.status,
          lastHeartbeat:
            data.agent?.lastHeartbeat ||
            data.lastHeartbeat ||
            prev[data.agentId]?.lastHeartbeat,
        },
      }));
    }
  });

  usePermaGraphEventListener(projectId, 'agent-heartbeat', (data) => {
    if (data.agentId) {
      setAgentStatuses((prev) => ({
        ...prev,
        [data.agentId]: {
          ...(prev[data.agentId] || {}),
          healthy: data.healthy,
          lastHeartbeat: data.timestamp || new Date().toISOString(),
        },
      }));
    }
  });

  return agentStatuses;
}

/**
 * Hook for real-time ontology statistics
 */
export function usePermaGraphOntologyStats(projectId: string) {
  const [stats, setStats] = useState<any>(null);

  usePermaGraphEventListener(projectId, 'ontology-updated', (data) => {
    // Trigger a refetch of stats or update local state
    setStats(data.stats);
  });

  return stats;
}
