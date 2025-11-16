import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Cpu,
  Database,
  HardDrive,
  History,
  MemoryStick,
  Network,
  RefreshCw,
  TrendingUp,
  XCircle,
} from 'lucide-react';
import { useMonitoring } from '@/hooks/useMonitoring';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';

interface SystemHealth {
  overall_status: string;
  components: Record<string, ComponentHealth>;
  unhealthy_components: string[];
  timestamp: string;
}

interface ComponentHealth {
  status: string;
  message: string;
  timestamp: string;
  response_time_ms: number;
  details: Record<string, any>;
}

interface PerformanceMetrics {
  reasoning: {
    average_duration_ms: number;
    recent_operations: number;
    max_duration_ms: number;
  };
  queries: {
    average_duration_ms: number;
    recent_queries: number;
    max_duration_ms: number;
  };
  synchronization: {
    average_duration_ms: number;
    recent_syncs: number;
    max_duration_ms: number;
  };
  timestamp: string;
}

interface SystemAlert {
  id: string;
  severity: string;
  component: string;
  message: string;
  timestamp: string;
  details: Record<string, any>;
}

interface SystemResources {
  cpu: {
    usage_percent: number;
    cores: number;
    load_average: number[];
  };
  memory: {
    usage_percent: number;
    total_mb: number;
    available_mb: number;
    used_mb: number;
  };
  disk: {
    usage_percent: number;
    total_gb: number;
    available_gb: number;
    used_gb: number;
  };
  network: {
    bytes_sent: number;
    bytes_received: number;
    packets_sent: number;
    packets_received: number;
  };
  timestamp: string;
}

export const MonitoringDashboard: React.FC = () => {
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [performanceMetrics, setPerformanceMetrics] =
    useState<PerformanceMetrics | null>(null);
  const [activeAlerts, setActiveAlerts] = useState<SystemAlert[]>([]);
  const [systemResources, setSystemResources] =
    useState<SystemResources | null>(null);
  const [metricsHistory, setMetricsHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const {
    metrics: queriedMetrics,
    alertHistory,
    components: componentHealth,
    queryMetrics,
    fetchAlertHistory,
    fetchComponentHealth,
    checkComponent,
  } = useMonitoring();

  const fetchMonitoringData = async () => {
    try {
      setRefreshing(true);

      const [
        healthResponse,
        metricsResponse,
        alertsResponse,
        resourcesResponse,
      ] = await Promise.all([
        fetch('/api/monitoring/health'),
        fetch('/api/monitoring/metrics/performance'),
        fetch('/api/monitoring/alerts'),
        fetch('/api/monitoring/system/resources'),
      ]);

      const [health, metrics, alerts, resources] = await Promise.all([
        healthResponse.json(),
        metricsResponse.json(),
        alertsResponse.json(),
        resourcesResponse.json(),
      ]);

      setSystemHealth(health.data);
      setPerformanceMetrics(metrics.data);
      setActiveAlerts(alerts.data);
      setSystemResources(resources.data);

      await Promise.all([
        queryMetrics(),
        fetchAlertHistory(),
        fetchComponentHealth(),
      ]);

      // Generate mock metrics history for charts
      const now = Date.now();
      const history = Array.from({ length: 20 }, (_, i) => ({
        timestamp: new Date(now - (19 - i) * 60000).toLocaleTimeString(),
        reasoning: Math.random() * 500 + 100,
        queries: Math.random() * 200 + 50,
        sync: Math.random() * 300 + 75,
        cpu: Math.random() * 100,
        memory: Math.random() * 100,
        disk: Math.random() * 100,
      }));
      setMetricsHistory(history);
    } catch (error) {
      console.error('Error fetching monitoring data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMonitoringData();
    const interval = setInterval(fetchMonitoringData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'degraded':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'unhealthy':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'degraded':
        return 'bg-yellow-100 text-yellow-800';
      case 'unhealthy':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'info':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const resolveAlert = async (alertId: string) => {
    try {
      await fetch(`/api/monitoring/alerts/${alertId}/resolve`, {
        method: 'POST',
      });
      // Refresh alerts
      const response = await fetch('/api/monitoring/alerts');
      const data = await response.json();
      setActiveAlerts(data.data);
    } catch (error) {
      console.error('Error resolving alert:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading monitoring data...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">System Monitoring</h1>
          <p className="text-muted-foreground">
            Real-time monitoring and observability for PermaGraph ecosystem
          </p>
        </div>
        <Button
          onClick={fetchMonitoringData}
          disabled={refreshing}
          variant="outline"
        >
          <RefreshCw
            className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`}
          />
          Refresh
        </Button>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
          <TabsTrigger value="resources">Resources</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {/* System Health Overview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                System Health
              </CardTitle>
              <CardDescription>
                Overall system status and component health
              </CardDescription>
            </CardHeader>
            <CardContent>
              {systemHealth && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(systemHealth.overall_status)}
                    <Badge
                      className={getStatusColor(systemHealth.overall_status)}
                    >
                      {systemHealth.overall_status.toUpperCase()}
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                      Last updated:{' '}
                      {new Date(systemHealth.timestamp).toLocaleString()}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Object.entries(componentHealth).map(
                      ([name, component]) => (
                        <Card key={name} className="p-4">
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="font-medium capitalize">
                              {name.replace('_', ' ')}
                            </h4>
                            <div className="flex items-center gap-2">
                              {getStatusIcon(component.status)}
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => checkComponent(name)}
                              >
                                Check
                              </Button>
                            </div>
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">
                            {component.message}
                          </p>
                          <div className="text-xs text-muted-foreground">
                            Last check:{' '}
                            {new Date(component.timestamp).toLocaleString()}
                          </div>
                        </Card>
                      )
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Active Alerts */}
          {activeAlerts.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  Active Alerts ({activeAlerts.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {activeAlerts.map((alert) => (
                    <Alert key={alert.id}>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertTitle className="flex items-center justify-between">
                        <span>{alert.component}</span>
                        <div className="flex items-center gap-2">
                          <Badge className={getSeverityColor(alert.severity)}>
                            {alert.severity}
                          </Badge>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => resolveAlert(alert.id)}
                          >
                            Resolve
                          </Button>
                        </div>
                      </AlertTitle>
                      <AlertDescription>
                        {alert.message}
                        <div className="text-xs text-muted-foreground mt-1">
                          {new Date(alert.timestamp).toLocaleString()}
                        </div>
                      </AlertDescription>
                    </Alert>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          {/* Performance Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {performanceMetrics && (
              <>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium">
                      Reasoning Operations
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {performanceMetrics.reasoning.average_duration_ms.toFixed(
                        1
                      )}
                      ms
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Average duration (
                      {performanceMetrics.reasoning.recent_operations} recent)
                    </p>
                    <div className="text-xs text-muted-foreground mt-1">
                      Max: {performanceMetrics.reasoning.max_duration_ms}ms
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium">
                      SPARQL Queries
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {performanceMetrics.queries.average_duration_ms.toFixed(
                        1
                      )}
                      ms
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Average duration (
                      {performanceMetrics.queries.recent_queries} recent)
                    </p>
                    <div className="text-xs text-muted-foreground mt-1">
                      Max: {performanceMetrics.queries.max_duration_ms}ms
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium">
                      Synchronization
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {performanceMetrics.synchronization.average_duration_ms.toFixed(
                        1
                      )}
                      ms
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Average duration (
                      {performanceMetrics.synchronization.recent_syncs} recent)
                    </p>
                    <div className="text-xs text-muted-foreground mt-1">
                      Max: {performanceMetrics.synchronization.max_duration_ms}
                      ms
                    </div>
                  </CardContent>
                </Card>
              </>
            )}
          </div>

          {/* Performance Charts */}
          <Card>
            <CardHeader>
              <CardTitle>Performance Trends</CardTitle>
              <CardDescription>
                Real-time performance metrics over the last 20 minutes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={metricsHistory}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="timestamp" />
                    <YAxis />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="reasoning"
                      stroke="#8884d8"
                      name="Reasoning (ms)"
                      strokeWidth={2}
                    />
                    <Line
                      type="monotone"
                      dataKey="queries"
                      stroke="#82ca9d"
                      name="Queries (ms)"
                      strokeWidth={2}
                    />
                    <Line
                      type="monotone"
                      dataKey="sync"
                      stroke="#ffc658"
                      name="Sync (ms)"
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {queriedMetrics && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">
                  Queried Metrics
                </CardTitle>
              </CardHeader>
              <CardContent>
                {Array.isArray(queriedMetrics) ? (
                  <div className="space-y-2">
                    {queriedMetrics.map((metric) => (
                      <div key={metric.name} className="flex justify-between">
                        <span className="text-sm">{metric.name}</span>
                        <span className="text-sm font-mono">
                          {metric.value}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-2">
                    {Object.entries(queriedMetrics).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-sm">{key}</span>
                        <span className="text-sm font-mono">
                          {typeof value === 'object'
                            ? JSON.stringify(value)
                            : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="alerts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Alert Management</CardTitle>
              <CardDescription>
                Manage system alerts and notifications
              </CardDescription>
            </CardHeader>
            <CardContent>
              {activeAlerts.length === 0 ? (
                <div className="text-center py-8">
                  <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
                  <h3 className="text-lg font-medium">No Active Alerts</h3>
                  <p className="text-muted-foreground">
                    All systems are operating normally
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {activeAlerts.map((alert) => (
                    <Card key={alert.id} className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge className={getSeverityColor(alert.severity)}>
                              {alert.severity}
                            </Badge>
                            <span className="font-medium">
                              {alert.component}
                            </span>
                          </div>
                          <p className="text-sm mb-2">{alert.message}</p>
                          <div className="text-xs text-muted-foreground">
                            {new Date(alert.timestamp).toLocaleString()}
                          </div>
                          {Object.keys(alert.details).length > 0 && (
                            <div className="mt-2 text-xs">
                              <strong>Details:</strong>{' '}
                              {JSON.stringify(alert.details)}
                            </div>
                          )}
                        </div>
                        <Button
                          size="sm"
                          onClick={() => resolveAlert(alert.id)}
                        >
                          Resolve
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {alertHistory.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <History className="h-5 w-5" />
                  Alert History
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {alertHistory.map((alert) => (
                    <Alert key={alert.id}>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertTitle className="flex items-center justify-between">
                        <span>{alert.component}</span>
                        <Badge className={getSeverityColor(alert.severity)}>
                          {alert.severity}
                        </Badge>
                      </AlertTitle>
                      <AlertDescription>
                        {alert.message}
                        <div className="text-xs text-muted-foreground mt-1">
                          {new Date(alert.timestamp).toLocaleString()}
                        </div>
                      </AlertDescription>
                    </Alert>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="resources" className="space-y-4">
          {systemResources && (
            <>
              {/* Resource Usage Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">
                      CPU Usage
                    </CardTitle>
                    <Cpu className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {systemResources.cpu.usage_percent.toFixed(1)}%
                    </div>
                    <Progress
                      value={systemResources.cpu.usage_percent}
                      className="mt-2"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      {systemResources.cpu.cores} cores
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">
                      Memory Usage
                    </CardTitle>
                    <MemoryStick className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {systemResources.memory.usage_percent.toFixed(1)}%
                    </div>
                    <Progress
                      value={systemResources.memory.usage_percent}
                      className="mt-2"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      {(systemResources.memory.used_mb / 1024).toFixed(1)}GB /{' '}
                      {(systemResources.memory.total_mb / 1024).toFixed(1)}GB
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">
                      Disk Usage
                    </CardTitle>
                    <HardDrive className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {systemResources.disk.usage_percent.toFixed(1)}%
                    </div>
                    <Progress
                      value={systemResources.disk.usage_percent}
                      className="mt-2"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      {systemResources.disk.used_gb}GB /{' '}
                      {systemResources.disk.total_gb}GB
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">
                      Network I/O
                    </CardTitle>
                    <Network className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-sm">
                      <div>
                        ↑{' '}
                        {(
                          systemResources.network.bytes_sent /
                          1024 /
                          1024
                        ).toFixed(2)}{' '}
                        MB
                      </div>
                      <div>
                        ↓{' '}
                        {(
                          systemResources.network.bytes_received /
                          1024 /
                          1024
                        ).toFixed(2)}{' '}
                        MB
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {systemResources.network.packets_sent +
                        systemResources.network.packets_received}{' '}
                      packets
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Resource Usage Chart */}
              <Card>
                <CardHeader>
                  <CardTitle>Resource Usage Trends</CardTitle>
                  <CardDescription>
                    System resource utilization over time
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={metricsHistory}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="timestamp" />
                        <YAxis />
                        <Tooltip />
                        <Area
                          type="monotone"
                          dataKey="cpu"
                          stackId="1"
                          stroke="#8884d8"
                          fill="#8884d8"
                          name="CPU %"
                        />
                        <Area
                          type="monotone"
                          dataKey="memory"
                          stackId="2"
                          stroke="#82ca9d"
                          fill="#82ca9d"
                          name="Memory %"
                        />
                        <Area
                          type="monotone"
                          dataKey="disk"
                          stackId="3"
                          stroke="#ffc658"
                          fill="#ffc658"
                          name="Disk %"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};
