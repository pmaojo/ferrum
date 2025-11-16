import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Activity, 
  Wifi, 
  WifiOff, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Users,
  Database,
  Zap,
  TrendingUp,
  FileText,
  GitBranch
} from 'lucide-react';
import { useRealtimeSync, useRealtimeSyncStatus } from '@/hooks/useRealtimeSync';
import { formatDistanceToNow } from 'date-fns';

interface RealtimeSystemStatusProps {
  projectId: string;
  className?: string;
}

/**
 * @kthulu:extend - Real-time system status component for Kthulu-PermaGraph integration
 * Shows connection status, sync metrics, and recent activity
 */
export function RealtimeSystemStatus({ projectId, className }: RealtimeSystemStatusProps) {
  const [selectedTab, setSelectedTab] = useState('overview');
  
  const {
    isConnected,
    isConnecting,
    error,
    metrics,
    connectedClients,
    events,
    lastEvent,
    forceSync,
    clearEvents,
    getEventsByType,
    getRecentEvents,
    successRate,
    isHealthy,
    hasRecentActivity
  } = useRealtimeSync({
    projectId,
    subscriptions: ['*'],
    maxEvents: 100
  });
  
  const getConnectionStatus = () => {
    if (isConnecting) return { status: 'connecting', color: 'yellow', icon: RefreshCw };
    if (isConnected) return { status: 'connected', color: 'green', icon: Wifi };
    return { status: 'disconnected', color: 'red', icon: WifiOff };
  };
  
  const connectionInfo = getConnectionStatus();
  
  const getHealthStatus = () => {
    if (!isConnected) return { status: 'offline', color: 'red', text: 'Offline' };
    if (error) return { status: 'error', color: 'red', text: 'Error' };
    if (hasRecentActivity) return { status: 'active', color: 'green', text: 'Active' };
    return { status: 'idle', color: 'yellow', text: 'Idle' };
  };
  
  const healthInfo = getHealthStatus();
  
  const recentSyncEvents = getEventsByType('sync_completed').slice(0, 5);
  const recentValidationEvents = getEventsByType('validation_completed').slice(0, 5);
  const recentErrors = getEventsByType('sync_error').slice(0, 5);
  
  const formatEventTime = (timestamp: string) => {
    return formatDistanceToNow(new Date(timestamp), { addSuffix: true });
  };
  
  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'sync_started': return <RefreshCw className="h-4 w-4 text-blue-500" />;
      case 'sync_completed': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'sync_error': return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'file_changed': return <FileText className="h-4 w-4 text-orange-500" />;
      case 'graph_updated': return <GitBranch className="h-4 w-4 text-purple-500" />;
      case 'validation_completed': return <CheckCircle className="h-4 w-4 text-blue-500" />;
      case 'agent_triggered': return <Zap className="h-4 w-4 text-yellow-500" />;
      default: return <Activity className="h-4 w-4 text-gray-500" />;
    }
  };
  
  return (
    <div className={`space-y-6 ${className}`}>
      {/* Connection Status Header */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <connectionInfo.icon 
                className={`h-5 w-5 ${
                  connectionInfo.color === 'green' ? 'text-green-500' :
                  connectionInfo.color === 'yellow' ? 'text-yellow-500 animate-spin' :
                  'text-red-500'
                }`} 
              />
              <div>
                <CardTitle className="text-lg">Real-time Sync Status</CardTitle>
                <CardDescription>
                  Project: {projectId} • {connectedClients} clients connected
                </CardDescription>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Badge 
                variant={healthInfo.color === 'green' ? 'default' : 'destructive'}
                className={
                  healthInfo.color === 'green' ? 'bg-green-100 text-green-800' :
                  healthInfo.color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }
              >
                {healthInfo.text}
              </Badge>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={forceSync}
                disabled={!isConnected}
              >
                <RefreshCw className="h-4 w-4 mr-1" />
                Force Sync
              </Button>
            </div>
          </div>
        </CardHeader>
        
        {error && (
          <CardContent className="pt-0">
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-4 w-4 text-red-500" />
                <span className="text-sm text-red-700">{error}</span>
              </div>
            </div>
          </CardContent>
        )}
      </Card>
      
      {/* Metrics Overview */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <TrendingUp className="h-4 w-4 text-green-500" />
                <div>
                  <p className="text-sm font-medium text-gray-600">Success Rate</p>
                  <p className="text-2xl font-bold text-green-600">{successRate.toFixed(1)}%</p>
                </div>
              </div>
              <Progress value={successRate} className="mt-2" />
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <RefreshCw className="h-4 w-4 text-blue-500" />
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Syncs</p>
                  <p className="text-2xl font-bold">{metrics.totalSyncs}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <Clock className="h-4 w-4 text-orange-500" />
                <div>
                  <p className="text-sm font-medium text-gray-600">Avg Time</p>
                  <p className="text-2xl font-bold">{metrics.averageSyncTime.toFixed(2)}s</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <FileText className="h-4 w-4 text-purple-500" />
                <div>
                  <p className="text-sm font-medium text-gray-600">Files Processed</p>
                  <p className="text-2xl font-bold">{metrics.filesProcessed}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
      
      {/* Detailed Information Tabs */}
      <Card>
        <CardHeader>
          <CardTitle>System Activity</CardTitle>
          <CardDescription>
            Real-time events and system information
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={selectedTab} onValueChange={setSelectedTab}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="events">Events</TabsTrigger>
              <TabsTrigger value="metrics">Metrics</TabsTrigger>
              <TabsTrigger value="errors">Errors</TabsTrigger>
            </TabsList>
            
            <TabsContent value="overview" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <h4 className="font-medium flex items-center space-x-2">
                    <Activity className="h-4 w-4" />
                    <span>Recent Activity</span>
                  </h4>
                  <ScrollArea className="h-48 border rounded-md p-3">
                    {getRecentEvents(10).map((event, index) => (
                      <div key={index} className="flex items-center space-x-3 py-2 border-b last:border-b-0">
                        {getEventIcon(event.eventType)}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{event.eventType}</p>
                          <p className="text-xs text-gray-500">{formatEventTime(event.timestamp)}</p>
                        </div>
                      </div>
                    ))}
                    {events.length === 0 && (
                      <p className="text-sm text-gray-500 text-center py-4">No recent activity</p>
                    )}
                  </ScrollArea>
                </div>
                
                <div className="space-y-3">
                  <h4 className="font-medium flex items-center space-x-2">
                    <Database className="h-4 w-4" />
                    <span>System Info</span>
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Connection Status:</span>
                      <Badge variant={isConnected ? 'default' : 'destructive'}>
                        {connectionInfo.status}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Connected Clients:</span>
                      <span className="font-medium">{connectedClients}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Last Event:</span>
                      <span className="font-medium">
                        {lastEvent ? formatEventTime(lastEvent.timestamp) : 'None'}
                      </span>
                    </div>
                    {metrics?.lastSyncTime && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Last Sync:</span>
                        <span className="font-medium">
                          {formatEventTime(metrics.lastSyncTime)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="events" className="space-y-4">
              <div className="flex justify-between items-center">
                <h4 className="font-medium">All Events ({events.length})</h4>
                <Button variant="outline" size="sm" onClick={clearEvents}>
                  Clear Events
                </Button>
              </div>
              <ScrollArea className="h-96 border rounded-md p-3">
                {events.map((event, index) => (
                  <div key={index} className="border-b last:border-b-0 py-3">
                    <div className="flex items-start space-x-3">
                      {getEventIcon(event.eventType)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-sm">{event.eventType}</span>
                          <Badge variant="outline" className="text-xs">
                            {formatEventTime(event.timestamp)}
                          </Badge>
                        </div>
                        <div className="mt-1 text-xs text-gray-600">
                          {event.source && <span className="mr-2">Source: {event.source}</span>}
                          {event.correlationId && <span>ID: {event.correlationId}</span>}
                        </div>
                        {Object.keys(event.data).length > 0 && (
                          <details className="mt-2">
                            <summary className="text-xs text-blue-600 cursor-pointer">
                              Show details
                            </summary>
                            <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-x-auto">
                              {JSON.stringify(event.data, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {events.length === 0 && (
                  <p className="text-sm text-gray-500 text-center py-8">No events recorded</p>
                )}
              </ScrollArea>
            </TabsContent>
            
            <TabsContent value="metrics" className="space-y-4">
              {metrics ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h4 className="font-medium">Synchronization Metrics</h4>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Total Syncs:</span>
                        <span className="font-medium">{metrics.totalSyncs}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Successful:</span>
                        <span className="font-medium text-green-600">{metrics.successfulSyncs}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Failed:</span>
                        <span className="font-medium text-red-600">{metrics.failedSyncs}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Success Rate:</span>
                        <span className="font-medium">{successRate.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <h4 className="font-medium">Performance Metrics</h4>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Average Sync Time:</span>
                        <span className="font-medium">{metrics.averageSyncTime.toFixed(2)}s</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Files Processed:</span>
                        <span className="font-medium">{metrics.filesProcessed}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Triples Updated:</span>
                        <span className="font-medium">{metrics.triplesUpdated}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Violations Detected:</span>
                        <span className="font-medium text-orange-600">{metrics.violationsDetected}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-gray-500 text-center py-8">No metrics available</p>
              )}
            </TabsContent>
            
            <TabsContent value="errors" className="space-y-4">
              <h4 className="font-medium">Recent Errors ({recentErrors.length})</h4>
              <ScrollArea className="h-96 border rounded-md p-3">
                {recentErrors.map((event, index) => (
                  <div key={index} className="border-b last:border-b-0 py-3">
                    <div className="flex items-start space-x-3">
                      <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-sm text-red-700">Sync Error</span>
                          <Badge variant="destructive" className="text-xs">
                            {formatEventTime(event.timestamp)}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-700 mt-1">{event.data.error}</p>
                        {event.data.affectedFiles && (
                          <div className="mt-2">
                            <p className="text-xs text-gray-600">Affected files:</p>
                            <ul className="text-xs text-gray-600 ml-4 list-disc">
                              {event.data.affectedFiles.map((file: string, i: number) => (
                                <li key={i}>{file}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {recentErrors.length === 0 && (
                  <p className="text-sm text-gray-500 text-center py-8">No recent errors</p>
                )}
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}