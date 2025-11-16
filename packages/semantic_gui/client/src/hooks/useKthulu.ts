import { useState, useEffect, useCallback } from 'react';
import { kthuluService } from '../services/kthuluService';
import { useWebSocket } from './useWebSocket';
import { useGraphRefresh } from './use-graph';
import { createLogger } from '../utils/logger';

export interface KthuluProject {
  path: string;
  name: string;
  modules: KthuluModule[];
  dependencies: KthuluDependency[];
}

export interface KthuluModule {
  name: string;
  path: string;
  useCases: string[];
  adapters: string[];
  entities: string[];
  ports: string[];
}

export interface KthuluDependency {
  source: string;
  target: string;
  type: 'depends' | 'calls' | 'implements' | 'uses';
}

export interface KthuluStatus {
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  lastSync: Date | null;
}

export function useKthulu(projectId: string) {
  const [status, setStatus] = useState<KthuluStatus>({
    isConnected: false,
    isLoading: false,
    error: null,
    lastSync: null,
  });

  const [project, setProject] = useState<KthuluProject | null>(null);
  const [availableCommands, setAvailableCommands] = useState<any[]>([]);

  // WebSocket for real-time updates
  const { lastMessage, sendMessage } = useWebSocket<Record<string, any>>();
  const { mutateAsync: refreshGraph } = useGraphRefresh();
  const logger = createLogger('useKthulu');

  // Handle WebSocket messages
  useEffect(() => {
    if (
      lastMessage?.type === 'kthulu-event' &&
      lastMessage.projectId === projectId
    ) {
      const { eventType, data } = lastMessage.data;

      switch (eventType) {
        case 'code-changed':
          handleCodeChange(data);
          break;
        case 'validation-result':
          handleValidationResult(data);
          break;
        case 'graph-updated':
        case 'graph.updated':
          handleGraphUpdate(data);
          break;
        case 'graph_events':
          handleGraphEvents(data?.events ?? []);
          break;
      }
    }
  }, [lastMessage, projectId]);

  const handleCodeChange = useCallback((data: any) => {
    logger.debug('Kthulu code changed', { projectId, changeType: data?.type });
    setStatus((prev) => ({ ...prev, lastSync: new Date() }));
  }, [logger, projectId]);

  const handleValidationResult = useCallback((data: any) => {
    logger.info('Kthulu validation result received', { 
      projectId, 
      isValid: data?.isValid,
      errorCount: data?.errors?.length || 0 
    });
  }, [logger, projectId]);

  const handleGraphUpdate = useCallback((data: any) => {
    logger.debug('Kthulu graph updated', { 
      projectId, 
      nodeCount: data?.nodes?.length || 0,
      edgeCount: data?.edges?.length || 0 
    });
  }, [logger, projectId]);

  const handleGraphEvents = useCallback(
    (events: any[]) => {
      const aggregated = events.reduce(
        (
          acc: { nodes: any[]; edges: any[]; totalChanges: number },
          evt: any
        ) => {
          switch (evt.event_type) {
            case 'NODE_ADDED':
            case 'NODE_UPDATED':
              acc.nodes.push(evt.data);
              break;
            case 'EDGE_ADDED':
            case 'EDGE_UPDATED':
              acc.edges.push(evt.data);
              break;
          }
          acc.totalChanges += 1;
          return acc;
        },
        { nodes: [], edges: [], totalChanges: 0 }
      );
      handleGraphUpdate(aggregated);
    },
    [handleGraphUpdate]
  );

  // Initialize Kthulu connection
  const initializeKthulu = useCallback(
    async (kthuluPath: string) => {
      setStatus((prev) => ({ ...prev, isLoading: true, error: null }));

      try {
        await kthuluService.initialize(projectId, kthuluPath);
        setStatus((prev) => ({
          ...prev,
          isConnected: true,
          isLoading: false,
          lastSync: new Date(),
        }));

        // Subscribe to WebSocket updates
        sendMessage({
          type: 'subscribe',
          projectId,
          data: {},
          timestamp: new Date().toISOString(),
        });

        // Load available commands
        const commands = await kthuluService.getCommands(projectId);
        setAvailableCommands(commands);
      } catch (error) {
        setStatus((prev) => ({
          ...prev,
          isLoading: false,
          error: error.message,
          isConnected: false,
        }));
      }
    },
    [projectId, sendMessage]
  );

  // Execute Kthulu CLI command
  const executeCommand = useCallback(
    async (command: string, args: string[] = []) => {
      setStatus((prev) => ({ ...prev, isLoading: true, error: null }));

      try {
        const result = await kthuluService.executeCommand(
          projectId,
          command,
          args
        );
        setStatus((prev) => ({
          ...prev,
          isLoading: false,
          lastSync: new Date(),
        }));
        return result;
      } catch (error) {
        setStatus((prev) => ({
          ...prev,
          isLoading: false,
          error: error.message,
        }));
        throw error;
      }
    },
    [projectId]
  );

  // Import architecture graph
  const importGraph = useCallback(async () => {
    setStatus((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const result = await kthuluService.importGraph(projectId);
      setStatus((prev) => ({
        ...prev,
        isLoading: false,
        lastSync: new Date(),
      }));
      return result;
    } catch (error) {
      setStatus((prev) => ({
        ...prev,
        isLoading: false,
        error: error.message,
      }));
      throw error;
    }
  }, [projectId]);

  // Validate architecture
  const validateArchitecture = useCallback(async () => {
    setStatus((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const result = await kthuluService.validate(projectId);
      setStatus((prev) => ({
        ...prev,
        isLoading: false,
        lastSync: new Date(),
      }));
      return result;
    } catch (error) {
      setStatus((prev) => ({
        ...prev,
        isLoading: false,
        error: error.message,
      }));
      throw error;
    }
  }, [projectId]);

  // Analyze project structure
  const analyzeProject = useCallback(async () => {
    setStatus((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const result = await kthuluService.analyzeProject(projectId);
      setProject(result.project);
      setStatus((prev) => ({
        ...prev,
        isLoading: false,
        lastSync: new Date(),
      }));
      return result;
    } catch (error) {
      setStatus((prev) => ({
        ...prev,
        isLoading: false,
        error: error.message,
      }));
      throw error;
    }
  }, [projectId]);

  // Apply code changes
  const applyChanges = useCallback(
    async (changes: any[]) => {
      setStatus((prev) => ({ ...prev, isLoading: true, error: null }));

      try {
        const result = await kthuluService.applyChanges(projectId, changes);
        await refreshGraph(projectId);
        setStatus((prev) => ({
          ...prev,
          isLoading: false,
          lastSync: new Date(),
        }));
        return result;
      } catch (error) {
        setStatus((prev) => ({
          ...prev,
          isLoading: false,
          error: error.message,
        }));
        throw error;
      }
    },
    [projectId, refreshGraph]
  );

  // Disconnect from Kthulu
  const disconnect = useCallback(async () => {
    try {
      await kthuluService.disconnect(projectId);
      setStatus({
        isConnected: false,
        isLoading: false,
        error: null,
        lastSync: null,
      });
      setProject(null);
      setAvailableCommands([]);

      // Unsubscribe from WebSocket
      sendMessage({
        type: 'unsubscribe',
        projectId,
        data: {},
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      logger.error('Failed to disconnect from Kthulu', error instanceof Error ? error : new Error(String(error)), { projectId });
    }
  }, [projectId, sendMessage]);

  // Check status on mount
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const statusResult = await kthuluService.getStatus(projectId);
        setStatus((prev) => ({
          ...prev,
          isConnected: statusResult.isConnected,
        }));

        if (statusResult.isConnected) {
          const commands = await kthuluService.getCommands(projectId);
          setAvailableCommands(commands);
          sendMessage({
            type: 'subscribe',
            projectId,
            data: {},
            timestamp: new Date().toISOString(),
          });
        }
      } catch (error) {
        logger.error('Failed to check Kthulu status', error instanceof Error ? error : new Error(String(error)), { projectId });
      }
    };

    checkStatus();
  }, [projectId, sendMessage]);

  return {
    status,
    project,
    availableCommands,
    initializeKthulu,
    executeCommand,
    importGraph,
    validateArchitecture,
    analyzeProject,
    applyChanges,
    disconnect,
  };
}
