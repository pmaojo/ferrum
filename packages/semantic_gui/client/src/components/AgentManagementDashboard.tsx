import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  usePermaGraphAgents,
  useStartAgent,
  useStopAgent,
} from '@/hooks/use-graph';
import { usePermaGraphEventListener } from '@/hooks/usePermaGraphWebSocket';

interface Props {
  projectId: string;
}

/**
 * Simple dashboard for managing PermaGraph agents.
 * Shows start/stop controls and displays realtime log events.
 */
export function AgentManagementDashboard({ projectId }: Props) {
  const { data } = usePermaGraphAgents();
  const startAgent = useStartAgent();
  const stopAgent = useStopAgent();
  const [logs, setLogs] = useState<string[]>([]);

  usePermaGraphEventListener(projectId, 'agents.event', (event) => {
    const message = event?.message || JSON.stringify(event);
    setLogs((prev) => [...prev, message]);
  });

  const agents = data?.agents || [];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Agents</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {agents.map((agent: any) => (
              <li key={agent.id} className="flex items-center gap-2">
                <span className="flex-1">
                  {agent.name || agent.id} - {agent.status}
                </span>
                {agent.status === 'running' ? (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => stopAgent.mutate({ agentId: agent.id })}
                  >
                    Stop
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    onClick={() => startAgent.mutate({ agentId: agent.id })}
                  >
                    Start
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Logs</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="h-40 overflow-auto border rounded p-2 text-sm"
            data-testid="agent-logs"
          >
            {logs.map((log, idx) => (
              <div key={idx}>{log}</div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
