import { useState, useCallback } from 'react';
import { connectorService } from '../services/connectorService';
import type { GraphData } from '../types/graph';

export interface ConnectorStatus {
  initialized: boolean;
  isLoading: boolean;
  error: string | null;
  lastAction: Date | null;
}

export function useConnector(projectId: string) {
  const [status, setStatus] = useState<ConnectorStatus>({
    initialized: false,
    isLoading: false,
    error: null,
    lastAction: null,
  });

  const [graph, setGraph] = useState<GraphData | null>(null);

  const initConnector = useCallback(
    async (projectPath: string, templateId: string) => {
      setStatus((prev) => ({ ...prev, isLoading: true, error: null }));
      try {
        const result = await connectorService.init(
          projectId,
          projectPath,
          templateId
        );
        setStatus({
          initialized: true,
          isLoading: false,
          error: null,
          lastAction: new Date(),
        });
        return result;
      } catch (error: any) {
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

  const executeCommand = useCallback(
    async (command: string, args: string[] = []) => {
      setStatus((prev) => ({ ...prev, isLoading: true, error: null }));
      try {
        const result = await connectorService.execute(projectId, command, args);
        setStatus((prev) => ({
          ...prev,
          isLoading: false,
          lastAction: new Date(),
        }));
        return result;
      } catch (error: any) {
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

  const generateGraph = useCallback(async () => {
    setStatus((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await connectorService.graph(projectId);
      setGraph(result.data);
      setStatus((prev) => ({
        ...prev,
        isLoading: false,
        lastAction: new Date(),
      }));
      return result;
    } catch (error: any) {
      setStatus((prev) => ({
        ...prev,
        isLoading: false,
        error: error.message,
      }));
      throw error;
    }
  }, [projectId]);

  const validateArchitecture = useCallback(async () => {
    setStatus((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await connectorService.validate(projectId);
      setStatus((prev) => ({
        ...prev,
        isLoading: false,
        lastAction: new Date(),
      }));
      return result;
    } catch (error: any) {
      setStatus((prev) => ({
        ...prev,
        isLoading: false,
        error: error.message,
      }));
      throw error;
    }
  }, [projectId]);

  return {
    status,
    graph,
    initConnector,
    executeCommand,
    generateGraph,
    validateArchitecture,
  };
}

export default useConnector;
