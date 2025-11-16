import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Activity,
  Clock,
  Cpu,
  MemoryStick,
  Zap,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
} from 'lucide-react';
import { useGraphPerformance } from '@/hooks/useGraphPerformance';
import {
  backgroundTaskManager,
  TaskStatus,
  QueueStatus,
} from '@/services/backgroundTaskManager';
import { Node, Edge, Viewport } from 'reactflow';

interface PerformanceMonitorProps {
  nodes: Node[];
  edges: Edge[];
  viewport: Viewport;
  className?: string;
}

interface TaskInfo {
  id: string;
  name: string;
  status: TaskStatus;
  progress: number;
  type: string;
}

/**
 * Performance Monitor Component
 *
 * Displays real-time performance metrics, alerts, and optimization suggestions
 */
export const PerformanceMonitor: React.FC<PerformanceMonitorProps> = ({
  nodes,
  edges,
  viewport,
  className = '',
}) => {
  const {
    metrics,
    metricsHistory,
    alerts,
    optimizationSuggestions,
    clearAlerts,
    getPerformanceSummary,
  } = useGraphPerformance(nodes, edges, viewport);

  const [queueStatus, setQueueStatus] = useState<QueueStatus>({
    queueSize: 0,
    pendingTasks: 0,
    runningTasks: 0,
    completedTasks: 0,
    failedTasks: 0,
    totalTasks: 0,
  });

  const [activeTasks, setActiveTasks] = useState<TaskInfo[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);

  // Update queue status periodically
  useEffect(() => {
    const updateQueueStatus = () => {
      setQueueStatus(backgroundTaskManager.getQueueStatus());
    };

    updateQueueStatus();
    const interval = setInterval(updateQueueStatus, 1000);
    return () => clearInterval(interval);
  }, []);

  // Performance summary
  const summary = getPerformanceSummary();

  // Get status color
  const getStatusColor = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.COMPLETED:
        return 'bg-green-500';
      case TaskStatus.RUNNING:
        return 'bg-blue-500';
      case TaskStatus.FAILED:
        return 'bg-red-500';
      case TaskStatus.CANCELLED:
        return 'bg-gray-500';
      default:
        return 'bg-yellow-500';
    }
  };

  // Get performance status
  const getPerformanceStatus = () => {
    if (alerts.some((a) => a.severity === 'error')) return 'error';
    if (alerts.some((a) => a.severity === 'warning')) return 'warning';
    return 'good';
  };

  const performanceStatus = getPerformanceStatus();

  if (!isExpanded) {
    // Compact view
    return (
      <Card className={`w-80 ${className}`}>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Performance
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(true)}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          {/* Status indicator */}
          <div className="flex items-center gap-2">
            {performanceStatus === 'good' && (
              <CheckCircle className="h-4 w-4 text-green-500" />
            )}
            {performanceStatus === 'warning' && (
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
            )}
            {performanceStatus === 'error' && (
              <XCircle className="h-4 w-4 text-red-500" />
            )}
            <span className="text-sm">
              {performanceStatus === 'good' && 'Performance Good'}
              {performanceStatus === 'warning' && 'Performance Issues'}
              {performanceStatus === 'error' && 'Performance Critical'}
            </span>
          </div>

          {/* Key metrics */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <div className="text-gray-500">Nodes</div>
              <div>
                {metrics.visibleNodeCount}/{metrics.nodeCount}
              </div>
            </div>
            <div>
              <div className="text-gray-500">FPS</div>
              <div>{metrics.fps}</div>
            </div>
            <div>
              <div className="text-gray-500">Render</div>
              <div>{metrics.renderTime.toFixed(1)}ms</div>
            </div>
            <div>
              <div className="text-gray-500">Tasks</div>
              <div>
                {queueStatus.runningTasks}/{queueStatus.totalTasks}
              </div>
            </div>
          </div>

          {/* Alerts */}
          {alerts.length > 0 && (
            <Alert className="py-2">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="text-xs">
                {alerts.length} performance alert{alerts.length > 1 ? 's' : ''}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    );
  }

  // Expanded view
  return (
    <Card className={`w-96 ${className}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Performance Monitor
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(false)}
          >
            ×
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="metrics" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="metrics">Metrics</TabsTrigger>
            <TabsTrigger value="tasks">Tasks</TabsTrigger>
            <TabsTrigger value="alerts">Alerts</TabsTrigger>
            <TabsTrigger value="optimize">Optimize</TabsTrigger>
          </TabsList>

          <TabsContent value="metrics" className="space-y-4">
            {/* Real-time metrics */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4" />
                  <span className="text-sm font-medium">Rendering</span>
                </div>
                <div className="text-xs text-gray-500">
                  {metrics.renderTime.toFixed(1)}ms
                </div>
                <Progress
                  value={Math.min(100, (metrics.renderTime / 16) * 100)}
                  className="h-2"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4" />
                  <span className="text-sm font-medium">FPS</span>
                </div>
                <div className="text-xs text-gray-500">{metrics.fps}</div>
                <Progress value={(metrics.fps / 60) * 100} className="h-2" />
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <MemoryStick className="h-4 w-4" />
                  <span className="text-sm font-medium">Memory</span>
                </div>
                <div className="text-xs text-gray-500">
                  {metrics.memoryUsage.toFixed(1)}MB
                </div>
                <Progress
                  value={Math.min(100, (metrics.memoryUsage / 100) * 100)}
                  className="h-2"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  <span className="text-sm font-medium">Nodes</span>
                </div>
                <div className="text-xs text-gray-500">
                  {metrics.visibleNodeCount}/{metrics.nodeCount}
                </div>
                <Progress
                  value={
                    (metrics.visibleNodeCount /
                      Math.max(metrics.nodeCount, 1)) *
                    100
                  }
                  className="h-2"
                />
              </div>
            </div>

            {/* Performance summary */}
            {summary && (
              <div className="border rounded p-3 space-y-2">
                <div className="text-sm font-medium">Performance Summary</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>Avg Render: {summary.avgRenderTime.toFixed(1)}ms</div>
                  <div>Avg FPS: {summary.avgFps.toFixed(0)}</div>
                  <div>Max Memory: {summary.maxMemory.toFixed(1)}MB</div>
                  <div>Alerts: {summary.alertCount}</div>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="tasks" className="space-y-4">
            {/* Queue status */}
            <div className="border rounded p-3">
              <div className="text-sm font-medium mb-2">Task Queue</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>Pending: {queueStatus.pendingTasks}</div>
                <div>Running: {queueStatus.runningTasks}</div>
                <div>Completed: {queueStatus.completedTasks}</div>
                <div>Failed: {queueStatus.failedTasks}</div>
              </div>
            </div>

            {/* Active tasks */}
            <div className="space-y-2">
              <div className="text-sm font-medium">Active Tasks</div>
              {queueStatus.runningTasks === 0 ? (
                <div className="text-xs text-gray-500">No active tasks</div>
              ) : (
                <div className="space-y-2">
                  {/* Placeholder for active tasks - would be populated from actual task data */}
                  <div className="border rounded p-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs">Graph Analysis</span>
                      <Badge variant="secondary" className="text-xs">
                        Running
                      </Badge>
                    </div>
                    <Progress value={65} className="h-1 mt-1" />
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="alerts" className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium">Performance Alerts</div>
              {alerts.length > 0 && (
                <Button variant="outline" size="sm" onClick={clearAlerts}>
                  Clear All
                </Button>
              )}
            </div>

            {alerts.length === 0 ? (
              <div className="text-xs text-gray-500">No alerts</div>
            ) : (
              <div className="space-y-2">
                {alerts.slice(-5).map((alert, index) => (
                  <Alert
                    key={index}
                    className={
                      alert.severity === 'error'
                        ? 'border-red-200'
                        : 'border-yellow-200'
                    }
                  >
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription className="text-xs">
                      <div className="font-medium">
                        {alert.type.replace('_', ' ').toUpperCase()}
                      </div>
                      <div>{alert.message}</div>
                      <div className="text-gray-500 mt-1">
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </div>
                    </AlertDescription>
                  </Alert>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="optimize" className="space-y-4">
            <div className="text-sm font-medium">Optimization Suggestions</div>

            {optimizationSuggestions.length === 0 ? (
              <div className="text-xs text-gray-500">
                No suggestions available
              </div>
            ) : (
              <div className="space-y-2">
                {optimizationSuggestions.map((suggestion, index) => (
                  <div key={index} className="border rounded p-2">
                    <div className="text-xs">{suggestion}</div>
                  </div>
                ))}
              </div>
            )}

            {/* Quick actions */}
            <div className="space-y-2">
              <div className="text-sm font-medium">Quick Actions</div>
              <div className="grid grid-cols-2 gap-2">
                <Button variant="outline" size="sm" className="text-xs">
                  Enable Clustering
                </Button>
                <Button variant="outline" size="sm" className="text-xs">
                  Reduce Node Count
                </Button>
                <Button variant="outline" size="sm" className="text-xs">
                  Clear Cache
                </Button>
                <Button variant="outline" size="sm" className="text-xs">
                  Optimize Layout
                </Button>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};

export default PerformanceMonitor;
