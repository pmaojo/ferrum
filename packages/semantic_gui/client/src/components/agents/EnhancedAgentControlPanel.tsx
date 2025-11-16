import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import {
  useStartAgent,
  useStopAgent,
  usePermaGraphConfigureAgent,
  useExplainViolation,
} from '@/hooks/use-graph';
import { usePermaGraphAgentStatus } from '@/hooks/usePermaGraphWebSocket';
import {
  Play,
  Square,
  Settings,
  Activity,
  Brain,
  Zap,
  AlertTriangle,
  CheckCircle,
  Clock,
  Cpu,
  MemoryStick,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AgentConfig {
  reasoner?: 'ELK' | 'HermiT' | 'Pellet';
  maxConcurrency?: number;
  timeout?: number;
  retryAttempts?: number;
  enableCaching?: boolean;
  logLevel?: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';
  customPrompt?: string;
  temperature?: number;
  maxTokens?: number;
}

interface AgentMetrics {
  tasksCompleted: number;
  averageResponseTime: number;
  successRate: number;
  memoryUsage: number;
  cpuUsage: number;
  uptime: number;
  lastError?: string;
}

interface EnhancedAgentControlPanelProps {
  projectId: string;
  agent: {
    id: string;
    name: string;
    type: 'reasoner' | 'explanation' | 'generation';
    description?: string;
    config?: AgentConfig;
    metrics?: AgentMetrics;
  };
}

const agentTypeIcons = {
  reasoner: Brain,
  explanation: Zap,
  generation: Activity,
};

const agentTypeColors = {
  reasoner: 'text-blue-600 bg-blue-50 border-blue-200',
  explanation: 'text-purple-600 bg-purple-50 border-purple-200',
  generation: 'text-green-600 bg-green-50 border-green-200',
};

/**
 * @kthulu:extend - Enhanced agent control panel with advanced configuration and monitoring
 * Provides comprehensive agent management with real-time metrics and debugging
 */
export function EnhancedAgentControlPanel({
  projectId,
  agent,
}: EnhancedAgentControlPanelProps) {
  const { toast } = useToast();
  const startAgent = useStartAgent();
  const stopAgent = useStopAgent();
  const configureAgent = usePermaGraphConfigureAgent();
  const explainViolation = useExplainViolation();
  const statuses = usePermaGraphAgentStatus(projectId);

  const [showConfig, setShowConfig] = useState(false);
  const [showMetrics, setShowMetrics] = useState(false);
  const [config, setConfig] = useState<AgentConfig>(agent.config || {});
  const [isConfigDirty, setIsConfigDirty] = useState(false);

  const currentStatus = statuses[agent.id]?.status || 'stopped';
  const isHealthy = statuses[agent.id]?.healthy !== false;
  const lastHeartbeat = statuses[agent.id]?.lastHeartbeat;
  const metrics = agent.metrics || {
    tasksCompleted: 0,
    averageResponseTime: 0,
    successRate: 100,
    memoryUsage: 0,
    cpuUsage: 0,
    uptime: 0,
  };

  const IconComponent = agentTypeIcons[agent.type];
  const colorClass = agentTypeColors[agent.type];

  // Update config dirty state when config changes
  useEffect(() => {
    const hasChanges =
      JSON.stringify(config) !== JSON.stringify(agent.config || {});
    setIsConfigDirty(hasChanges);
  }, [config, agent.config]);

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
      { projectId, agentId: agent.id, config },
      {
        onSuccess: () => {
          toast({
            title: 'Configuration Saved',
            description: `${agent.name} configuration updated successfully`,
          });
          setIsConfigDirty(false);
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

  const handleResetConfig = () => {
    setConfig(agent.config || {});
    setIsConfigDirty(false);
  };

  const handleExplain = () => {
    const description = window.prompt('Describe violation to explain');
    if (!description) return;
    explainViolation.mutate(
      {
        projectId,
        agentId: agent.id,
        violation: {
          ruleId: 'manual',
          type: 'DIP_VIOLATION',
          severity: 'low',
          description,
          sourceElement: 'unknown',
        },
      },
      {
        onSuccess: (data) => {
          toast({
            title: 'Explanation',
            description: data.explanation,
          });
        },
        onError: (error) => {
          toast({
            title: 'Explain Failed',
            description: (error as Error).message,
            variant: 'destructive',
          });
        },
      }
    );
  };

  const getStatusBadge = () => {
    switch (currentStatus) {
      case 'running':
        return (
          <Badge className="bg-green-100 text-green-800">🟢 Running</Badge>
        );
      case 'starting':
        return (
          <Badge className="bg-yellow-100 text-yellow-800">🟡 Starting</Badge>
        );
      case 'stopping':
        return (
          <Badge className="bg-orange-100 text-orange-800">🟠 Stopping</Badge>
        );
      case 'error':
        return <Badge variant="destructive">🔴 Error</Badge>;
      default:
        return <Badge variant="secondary">⚫ Stopped</Badge>;
    }
  };

  const getHealthBadge = () => {
    if (currentStatus !== 'running') return null;

    return isHealthy ? (
      <Badge className="bg-green-100 text-green-800">
        <CheckCircle className="w-3 h-3 mr-1" />
        Healthy
      </Badge>
    ) : (
      <Badge variant="destructive">
        <AlertTriangle className="w-3 h-3 mr-1" />
        Unhealthy
      </Badge>
    );
  };

  return (
    <Card className={cn('border-2', colorClass)}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn('p-2 rounded-lg', colorClass)}>
              <IconComponent className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold">{agent.name}</h3>
              <p className="text-sm text-muted-foreground capitalize">
                {agent.type} Agent
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {getStatusBadge()}
            {getHealthBadge()}
          </div>
        </CardTitle>
        {agent.description && (
          <p className="text-sm text-muted-foreground">{agent.description}</p>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Control Buttons */}
        <div className="flex items-center gap-2">
          {currentStatus === 'running' ? (
            <Button
              onClick={handleStop}
              disabled={stopAgent.isPending}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
            >
              <Square className="w-4 h-4" />
              {stopAgent.isPending ? 'Stopping...' : 'Stop'}
            </Button>
          ) : (
            <Button
              onClick={handleStart}
              disabled={startAgent.isPending}
              size="sm"
              className="flex items-center gap-2"
            >
              <Play className="w-4 h-4" />
              {startAgent.isPending ? 'Starting...' : 'Start'}
            </Button>
          )}

          <Button
            onClick={handleExplain}
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
          >
            Explain
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowConfig(!showConfig)}
            className="flex items-center gap-2"
          >
            <Settings className="w-4 h-4" />
            Configure
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowMetrics(!showMetrics)}
            className="flex items-center gap-2"
          >
            <TrendingUp className="w-4 h-4" />
            Metrics
          </Button>
        </div>

        {/* Quick Status Info */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-muted-foreground" />
            <span>
              Uptime: {Math.floor(metrics.uptime / 3600)}h{' '}
              {Math.floor((metrics.uptime % 3600) / 60)}m
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-muted-foreground" />
            <span>Tasks: {metrics.tasksCompleted}</span>
          </div>
          {lastHeartbeat && (
            <div className="flex items-center gap-2 col-span-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-xs text-muted-foreground">
                Last heartbeat: {new Date(lastHeartbeat).toLocaleTimeString()}
              </span>
            </div>
          )}
        </div>

        {/* Configuration Panel */}
        {showConfig && (
          <Card className="border-dashed">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center justify-between">
                Agent Configuration
                {isConfigDirty && (
                  <Badge variant="outline" className="text-orange-600">
                    Unsaved Changes
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="general" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="general">General</TabsTrigger>
                  <TabsTrigger value="reasoning">Reasoning</TabsTrigger>
                  <TabsTrigger value="advanced">Advanced</TabsTrigger>
                </TabsList>

                <TabsContent value="general" className="space-y-4 mt-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Log Level</Label>
                      <Select
                        value={config.logLevel || 'INFO'}
                        onValueChange={(value) =>
                          setConfig({ ...config, logLevel: value as any })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="DEBUG">Debug</SelectItem>
                          <SelectItem value="INFO">Info</SelectItem>
                          <SelectItem value="WARN">Warning</SelectItem>
                          <SelectItem value="ERROR">Error</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label>Max Concurrency</Label>
                      <Input
                        type="number"
                        value={config.maxConcurrency || 5}
                        onChange={(e) =>
                          setConfig({
                            ...config,
                            maxConcurrency: parseInt(e.target.value),
                          })
                        }
                        min={1}
                        max={20}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Enable Caching</Label>
                      <Switch
                        checked={config.enableCaching !== false}
                        onCheckedChange={(checked) =>
                          setConfig({ ...config, enableCaching: checked })
                        }
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Timeout (seconds)</Label>
                    <div className="px-3">
                      <Slider
                        value={[config.timeout || 30]}
                        onValueChange={([value]) =>
                          setConfig({ ...config, timeout: value })
                        }
                        max={300}
                        min={5}
                        step={5}
                        className="w-full"
                      />
                      <div className="flex justify-between text-xs text-muted-foreground mt-1">
                        <span>5s</span>
                        <span>{config.timeout || 30}s</span>
                        <span>300s</span>
                      </div>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="reasoning" className="space-y-4 mt-4">
                  {agent.type === 'reasoner' && (
                    <div className="space-y-2">
                      <Label>Reasoner Engine</Label>
                      <Select
                        value={config.reasoner || 'ELK'}
                        onValueChange={(value) =>
                          setConfig({ ...config, reasoner: value as any })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="ELK">
                            ELK (Fast, OWL 2 EL)
                          </SelectItem>
                          <SelectItem value="HermiT">
                            HermiT (Complete, OWL 2 DL)
                          </SelectItem>
                          <SelectItem value="Pellet">
                            Pellet (Stable, OWL 2 DL)
                          </SelectItem>
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground">
                        ELK is fastest for basic reasoning. HermiT/Pellet
                        support complex restrictions.
                      </p>
                    </div>
                  )}

                  {agent.type === 'explanation' && (
                    <>
                      <div className="space-y-2">
                        <Label>Temperature</Label>
                        <div className="px-3">
                          <Slider
                            value={[config.temperature || 0.7]}
                            onValueChange={([value]) =>
                              setConfig({ ...config, temperature: value })
                            }
                            max={2}
                            min={0}
                            step={0.1}
                            className="w-full"
                          />
                          <div className="flex justify-between text-xs text-muted-foreground mt-1">
                            <span>0 (Deterministic)</span>
                            <span>{config.temperature || 0.7}</span>
                            <span>2 (Creative)</span>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label>Max Tokens</Label>
                        <Input
                          type="number"
                          value={config.maxTokens || 500}
                          onChange={(e) =>
                            setConfig({
                              ...config,
                              maxTokens: parseInt(e.target.value),
                            })
                          }
                          min={50}
                          max={2000}
                        />
                      </div>
                    </>
                  )}
                </TabsContent>

                <TabsContent value="advanced" className="space-y-4 mt-4">
                  <div className="space-y-2">
                    <Label>Retry Attempts</Label>
                    <Input
                      type="number"
                      value={config.retryAttempts || 3}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          retryAttempts: parseInt(e.target.value),
                        })
                      }
                      min={0}
                      max={10}
                    />
                  </div>

                  {agent.type === 'explanation' && (
                    <div className="space-y-2">
                      <Label>Custom Prompt Template</Label>
                      <Textarea
                        value={config.customPrompt || ''}
                        onChange={(e) =>
                          setConfig({ ...config, customPrompt: e.target.value })
                        }
                        placeholder="Enter custom prompt template for explanations..."
                        rows={4}
                      />
                      <p className="text-xs text-muted-foreground">
                        Use {'{violation}'}, {'{components}'}, {'{suggestion}'}{' '}
                        as placeholders.
                      </p>
                    </div>
                  )}
                </TabsContent>
              </Tabs>

              <Separator className="my-4" />

              <div className="flex justify-between">
                <Button
                  variant="outline"
                  onClick={handleResetConfig}
                  disabled={!isConfigDirty}
                >
                  Reset
                </Button>
                <Button
                  onClick={handleSaveConfig}
                  disabled={configureAgent.isPending || !isConfigDirty}
                >
                  {configureAgent.isPending
                    ? 'Saving...'
                    : 'Save Configuration'}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Metrics Panel */}
        {showMetrics && (
          <Card className="border-dashed">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Performance Metrics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Success Rate</span>
                    <span className="text-sm text-muted-foreground">
                      {metrics.successRate}%
                    </span>
                  </div>
                  <Progress value={metrics.successRate} className="h-2" />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Avg Response</span>
                    <span className="text-sm text-muted-foreground">
                      {metrics.averageResponseTime}ms
                    </span>
                  </div>
                  <Progress
                    value={Math.min(metrics.averageResponseTime / 10, 100)}
                    className="h-2"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm">CPU: {metrics.cpuUsage}%</span>
                </div>
                <div className="flex items-center gap-2">
                  <MemoryStick className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm">
                    Memory: {metrics.memoryUsage}MB
                  </span>
                </div>
              </div>

              {metrics.lastError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <AlertTriangle className="w-4 h-4 text-red-600" />
                    <span className="text-sm font-medium text-red-800">
                      Last Error
                    </span>
                  </div>
                  <p className="text-xs text-red-700 font-mono">
                    {metrics.lastError}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </CardContent>
    </Card>
  );
}
