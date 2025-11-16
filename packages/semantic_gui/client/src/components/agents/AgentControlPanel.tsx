import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import {
  useStartAgent,
  useStopAgent,
  usePermaGraphConfigureAgent,
} from '@/hooks/use-graph';
import { usePermaGraphAgentStatus } from '@/hooks/usePermaGraphWebSocket';

interface AgentControlPanelProps {
  projectId: string;
  agent: any;
}

/**
 * Control panel for individual PermaGraph agents
 */
export function AgentControlPanel({
  projectId,
  agent,
}: AgentControlPanelProps) {
  const { toast } = useToast();
  const startAgent = useStartAgent();
  const stopAgent = useStopAgent();
  const configureAgent = usePermaGraphConfigureAgent();
  const statuses = usePermaGraphAgentStatus(projectId);

  const [showConfig, setShowConfig] = useState(false);
  const [reasoner, setReasoner] = useState(agent.config?.reasoner || 'ELK');

  const current = statuses[agent.id]?.status || agent.status;
  const healthy = statuses[agent.id]?.healthy;
  const lastHeartbeat = statuses[agent.id]?.lastHeartbeat || agent.lastActivity;

  const handleStart = () => {
    startAgent.mutate(
      { agentId: agent.id },
      {
        onSuccess: () => {
          toast({
            title: 'Agent Started',
            description: `${agent.name} is now running`,
          });
        },
        onError: (error) => {
          toast({
            title: 'Start Failed',
            description: (error as Error).message,
            variant: 'destructive',
          });
        },
      }
    );
  };

  const handleStop = () => {
    stopAgent.mutate(
      { agentId: agent.id },
      {
        onSuccess: () => {
          toast({
            title: 'Agent Stopped',
            description: `${agent.name} has been stopped`,
          });
        },
        onError: (error) => {
          toast({
            title: 'Stop Failed',
            description: (error as Error).message,
            variant: 'destructive',
          });
        },
      }
    );
  };

  const handleSaveConfig = () => {
    configureAgent.mutate(
      { projectId, agentId: agent.id, config: { reasoner } },
      {
        onSuccess: () => {
          toast({
            title: 'Configuration Saved',
            description: `${agent.name} configured to use ${reasoner} reasoner`,
          });
          setShowConfig(false);
        },
        onError: (error) => {
          toast({
            title: 'Configuration Failed',
            description: (error as Error).message,
            variant: 'destructive',
          });
        },
      }
    );
  };

  return (
    <div className="p-4 border rounded space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Badge variant={current === 'running' ? 'default' : 'secondary'}>
            {current}
          </Badge>
          {healthy !== undefined && (
            <Badge variant={healthy ? 'default' : 'destructive'}>
              {healthy ? 'Healthy' : 'Unhealthy'}
            </Badge>
          )}
          <div>
            <div className="font-medium">{agent.name}</div>
            <div className="text-sm text-muted-foreground">
              Type: {agent.type}
              {lastHeartbeat && (
                <span>
                  {' • '}Last heartbeat:{' '}
                  {new Date(lastHeartbeat).toLocaleTimeString()}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          {current === 'running' ? (
            <Button
              onClick={handleStop}
              disabled={stopAgent.isPending}
              size="sm"
              variant="outline"
            >
              Stop
            </Button>
          ) : (
            <Button
              onClick={handleStart}
              disabled={startAgent.isPending}
              size="sm"
              variant="outline"
            >
              Start
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowConfig((v) => !v)}
          >
            Configure
          </Button>
        </div>
      </div>

      {showConfig && (
        <div className="mt-2 border-t pt-2 space-y-2">
          <div className="flex items-center gap-2">
            <Label htmlFor={`reasoner-${agent.id}`}>Reasoner</Label>
            <Select value={reasoner} onValueChange={setReasoner}>
              <SelectTrigger id={`reasoner-${agent.id}`} className="w-[180px]">
                <SelectValue placeholder="Select reasoner" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ELK">ELK</SelectItem>
                <SelectItem value="HermiT">HermiT</SelectItem>
              </SelectContent>
            </Select>
            <Button
              onClick={handleSaveConfig}
              size="sm"
              disabled={configureAgent.isPending}
            >
              {configureAgent.isPending ? 'Saving...' : 'Save'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
