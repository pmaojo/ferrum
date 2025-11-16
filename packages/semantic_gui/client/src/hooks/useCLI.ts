import { useState, useCallback } from 'react';
import { useTemplate } from '@/context/TemplateContext';
import { useToast } from '@/hooks/use-toast';

interface CLIOperationResult {
  success: boolean;
  output: string;
  error?: string;
}

interface UseCLIReturn {
  executeOperation: (
    operation: string,
    args?: Record<string, any>
  ) => Promise<CLIOperationResult>;
  isExecuting: boolean;
  lastResult: CLIOperationResult | null;
  availableOperations: string[];
}

export function useCLI(projectId: string): UseCLIReturn {
  const { currentTemplate, cliCommands } = useTemplate();
  const { toast } = useToast();

  const [isExecuting, setIsExecuting] = useState(false);
  const [lastResult, setLastResult] = useState<CLIOperationResult | null>(null);

  const availableOperations = Object.keys(cliCommands);

  const executeOperation = useCallback(
    async (
      operation: string,
      args?: Record<string, any>
    ): Promise<CLIOperationResult> => {
      if (!currentTemplate || !projectId) {
        const error = 'No template or project selected';
        toast({
          title: 'Error',
          description: error,
          variant: 'destructive',
        });
        return { success: false, output: '', error };
      }

      if (!cliCommands[operation]) {
        const error = `Operation "${operation}" not available in template`;
        toast({
          title: 'Error',
          description: error,
          variant: 'destructive',
        });
        return { success: false, output: '', error };
      }

      setIsExecuting(true);

      try {
        const traceId = crypto.randomUUID();
        const response = await fetch(
          `/api/v1/projects/${projectId}/cli/execute`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'x-trace-id': traceId,
            },
            body: JSON.stringify({ operation, args }),
          }
        );

        if (!response.ok) {
          const errorData = await response
            .json()
            .catch(() => ({ error: response.statusText }));
          throw new Error(errorData.error || `HTTP ${response.status}`);
        }

        const data = await response.json();

        const result: CLIOperationResult = {
          success: data.exitCode === 0,
          output: data.stdout || '',
          error: data.exitCode === 0 ? undefined : data.stderr || 'CLI error',
        };

        setLastResult(result);

        toast({
          title: 'Operation Completed',
          description: `${operation} executed successfully`,
        });

        return result;
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : 'Unknown error';

        const result: CLIOperationResult = {
          success: false,
          output: '',
          error: errorMessage,
        };

        setLastResult(result);

        toast({
          title: 'Operation Failed',
          description: errorMessage,
          variant: 'destructive',
        });

        return result;
      } finally {
        setIsExecuting(false);
      }
    },
    [currentTemplate, projectId, cliCommands, toast]
  );

  return {
    executeOperation,
    isExecuting,
    lastResult,
    availableOperations,
  };
}

// Specific hooks for common operations
export function usePlanGraph(projectId: string) {
  const { executeOperation, isExecuting } = useCLI(projectId);

  const planGraph = useCallback(async () => {
    return executeOperation('planGraph');
  }, [executeOperation]);

  return { planGraph, isPlanning: isExecuting };
}

export function useValidateArchitecture(projectId: string) {
  const { executeOperation, isExecuting } = useCLI(projectId);

  const validate = useCallback(async () => {
    return executeOperation('validate');
  }, [executeOperation]);

  return { validate, isValidating: isExecuting };
}
