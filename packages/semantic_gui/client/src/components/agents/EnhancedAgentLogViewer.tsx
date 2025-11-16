import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { usePermaGraphEventListener } from '@/hooks/usePermaGraphWebSocket';
import {
  Search,
  Download,
  Trash2,
  Filter,
  Play,
  Pause,
  AlertTriangle,
  Info,
  CheckCircle,
  XCircle,
  Clock,
  User,
  Activity,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AgentLogEntry {
  id: string;
  agentId: string;
  agentName: string;
  message: string;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';
  timestamp: string;
  category?:
    | 'reasoning'
    | 'explanation'
    | 'generation'
    | 'validation'
    | 'system';
  metadata?: Record<string, any>;
  duration?: number;
  stackTrace?: string;
}

interface EnhancedAgentLogViewerProps {
  projectId: string;
  agents: Array<{ id: string; name: string; type: string }>;
}

const logLevelStyles = {
  DEBUG: 'text-gray-600 bg-gray-50 border-gray-200',
  INFO: 'text-blue-600 bg-blue-50 border-blue-200',
  WARN: 'text-yellow-600 bg-yellow-50 border-yellow-200',
  ERROR: 'text-red-600 bg-red-50 border-red-200',
};

const logLevelIcons = {
  DEBUG: Info,
  INFO: CheckCircle,
  WARN: AlertTriangle,
  ERROR: XCircle,
};

/**
 * @kthulu:extend - Enhanced agent log viewer with advanced filtering and debugging
 * Provides comprehensive log analysis with real-time streaming and export capabilities
 */
export function EnhancedAgentLogViewer({
  projectId,
  agents,
}: EnhancedAgentLogViewerProps) {
  const [logs, setLogs] = useState<AgentLogEntry[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<AgentLogEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<string>('all');
  const [selectedLevel, setSelectedLevel] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const [showMetadata, setShowMetadata] = useState(false);
  const [maxLogs, setMaxLogs] = useState(1000);

  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  // Listen for agent logs
  usePermaGraphEventListener(projectId, 'agents.log', (data) => {
    if (!isStreaming) return;

    const logEntry: AgentLogEntry = {
      id: `${Date.now()}-${Math.random()}`,
      agentId: data.agentId || 'unknown',
      agentName:
        agents.find((a) => a.id === data.agentId)?.name ||
        data.agentId ||
        'Unknown',
      message: data.message || '',
      level: data.level || 'INFO',
      timestamp: data.timestamp || new Date().toISOString(),
      category: data.category || 'system',
      metadata: data.metadata,
      duration: data.duration,
      stackTrace: data.stackTrace,
    };

    setLogs((prev) => {
      const newLogs = [...prev, logEntry];
      // Keep only the last maxLogs entries
      return newLogs.slice(-maxLogs);
    });
  });

  // Listen for validation events and convert to logs
  usePermaGraphEventListener(projectId, 'validation-completed', (data) => {
    if (!isStreaming) return;

    const logEntry: AgentLogEntry = {
      id: `validation-${Date.now()}`,
      agentId: 'reasoner',
      agentName: 'Reasoner Agent',
      message: `Validation completed: ${data.isConsistent ? 'CONSISTENT' : 'VIOLATIONS FOUND'}`,
      level: data.isConsistent ? 'INFO' : 'WARN',
      timestamp: new Date().toISOString(),
      category: 'validation',
      metadata: {
        violationCount: data.violatedRules?.length || 0,
        consistencyStatus: data.isConsistent,
      },
    };

    setLogs((prev) => [...prev.slice(-maxLogs + 1), logEntry]);
  });

  // Listen for violation events
  usePermaGraphEventListener(projectId, 'violation-found', (data) => {
    if (!isStreaming) return;

    const logEntry: AgentLogEntry = {
      id: `violation-${Date.now()}`,
      agentId: 'reasoner',
      agentName: 'Reasoner Agent',
      message: `Violation detected: ${data.message}`,
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      category: 'validation',
      metadata: {
        ruleId: data.ruleId,
        components: data.components,
        severity: data.severity,
      },
    };

    setLogs((prev) => [...prev.slice(-maxLogs + 1), logEntry]);
  });

  // Filter logs based on current filters
  useEffect(() => {
    let filtered = logs;

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(
        (log) =>
          log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
          log.agentName.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Filter by agent
    if (selectedAgent !== 'all') {
      filtered = filtered.filter((log) => log.agentId === selectedAgent);
    }

    // Filter by level
    if (selectedLevel !== 'all') {
      filtered = filtered.filter((log) => log.level === selectedLevel);
    }

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter((log) => log.category === selectedCategory);
    }

    setFilteredLogs(filtered);
  }, [logs, searchTerm, selectedAgent, selectedLevel, selectedCategory]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredLogs, autoScroll]);

  const clearLogs = () => {
    setLogs([]);
  };

  const exportLogs = () => {
    const logData = filteredLogs.map((log) => ({
      timestamp: log.timestamp,
      agent: log.agentName,
      level: log.level,
      category: log.category,
      message: log.message,
      metadata: log.metadata,
    }));

    const blob = new Blob([JSON.stringify(logData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agent-logs-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getLogIcon = (level: AgentLogEntry['level']) => {
    const IconComponent = logLevelIcons[level];
    return <IconComponent className="w-4 h-4" />;
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  };

  const categories = Array.from(
    new Set(logs.map((log) => log.category).filter(Boolean))
  );
  const logStats = {
    total: logs.length,
    errors: logs.filter((log) => log.level === 'ERROR').length,
    warnings: logs.filter((log) => log.level === 'WARN').length,
    info: logs.filter((log) => log.level === 'INFO').length,
    debug: logs.filter((log) => log.level === 'DEBUG').length,
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Agent Logs & Debugging
            <Badge variant="outline">{filteredLogs.length} entries</Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsStreaming(!isStreaming)}
              className="flex items-center gap-2"
            >
              {isStreaming ? (
                <Pause className="w-4 h-4" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {isStreaming ? 'Pause' : 'Resume'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={exportLogs}
              className="flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Export
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearLogs}
              className="flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              Clear
            </Button>
          </div>
        </CardTitle>
      </CardHeader>

      <CardContent>
        <Tabs defaultValue="logs" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="logs">Live Logs</TabsTrigger>
            <TabsTrigger value="stats">Statistics</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="logs" className="space-y-4 mt-4">
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-2">
                <Search className="w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search logs..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-48"
                />
              </div>

              <Select value={selectedAgent} onValueChange={setSelectedAgent}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="All agents" />
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

              <Select value={selectedLevel} onValueChange={setSelectedLevel}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="All levels" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All levels</SelectItem>
                  <SelectItem value="ERROR">Error</SelectItem>
                  <SelectItem value="WARN">Warning</SelectItem>
                  <SelectItem value="INFO">Info</SelectItem>
                  <SelectItem value="DEBUG">Debug</SelectItem>
                </SelectContent>
              </Select>

              {categories.length > 0 && (
                <Select
                  value={selectedCategory}
                  onValueChange={setSelectedCategory}
                >
                  <SelectTrigger className="w-36">
                    <SelectValue placeholder="All categories" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All categories</SelectItem>
                    {categories.map((category) => (
                      <SelectItem key={category} value={category || ''}>
                        {category}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}

              <div className="flex items-center gap-2 ml-auto">
                <Label htmlFor="auto-scroll" className="text-sm">
                  Auto-scroll
                </Label>
                <Switch
                  id="auto-scroll"
                  checked={autoScroll}
                  onCheckedChange={setAutoScroll}
                />
              </div>
            </div>

            {/* Log Display */}
            <ScrollArea className="h-96 border rounded-lg" ref={scrollAreaRef}>
              <div className="p-4 space-y-2 font-mono text-sm">
                {filteredLogs.length === 0 ? (
                  <div className="text-center text-muted-foreground py-8">
                    {logs.length === 0
                      ? 'No logs yet'
                      : 'No logs match current filters'}
                  </div>
                ) : (
                  filteredLogs.map((log) => (
                    <div
                      key={log.id}
                      className={cn(
                        'p-3 rounded-lg border-l-4 space-y-1',
                        logLevelStyles[log.level]
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {getLogIcon(log.level)}
                          <Badge variant="outline" className="text-xs">
                            {log.level}
                          </Badge>
                          <span className="font-semibold">{log.agentName}</span>
                          {log.category && (
                            <Badge variant="secondary" className="text-xs">
                              {log.category}
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Clock className="w-3 h-3" />
                          {formatTimestamp(log.timestamp)}
                          {log.duration && <span>({log.duration}ms)</span>}
                        </div>
                      </div>

                      <div className="text-sm">{log.message}</div>

                      {showMetadata && log.metadata && (
                        <details className="text-xs">
                          <summary className="cursor-pointer text-muted-foreground">
                            Metadata
                          </summary>
                          <pre className="mt-1 p-2 bg-muted rounded text-xs overflow-x-auto">
                            {JSON.stringify(log.metadata, null, 2)}
                          </pre>
                        </details>
                      )}

                      {log.stackTrace && (
                        <details className="text-xs">
                          <summary className="cursor-pointer text-red-600">
                            Stack Trace
                          </summary>
                          <pre className="mt-1 p-2 bg-red-50 rounded text-xs overflow-x-auto text-red-800">
                            {log.stackTrace}
                          </pre>
                        </details>
                      )}
                    </div>
                  ))
                )}
                <div ref={logEndRef} />
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="stats" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <Card>
                <CardContent className="p-4 text-center">
                  <div className="text-2xl font-bold">{logStats.total}</div>
                  <div className="text-sm text-muted-foreground">Total</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4 text-center">
                  <div className="text-2xl font-bold text-red-600">
                    {logStats.errors}
                  </div>
                  <div className="text-sm text-muted-foreground">Errors</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4 text-center">
                  <div className="text-2xl font-bold text-yellow-600">
                    {logStats.warnings}
                  </div>
                  <div className="text-sm text-muted-foreground">Warnings</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4 text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {logStats.info}
                  </div>
                  <div className="text-sm text-muted-foreground">Info</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4 text-center">
                  <div className="text-2xl font-bold text-gray-600">
                    {logStats.debug}
                  </div>
                  <div className="text-sm text-muted-foreground">Debug</div>
                </CardContent>
              </Card>
            </div>

            {/* Agent Activity */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Agent Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {agents.map((agent) => {
                    const agentLogs = logs.filter(
                      (log) => log.agentId === agent.id
                    );
                    const lastActivity = agentLogs[agentLogs.length - 1];

                    return (
                      <div
                        key={agent.id}
                        className="flex items-center justify-between p-2 border rounded"
                      >
                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4" />
                          <span className="font-medium">{agent.name}</span>
                          <Badge variant="outline">
                            {agentLogs.length} logs
                          </Badge>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {lastActivity
                            ? `Last: ${formatTimestamp(lastActivity.timestamp)}`
                            : 'No activity'}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="settings" className="space-y-4 mt-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>Show Metadata</Label>
                <Switch
                  checked={showMetadata}
                  onCheckedChange={setShowMetadata}
                />
              </div>

              <div className="space-y-2">
                <Label>Max Log Entries</Label>
                <Select
                  value={maxLogs.toString()}
                  onValueChange={(value) => setMaxLogs(parseInt(value))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="100">100</SelectItem>
                    <SelectItem value="500">500</SelectItem>
                    <SelectItem value="1000">1000</SelectItem>
                    <SelectItem value="5000">5000</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Higher values may impact performance
                </p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
