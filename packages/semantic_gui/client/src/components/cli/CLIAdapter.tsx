import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { useTemplate } from '@/context/TemplateContext';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ApprovalDialog, type FileDiff } from '@/components/diff';
import { 
  Terminal,
  Play,
  CheckCircle,
  AlertCircle,
  Loader2,
  FileText,
  Zap,
} from 'lucide-react';
import { useCLIOperations, type CLIOperation } from '@/hooks/useCLIOperations';
import { useProject } from '@/hooks/use-graph';

interface CLIAdapterProps {
  projectId: string;
  className?: string;
}

export function CLIAdapter({ projectId, className }: CLIAdapterProps) {
  const { currentTemplate, cliCommands, isLoading } = useTemplate();
  const { operations, isLoading: opsLoading } = useCLIOperations(projectId);
  const { data: project } = useProject(projectId);
  const { toast } = useToast();
  const { lastMessage } = useWebSocket<string>();

  const [activeOperation, setActiveOperation] = useState<string | null>(null);
  const [operationResults, setOperationResults] = useState<
    Record<string, string>
  >({});
  const [operationStatus, setOperationStatus] = useState<
    Record<string, 'idle' | 'running' | 'success' | 'error'>
  >({});
  const [currentTraceId, setCurrentTraceId] = useState<string | null>(null);
  const [pendingDiffs, setPendingDiffs] = useState<FileDiff[]>([]);
  const [approvalOpen, setApprovalOpen] = useState(false);
  const [pendingOperation, setPendingOperation] = useState<{ key: string; args?: Record<string, any>; } | null>(null);

  const projectConfig = project?.metadata?.config || {};

  const requiresInput = (op: CLIOperation) => {
    const props = op.argsSchema?.properties;
    if (!props) return false;
    return Object.entries<any>(props).some(([key, v]) => {
      if ('const' in v) return false;
      return projectConfig[key] === undefined;
    });
  };

  const iconMap: Record<string, React.ReactNode> = {
    planGraph: <FileText className="h-4 w-4" />,
    validate: <CheckCircle className="h-4 w-4" />,
  };

  const availableOperations = operations
    .filter((op) => !requiresInput(op))
    .map((op) => ({
      ...op,
      icon: iconMap[op.key] ?? <Terminal className="h-4 w-4" />,
    }));

  const previewOperation = async (
    operationKey: string,
    args?: Record<string, any>
  ) => {
    if (!currentTemplate || !projectId) {
      toast({
        title: 'Error',
        description: 'No template or project selected',
        variant: 'destructive',
      });
      return;
    }

    const traceId = crypto.randomUUID();
    setActiveOperation(operationKey);
    setCurrentTraceId(traceId);
    setOperationStatus((prev) => ({ ...prev, [operationKey]: 'running' }));

    try {
      const response = await fetch(`/api/projects/${projectId}/cli/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-trace-id': traceId,
        },
        body: JSON.stringify({ operation: operationKey, args, applyMode: 'diff' }),
      });

      if (!response.ok) {
        throw new Error(`CLI operation failed: ${response.statusText}`);
      }
      const diffs: FileDiff[] = await response.json();
      setPendingDiffs(diffs);
      setApprovalOpen(true);
      setPendingOperation({ key: operationKey, args });
      setOperationStatus((prev) => ({ ...prev, [operationKey]: 'idle' }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setOperationStatus((prev) => ({ ...prev, [operationKey]: 'error' }));
      toast({
        title: 'Operation Failed',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setActiveOperation(null);
      setCurrentTraceId(null);
    }
  };

  const executeOperation = async (
    operationKey: string,
    args?: Record<string, any>,
    applyMode: 'write' | 'pr' = 'write'
  ) => {
    if (!currentTemplate || !projectId) {
      toast({
        title: 'Error',
        description: 'No template or project selected',
        variant: 'destructive',
      });
      return;
    }

    const traceId = crypto.randomUUID();
    setActiveOperation(operationKey);
    setCurrentTraceId(traceId);
    setOperationStatus((prev) => ({ ...prev, [operationKey]: 'running' }));
    setOperationResults((prev) => ({ ...prev, [operationKey]: '' }));

    try {
      const response = await fetch(`/api/projects/${projectId}/cli/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-trace-id': traceId,
        },
        body: JSON.stringify({ operation: operationKey, args, applyMode }),
      });

      if (!response.ok) {
        throw new Error(`CLI operation failed: ${response.statusText}`);
      }
      const result = await response.json();

      setOperationStatus((prev) => ({
        ...prev,
        [operationKey]: result.exitCode === 0 ? 'success' : 'error',
      }));

      if (result.exitCode === 0) {
        toast({
          title: 'Operation Completed',
          description: `${operationKey} executed successfully`,
        });
      } else {
        toast({
          title: 'Operation Failed',
          description: result.stderr || 'CLI error',
          variant: 'destructive',
        });
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error';
      setOperationStatus((prev) => ({ ...prev, [operationKey]: 'error' }));

      toast({
        title: 'Operation Failed',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setActiveOperation(null);
      setCurrentTraceId(null);
    }
  };

  const cancelOperation = async () => {
    if (!currentTraceId) return;
    try {
      await fetch(`/api/projects/${projectId}/cli/cancel`, {
        method: 'POST',
        headers: { 'x-trace-id': currentTraceId },
      });
    } catch (error) {
      console.error('Failed to cancel CLI operation', error);
    }
  };

  useEffect(() => {
    if (
      lastMessage?.type === 'cli.progress' &&
      lastMessage.projectId === projectId &&
      activeOperation
    ) {
      setOperationResults((prev) => ({
        ...prev,
        [activeOperation]: (prev[activeOperation] || '') + lastMessage.data,
      }));
    }
  }, [lastMessage, projectId, activeOperation]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  if (isLoading || opsLoading) {
    return (
      <Card className={className}>
        <CardContent className="p-6 text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">
            Loading CLI adapter...
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!currentTemplate || availableOperations.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="p-6 text-center">
          <Terminal className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            No CLI operations available for this template
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Terminal className="h-5 w-5" />
            <span>CLI Operations</span>
            <Badge variant="outline" className="text-xs">
              {currentTemplate.name}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
        {/* Available Operations */}
        <div className="grid gap-2">
          {availableOperations.map((operation) => {
            const status = operationStatus[operation.key] || 'idle';
            const isRunning = activeOperation === operation.key;

            return (
              <div
                key={operation.key}
                className="flex items-center justify-between p-3 border rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  {operation.icon}
                  <div>
                    <div className="font-medium text-sm">{operation.label}</div>
                    <div className="text-xs text-muted-foreground">
                      {operation.description}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  {getStatusIcon(status)}
                  {isRunning ? (
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={cancelOperation}
                    >
                      Cancel
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      onClick={() => previewOperation(operation.key)}
                      disabled={!!activeOperation || !projectId}
                      variant={status === 'success' ? 'outline' : 'default'}
                    >
                      <>
                        <Play className="h-3 w-3 mr-1" />
                        Execute
                      </>
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Operation Results */}
        {Object.entries(operationResults).map(([operationKey, result]) => (
          <div key={operationKey} className="space-y-2">
            <div className="flex items-center space-x-2">
              <Terminal className="h-4 w-4" />
              <span className="font-medium text-sm">
                {
                  availableOperations.find((op) => op.key === operationKey)
                    ?.label
                }{' '}
                Result:
              </span>
              {getStatusIcon(operationStatus[operationKey])}
            </div>
            <Textarea
              value={result}
              readOnly
              className="font-mono text-xs min-h-20 bg-muted/50"
              placeholder="Operation output will appear here..."
            />
          </div>
        ))}

        {/* Template CLI Info */}
        <div className="pt-4 border-t">
          <div className="flex items-center space-x-2 mb-2">
            <Zap className="h-4 w-4" />
            <span className="font-medium text-sm">Available Commands:</span>
          </div>
          <div className="text-xs text-muted-foreground space-y-1">
            {Object.keys(cliCommands).map((cmd) => (
              <div key={cmd} className="font-mono">
                {cmd}:{' '}
                {typeof cliCommands[cmd] === 'string'
                  ? cliCommands[cmd]
                  : JSON.stringify(cliCommands[cmd])}
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
    <ApprovalDialog
      open={approvalOpen}
      diffs={pendingDiffs}
      onClose={() => setApprovalOpen(false)}
      onApply={async (mode) => {
        setApprovalOpen(false);
        if (mode === 'diff') return;
        if (pendingOperation) {
          await executeOperation(pendingOperation.key, pendingOperation.args, mode);
        }
      }}
    />
  </>
  );
}
