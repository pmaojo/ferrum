import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Bell,
  BellOff,
  X,
  CheckCircle,
  AlertTriangle,
  Info,
  Zap,
  FileText,
  GitBranch,
  Users,
  Settings,
  Volume2,
  VolumeX,
  Eye,
  EyeOff,
} from 'lucide-react';
import { useRealtimeSync } from '@/hooks/useRealtimeSync';
import { useToast } from '@/hooks/use-toast';
import { formatDistanceToNow } from 'date-fns';

interface NotificationSettings {
  enabled: boolean;
  soundEnabled: boolean;
  showDesktopNotifications: boolean;
  eventTypes: {
    sync_completed: boolean;
    sync_error: boolean;
    validation_completed: boolean;
    agent_triggered: boolean;
    file_changed: boolean;
    graph_updated: boolean;
    collaboration_event: boolean;
  };
  priority: {
    high: boolean;
    medium: boolean;
    low: boolean;
  };
}

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: string;
  eventType: string;
  priority: 'high' | 'medium' | 'low';
  read: boolean;
  dismissed: boolean;
  data?: Record<string, any>;
}

interface RealtimeNotificationSystemProps {
  projectId: string;
  className?: string;
}

/**
 * @kthulu:extend - Real-time notification system for Kthulu-PermaGraph integration
 * Manages notifications, alerts, and user preferences for real-time events
 */
export function RealtimeNotificationSystem({
  projectId,
  className,
}: RealtimeNotificationSystemProps) {
  const { toast } = useToast();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [settings, setSettings] = useState<NotificationSettings>({
    enabled: true,
    soundEnabled: true,
    showDesktopNotifications: true,
    eventTypes: {
      sync_completed: true,
      sync_error: true,
      validation_completed: true,
      agent_triggered: true,
      file_changed: false,
      graph_updated: true,
      collaboration_event: true,
    },
    priority: {
      high: true,
      medium: true,
      low: false,
    },
  });
  const [showSettings, setShowSettings] = useState(false);

  const { isConnected, events, lastEvent } = useRealtimeSync({
    projectId,
    subscriptions: ['*'],
    onEvent: handleRealtimeEvent,
  });

  function handleRealtimeEvent(event: any) {
    if (!settings.enabled) return;

    const notification = createNotificationFromEvent(event);
    if (!notification) return;

    // Check if event type is enabled
    if (
      !settings.eventTypes[event.eventType as keyof typeof settings.eventTypes]
    )
      return;

    // Check if priority is enabled
    if (!settings.priority[notification.priority]) return;

    addNotification(notification);

    // Show desktop notification if enabled
    if (settings.showDesktopNotifications && 'Notification' in window) {
      showDesktopNotification(notification);
    }

    // Play sound if enabled
    if (settings.soundEnabled) {
      playNotificationSound(notification.type);
    }
  }

  const createNotificationFromEvent = useCallback(
    (event: any): Notification | null => {
      const baseNotification = {
        id: `${event.eventType}-${Date.now()}`,
        timestamp: event.timestamp || new Date().toISOString(),
        eventType: event.eventType,
        read: false,
        dismissed: false,
        data: event.data,
      };

      switch (event.eventType) {
        case 'sync_completed':
          return {
            ...baseNotification,
            type: event.data.success ? 'success' : 'error',
            title: event.data.success ? 'Sync Completed' : 'Sync Failed',
            message: event.data.success
              ? `Successfully processed ${event.data.filesProcessed} files in ${event.data.duration?.toFixed(2)}s`
              : 'Synchronization encountered errors',
            priority: event.data.success ? 'low' : 'high',
          };

        case 'sync_error':
          return {
            ...baseNotification,
            type: 'error',
            title: 'Synchronization Error',
            message:
              event.data.error || 'An error occurred during synchronization',
            priority: 'high',
          };

        case 'validation_completed':
          return {
            ...baseNotification,
            type: event.data.isConsistent ? 'success' : 'warning',
            title: 'Validation Completed',
            message: event.data.isConsistent
              ? 'Architecture validation passed'
              : `Found ${event.data.violationCount} architectural violations`,
            priority: event.data.isConsistent ? 'low' : 'medium',
          };

        case 'agent_triggered':
          return {
            ...baseNotification,
            type: 'info',
            title: 'Agent Activated',
            message: `${event.data.agentType} agent triggered: ${event.data.reason}`,
            priority: 'medium',
          };

        case 'file_changed':
          return {
            ...baseNotification,
            type: 'info',
            title: 'File Changed',
            message: `${event.data.filePath} was ${event.data.changeType}`,
            priority: 'low',
          };

        case 'graph_updated':
          return {
            ...baseNotification,
            type: 'info',
            title: 'Graph Updated',
            message: `${event.data.totalChanges || 0} changes to the semantic graph`,
            priority: 'low',
          };

        case 'user_joined':
          return {
            ...baseNotification,
            type: 'info',
            title: 'User Joined',
            message: `${event.data.userName} joined the collaboration`,
            priority: 'low',
          };

        case 'conflict_detected':
          return {
            ...baseNotification,
            type: 'warning',
            title: 'Edit Conflict',
            message: `Conflict detected in ${event.data.fileName}`,
            priority: 'high',
          };

        default:
          return null;
      }
    },
    []
  );

  const addNotification = useCallback((notification: Notification) => {
    setNotifications((prev) => [notification, ...prev.slice(0, 99)]); // Keep max 100 notifications
  }, []);

  const showDesktopNotification = useCallback((notification: Notification) => {
    if (Notification.permission === 'granted') {
      const desktopNotification = new Notification(notification.title, {
        body: notification.message,
        icon: '/favicon.ico',
        tag: notification.id,
      });

      desktopNotification.onclick = () => {
        window.focus();
        markAsRead(notification.id);
        desktopNotification.close();
      };

      // Auto close after 5 seconds
      setTimeout(() => desktopNotification.close(), 5000);
    }
  }, []);

  const playNotificationSound = useCallback((type: string) => {
    // In a real implementation, you would play different sounds for different types
    const audio = new Audio('/notification-sound.mp3');
    audio.volume = 0.3;
    audio.play().catch(() => {
      // Ignore audio play errors (user interaction required)
    });
  }, []);

  const markAsRead = useCallback((notificationId: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === notificationId ? { ...n, read: true } : n))
    );
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const dismissNotification = useCallback((notificationId: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === notificationId ? { ...n, dismissed: true } : n))
    );
  }, []);

  const clearAllNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const requestNotificationPermission = useCallback(async () => {
    if ('Notification' in window && Notification.permission === 'default') {
      const permission = await Notification.requestPermission();
      if (permission === 'granted') {
        toast({
          title: 'Notifications Enabled',
          description: "You'll now receive desktop notifications",
        });
      }
    }
  }, [toast]);

  const updateSettings = useCallback(
    (newSettings: Partial<NotificationSettings>) => {
      setSettings((prev) => ({ ...prev, ...newSettings }));
    },
    []
  );

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'info':
        return <Info className="h-4 w-4 text-blue-500" />;
      default:
        return <Bell className="h-4 w-4 text-gray-500" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'border-l-red-500';
      case 'medium':
        return 'border-l-yellow-500';
      case 'low':
        return 'border-l-blue-500';
      default:
        return 'border-l-gray-500';
    }
  };

  const visibleNotifications = notifications.filter((n) => !n.dismissed);
  const unreadCount = visibleNotifications.filter((n) => !n.read).length;

  // Request notification permission on mount
  useEffect(() => {
    if (
      settings.showDesktopNotifications &&
      'Notification' in window &&
      Notification.permission === 'default'
    ) {
      requestNotificationPermission();
    }
  }, [settings.showDesktopNotifications, requestNotificationPermission]);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Notification Header */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {settings.enabled ? (
                <Bell className="h-5 w-5 text-blue-500" />
              ) : (
                <BellOff className="h-5 w-5 text-gray-400" />
              )}
              <div>
                <CardTitle className="text-lg">Notifications</CardTitle>
                <CardDescription>
                  {isConnected
                    ? 'Real-time notifications active'
                    : 'Disconnected from notification service'}
                </CardDescription>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              {unreadCount > 0 && (
                <Badge variant="destructive">{unreadCount} unread</Badge>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowSettings(!showSettings)}
              >
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>

        {/* Quick Actions */}
        <CardContent className="pt-0">
          <div className="flex space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={markAllAsRead}
              disabled={unreadCount === 0}
            >
              Mark All Read
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={clearAllNotifications}
              disabled={visibleNotifications.length === 0}
            >
              Clear All
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => updateSettings({ enabled: !settings.enabled })}
            >
              {settings.enabled ? (
                <>
                  <BellOff className="h-4 w-4 mr-1" />
                  Disable
                </>
              ) : (
                <>
                  <Bell className="h-4 w-4 mr-1" />
                  Enable
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Settings Panel */}
      {showSettings && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Notification Settings</CardTitle>
            <CardDescription>
              Customize your notification preferences
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* General Settings */}
            <div className="space-y-4">
              <h4 className="font-medium">General</h4>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Volume2 className="h-4 w-4" />
                    <span className="text-sm">Sound notifications</span>
                  </div>
                  <Switch
                    checked={settings.soundEnabled}
                    onCheckedChange={(checked) =>
                      updateSettings({ soundEnabled: checked })
                    }
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Bell className="h-4 w-4" />
                    <span className="text-sm">Desktop notifications</span>
                  </div>
                  <Switch
                    checked={settings.showDesktopNotifications}
                    onCheckedChange={(checked) =>
                      updateSettings({ showDesktopNotifications: checked })
                    }
                  />
                </div>
              </div>
            </div>

            <Separator />

            {/* Event Types */}
            <div className="space-y-4">
              <h4 className="font-medium">Event Types</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(settings.eventTypes).map(
                  ([eventType, enabled]) => (
                    <div
                      key={eventType}
                      className="flex items-center justify-between"
                    >
                      <span className="text-sm capitalize">
                        {eventType.replace('_', ' ')}
                      </span>
                      <Switch
                        checked={enabled}
                        onCheckedChange={(checked) =>
                          updateSettings({
                            eventTypes: {
                              ...settings.eventTypes,
                              [eventType]: checked,
                            },
                          })
                        }
                      />
                    </div>
                  )
                )}
              </div>
            </div>

            <Separator />

            {/* Priority Levels */}
            <div className="space-y-4">
              <h4 className="font-medium">Priority Levels</h4>
              <div className="space-y-3">
                {Object.entries(settings.priority).map(
                  ([priority, enabled]) => (
                    <div
                      key={priority}
                      className="flex items-center justify-between"
                    >
                      <div className="flex items-center space-x-2">
                        <div
                          className={`w-3 h-3 rounded-full ${
                            priority === 'high'
                              ? 'bg-red-500'
                              : priority === 'medium'
                                ? 'bg-yellow-500'
                                : 'bg-blue-500'
                          }`}
                        />
                        <span className="text-sm capitalize">
                          {priority} priority
                        </span>
                      </div>
                      <Switch
                        checked={enabled}
                        onCheckedChange={(checked) =>
                          updateSettings({
                            priority: {
                              ...settings.priority,
                              [priority]: checked,
                            },
                          })
                        }
                      />
                    </div>
                  )
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Notifications List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recent Notifications</CardTitle>
          <CardDescription>
            {visibleNotifications.length} notifications â¢ {unreadCount} unread
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-96">
            {visibleNotifications.length > 0 ? (
              <div className="space-y-3">
                {visibleNotifications.map((notification) => (
                  <div
                    key={notification.id}
                    className={`p-3 border-l-4 rounded-r-lg ${
                      notification.read ? 'bg-gray-50' : 'bg-white border-2'
                    } ${getPriorityColor(notification.priority)}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-3 flex-1">
                        {getNotificationIcon(notification.type)}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <h4
                              className={`text-sm font-medium ${
                                notification.read
                                  ? 'text-gray-700'
                                  : 'text-gray-900'
                              }`}
                            >
                              {notification.title}
                            </h4>
                            {!notification.read && (
                              <div className="w-2 h-2 bg-blue-500 rounded-full" />
                            )}
                          </div>
                          <p
                            className={`text-sm mt-1 ${
                              notification.read
                                ? 'text-gray-500'
                                : 'text-gray-700'
                            }`}
                          >
                            {notification.message}
                          </p>
                          <div className="flex items-center space-x-2 mt-2">
                            <Badge variant="outline" className="text-xs">
                              {notification.eventType}
                            </Badge>
                            <span className="text-xs text-gray-500">
                              {formatDistanceToNow(
                                new Date(notification.timestamp),
                                { addSuffix: true }
                              )}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-1 ml-2">
                        {!notification.read && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => markAsRead(notification.id)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => dismissNotification(notification.id)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Bell className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <p className="text-sm text-gray-500">No notifications yet</p>
                <p className="text-xs text-gray-400 mt-1">
                  You'll see real-time updates here when they occur
                </p>
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
