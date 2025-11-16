import { useState } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { usePermaGraphEventListener } from '@/hooks/usePermaGraphWebSocket';

interface AgentLogEntry {
  agentId: string;
  message: string;
  level?: string;
  timestamp: string;
}

interface AgentLogViewerProps {
  projectId: string;
  agents: Array<{ id: string; name: string }>;
}

/**
 * Viewer for real-time agent logs streamed via WebSocket
 */
export function AgentLogViewer({ projectId, agents }: AgentLogViewerProps) {
  const [logs, setLogs] = useState<AgentLogEntry[]>([]);
  const [filter, setFilter] = useState<string>('all');

  usePermaGraphEventListener(projectId, 'agents.log', (data) => {
    if (data.agentId && data.message) {
      setLogs((prev) => [...prev, data as AgentLogEntry]);
    }
  });

  usePermaGraphEventListener(projectId, 'violation-found', (data) => {
    if (data.message) {
      setLogs((prev) => [
        ...prev,
        {
          agentId: data.ruleId || 'validation',
          message: data.message,
          level: data.status,
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  });

  const filteredLogs =
    filter === 'all' ? logs : logs.filter((log) => log.agentId === filter);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="font-medium">Agent Logs</span>
        <Select value={filter} onValueChange={setFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by agent" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All agents</SelectItem>
            {agents.map((agent) => (
              <SelectItem key={agent.id} value={agent.id}>
                {agent.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="h-48 overflow-auto border rounded p-2 text-sm font-mono bg-muted">
        {filteredLogs.map((log, idx) => (
          <div key={idx} className="mb-1">
            <span className="text-muted-foreground mr-2">
              {new Date(log.timestamp).toLocaleTimeString()}
            </span>
            <span className="font-semibold mr-2">{log.agentId}</span>
            {log.message}
          </div>
        ))}
      </div>
    </div>
  );
}
