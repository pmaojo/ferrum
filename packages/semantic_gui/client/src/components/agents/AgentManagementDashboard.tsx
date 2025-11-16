import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import {
  usePermaGraphAgents,
  useStartAgent,
  useStopAgent,
} from '@/hooks/use-graph';
import {
  usePermaGraphAgentStatus,
  usePermaGraphEventListener,
} from '@/hooks/usePermaGraphWebSocket';
import { EnhancedAgentControlPanel } from './EnhancedAgentControlPanel';
import { EnhancedAgentLogViewer } from './EnhancedAgentLogViewer';
import {
  Brain,
  Zap,
  Activity,
  Play,
  Square,
  Settings,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  BarChart3,
  Network,
  Cpu,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AgentManagementDashboardProps {
  projectId: string;
}

interface SystemMetrics {
  totalAgents: number;
  runningAgents: number;
  healthyAgents: number;
  totalTasks: number;
  averageResponseTime: number;
  systemLoad: number;
  uptime: number;
}

const agentTypeConfig = {
  reasoner: {
    icon: Brain,
    color: 'text-blue-600 bg-blue-50 border-blue-200',
    description: 'OWL reasoning and validation',
  },
  explanation: {
    icon: Zap,
    color: 'text-purple-600 bg-purple-50 border-purple-200',
    description: 'Natural language explanations',
  },
  generation: {
    icon: Activity,
    color: 'text-green-600 bg-green-50 border-green-200',
    description: 'Code and axiom generation',
  },
};

/**
 * @kthulu:extend - Comprehensive agent management dashboard
 * Provides centralized control and monitoring for all PermaGraph agents
 */
export function AgentManagementDashboard({
  projectId,
}: AgentManagementDashboardProps) {
  const { toast } = useToast();
  const { data: agentsData } = usePermaGraphAgents();
  const agentStatuses = usePermaGraphAgentStatus(projectId);
  const startAgent = useStartAgent();
  const stopAgent = useStopAgent();

  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics>({
    totalAgents: 0,
    runningAgents: 0,
    healthyAgents: 0,
    totalTasks: 0,
    averageResponseTime: 0,
    systemLoad: 0,
    uptime: 0,
  });

  const [recentEvents, setRecentEvents] = useState<
    Array<{
      id: string;
      type: string;
      message: string;
      timestamp: string;
      severity: 'info' | 'warning' | 'error';
    }>
  >([]);

  const agents = agentsData?.agents || [];

  // Listen for system events
  usePermaGraphEventListener(projectId, 'agents.status', (data) => {
    const event = {
      id: `status-${Date.now()}`,
      type: 'status',
      message: `Agent ${data.agentName} is now ${data.status}`,
      timestamp: new Date().toISOString(),
      severity: data.status === 'error' ? 'error' : ('info' as const),
    };
    setRecentEvents((prev) => [event, ...prev.slice(0, 9)]);
  });

  usePermaGraphEventListener(projectId, 'validation-completed', (data) => {
    const event = {
      id: `validation-${Date.now()}`,
      type: 'validation',
      message: `Validation ${data.isConsistent ? 'passed' : 'failed'} - ${data.violatedRules?.length || 0} violations`,
      timestamp: new Date().toISOString(),
      severity: data.isConsistent ? 'info' : ('warning' as const),
    };
    setRecentEvents((prev) => [event, ...prev.slice(0, 9)]);
  });

  usePermaGraphEventListener(projectId, 'agents.log', (data) => {
    const event = {
      id: `agents-${Date.now()}`,
      type: data.type || 'agent',
      message: data.message || '',
      timestamp: data.timestamp || new Date().toISOString(),
      severity:
        data.level === 'ERROR'
          ? ('error' as const)
          : data.level === 'WARN'
            ? ('warning' as const)
            : ('info' as const),
    };
    setRecentEvents((prev) => [event, ...prev.slice(0, 9)]);
  });

  usePermaGraphEventListener(projectId, 'agent-error', (data) => {
    const event = {
      id: `error-${Date.now()}`,
      type: 'error',
      message: `Agent error: ${data.message}`,
      timestamp: new Date().toISOString(),
      severity: 'error' as const,
    };
    setRecentEvents((prev) => [event, ...prev.slice(0, 9)]);
  });

  // Calculate system metrics
  useEffect(() => {
    const runningCount = agents.filter(
      (agent) => (agentStatuses[agent.id]?.status || agent.status) === 'running'
    ).length;

    const healthyCount = agents.filter(
      (agent) => agentStatuses[agent.id]?.healthy !== false
    ).length;

    const totalTasks = agents.reduce(
      (sum, agent) => sum + (agent.metrics?.tasksCompleted || 0),
      0
    );

    const avgResponseTime =
      agents.length > 0
        ? agents.reduce(
            (sum, agent) => sum + (agent.metrics?.averageResponseTime || 0),
            0
          ) / agents.length
        : 0;

    const systemLoad =
      runningCount > 0 ? (runningCount / agents.length) * 100 : 0;

    setSystemMetrics({
      totalAgents: agents.length,
      runningAgents: runningCount,
      healthyAgents: healthyCount,
      totalTasks,
      averageResponseTime: Math.round(avgResponseTime),
      systemLoad: Math.round(systemLoad),
      uptime: Math.max(...agents.map((a) => a.metrics?.uptime || 0)),
    });
  }, [agents, agentStatuses]);

  const handleStartAll = () => {
    const stoppedAgents = agents.filter(
      (agent) => (agentStatuses[agent.id]?.status || agent.status) !== 'running'
    );

    stoppedAgents.forEach((agent) => {
      startAgent.mutate({ agentId: agent.id });
    });

    toast({
      title: 'Starting All Agents',
      description: `Starting ${stoppedAgents.length} agents...`,
    });
  };

  const handleStopAll = () => {
    const runningAgents = agents.filter(
      (agent) => (agentStatuses[agent.id]?.status || agent.status) === 'running'
    );

    runningAgents.forEach((agent) => {
      stopAgent.mutate({ agentId: agent.id });
    });

    toast({
      title: 'Stopping All Agents',
      description: `Stopping ${runningAgents.length} agents...`,
    });
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'status':
        return <Activity className="w-4 h-4" />;
      case 'validation':
        return <CheckCircle className="w-4 h-4" />;
      case 'error':
        return <AlertTriangle className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const getEventColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'warning':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default:
        return 'text-blue-600 bg-blue-50 border-blue-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* System Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Network className="w-5 h-5" />
              Agent System Overview
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={handleStartAll}
                disabled={
                  systemMetrics.runningAgents === systemMetrics.totalAgents
                }
                size="sm"
                className="flex items-center gap-2"
              >
                <Play className="w-4 h-4" />
                Start All
              </Button>
              <Button
                onClick={handleStopAll}
                disabled={systemMetrics.runningAgents === 0}
                variant="outline"
                size="sm"
                className="flex items-center gap-2"
              >
                <Square className="w-4 h-4" />
                Stop All
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {systemMetrics.totalAgents}
                </div>
                <div className="text-sm text-muted-foreground">
                  Total Agents
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-green-600">
                  {systemMetrics.runningAgents}
                </div>
                <div className="text-sm text-muted-foreground">Running</div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-emerald-600">
                  {systemMetrics.healthyAgents}
                </div>
                <div className="text-sm text-muted-foreground">Healthy</div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {systemMetrics.totalTasks}
                </div>
                <div className="text-sm text-muted-foreground">Tasks Done</div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {systemMetrics.averageResponseTime}ms
                </div>
                <div className="text-sm text-muted-foreground">
                  Avg Response
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-cyan-600">
                  {systemMetrics.systemLoad}%
                </div>
                <div className="text-sm text-muted-foreground">System Load</div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-gray-600">
                  {Math.floor(systemMetrics.uptime / 3600)}h
                </div>
                <div className="text-sm text-muted-foreground">Max Uptime</div>
              </CardContent>
            </Card>
          </div>

          {/* System Health Bar */}
          <div className="mt-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span>System Health</span>
              <span>
                {Math.round(
                  (systemMetrics.healthyAgents /
                    Math.max(systemMetrics.totalAgents, 1)) *
                    100
                )}
                %
              </span>
            </div>
            <Progress
              value={
                (systemMetrics.healthyAgents /
                  Math.max(systemMetrics.totalAgents, 1)) *
                100
              }
              className="h-2"
            />
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agent Controls */}
        <div className="lg:col-span-2">
          <Tabs defaultValue="agents" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="agents">Agent Controls</TabsTrigger>
              <TabsTrigger value="logs">System Logs</TabsTrigger>
            </TabsList>

            <TabsContent value="agents" className="space-y-4 mt-4">
              <div className="space-y-4">
                {agents.map((agent) => (
                  <EnhancedAgentControlPanel
                    key={agent.id}
                    projectId={projectId}
                    agent={agent}
                  />
                ))}

                {agents.length === 0 && (
                  <Card>
                    <CardContent className="p-8 text-center">
                      <Brain className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                      <h3 className="text-lg font-semibold mb-2">
                        No Agents Available
                      </h3>
                      <p className="text-muted-foreground">
                        Initialize PermaGraph to create intelligent agents for
                        semantic analysis.
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>
            </TabsContent>

            <TabsContent value="logs" className="mt-4">
              <EnhancedAgentLogViewer projectId={projectId} agents={agents} />
            </TabsContent>
          </Tabs>
        </div>

        {/* System Activity & Events */}
        <div className="space-y-6">
          {/* Agent Type Distribution */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                Agent Distribution
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {Object.entries(agentTypeConfig).map(([type, config]) => {
                const count = agents.filter(
                  (agent) => agent.type === type
                ).length;
                const IconComponent = config.icon;

                return (
                  <div key={type} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={cn('p-1 rounded', config.color)}>
                        <IconComponent className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="font-medium capitalize">{type}</div>
                        <div className="text-xs text-muted-foreground">
                          {config.description}
                        </div>
                      </div>
                    </div>
                    <Badge variant="outline">{count}</Badge>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Recent Events */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Recent Events
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {recentEvents.length === 0 ? (
                  <div className="text-center text-muted-foreground py-4">
                    No recent events
                  </div>
                ) : (
                  recentEvents.map((event) => (
                    <div
                      key={event.id}
                      className={cn(
                        'p-2 rounded-lg border-l-4 text-sm',
                        getEventColor(event.severity)
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        {getEventIcon(event.type)}
                        <span className="font-medium capitalize">
                          {event.type}
                        </span>
                        <span className="text-xs text-muted-foreground ml-auto">
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <div>{event.message}</div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Settings className="w-4 h-4" />
                Quick Actions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start"
              >
                <Cpu className="w-4 h-4 mr-2" />
                System Diagnostics
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start"
              >
                <TrendingUp className="w-4 h-4 mr-2" />
                Performance Report
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start"
              >
                <Settings className="w-4 h-4 mr-2" />
                Global Configuration
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
