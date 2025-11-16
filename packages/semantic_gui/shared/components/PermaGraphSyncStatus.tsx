import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Clock, XCircle, Wifi, WifiOff } from 'lucide-react';

interface SyncStatus {
  status: 'not_started' | 'in_progress' | 'success' | 'failed' | 'disabled';
  timestamp: string;
  version_id?: string;
  error?: string;
}

interface PermaGraphSyncStatusProps {
  projectPath?: string;
  className?: string;
}

export const PermaGraphSyncStatus: React.FC<PermaGraphSyncStatusProps> = ({
  projectPath = '.',
  className = '',
}) => {
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadSyncStatus = async () => {
      try {
        // In a real implementation, this would read from the .ferrum_sync_status.json file
        // For now, we'll simulate the status
        const response = await fetch(`/api/ferrum/sync-status?path=${encodeURIComponent(projectPath)}`);
        if (response.ok) {
          const status = await response.json();
          setSyncStatus(status);
        }
      } catch (error) {
        console.warn('Failed to load sync status:', error);
        setSyncStatus({
          status: 'not_started',
          timestamp: new Date().toISOString(),
        });
      } finally {
        setIsLoading(false);
      }
    };

    loadSyncStatus();
    
    // Poll for status updates every 5 seconds
    const interval = setInterval(loadSyncStatus, 5000);
    return () => clearInterval(interval);
  }, [projectPath]);

  if (isLoading) {
    return (
      <div className={`flex items-center space-x-2 text-gray-500 ${className}`}>
        <Clock className="w-4 h-4 animate-spin" />
        <span className="text-sm">Loading sync status...</span>
      </div>
    );
  }

  if (!syncStatus) {
    return null;
  }

  const getStatusIcon = () => {
    switch (syncStatus.status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'in_progress':
        return <Clock className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'disabled':
        return <WifiOff className="w-4 h-4 text-gray-400" />;
      default:
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
    }
  };  
const getStatusText = () => {
    switch (syncStatus.status) {
      case 'success':
        return `Synced to PermaGraph${syncStatus.version_id ? ` (v${syncStatus.version_id.slice(0, 8)})` : ''}`;
      case 'failed':
        return `Sync failed: ${syncStatus.error || 'Unknown error'}`;
      case 'in_progress':
        return 'Syncing to PermaGraph...';
      case 'disabled':
        return 'PermaGraph sync disabled';
      default:
        return 'Not synced';
    }
  };

  const getStatusColor = () => {
    switch (syncStatus.status) {
      case 'success':
        return 'text-green-600';
      case 'failed':
        return 'text-red-600';
      case 'in_progress':
        return 'text-blue-600';
      case 'disabled':
        return 'text-gray-500';
      default:
        return 'text-yellow-600';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch {
      return 'Unknown time';
    }
  };

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {getStatusIcon()}
      <div className="flex flex-col">
        <span className={`text-sm font-medium ${getStatusColor()}`}>
          {getStatusText()}
        </span>
        <span className="text-xs text-gray-400">
          {formatTimestamp(syncStatus.timestamp)}
        </span>
      </div>
    </div>
  );
};

export default PermaGraphSyncStatus;