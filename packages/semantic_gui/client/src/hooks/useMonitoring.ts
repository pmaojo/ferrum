import { useState, useCallback } from 'react';

export interface MonitoringMetric {
  name: string;
  value: number | string;
  timestamp?: string;
  [key: string]: any;
}

export interface MonitoringAlert {
  id: string;
  severity: string;
  component: string;
  message: string;
  timestamp: string;
  [key: string]: any;
}

export interface ComponentStatus {
  status: string;
  message: string;
  timestamp: string;
  response_time_ms?: number;
  details?: Record<string, any>;
}

export type ComponentHealthMap = Record<string, ComponentStatus>;

/**
 * Hook for interacting with monitoring API endpoints
 */
export const useMonitoring = () => {
  const [metrics, setMetrics] = useState<
    Record<string, MonitoringMetric> | MonitoringMetric[] | null
  >(null);
  const [alertHistory, setAlertHistory] = useState<MonitoringAlert[]>([]);
  const [components, setComponents] = useState<ComponentHealthMap>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Query metrics
  const queryMetrics = useCallback(async (query: Record<string, any> = {}) => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/monitoring/metrics/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(query),
      });
      const data = await response.json();
      if (data.success === false) {
        setError(data.error || 'Failed to query metrics');
      } else {
        setMetrics(data.data || data.metrics || null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to query metrics');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch alert history
  const fetchAlertHistory = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/monitoring/alerts/history');
      const data = await response.json();
      if (data.success === false) {
        setError(data.error || 'Failed to fetch alert history');
      } else {
        setAlertHistory(data.data || data.history || []);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to fetch alert history'
      );
    }
  }, []);

  // Fetch health status of all components
  const fetchComponentHealth = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/monitoring/health/components');
      const data = await response.json();
      if (data.success === false) {
        setError(data.error || 'Failed to fetch component health');
      } else {
        setComponents(data.data || {});
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to fetch component health'
      );
    }
  }, []);

  // Manually check a component
  const checkComponent = useCallback(async (component: string) => {
    try {
      const response = await fetch(
        `/api/v1/monitoring/health/components/${component}/check`,
        {
          method: 'POST',
        }
      );
      const data = await response.json();
      if (data.success === false) {
        setError(data.error || 'Failed to check component');
      } else {
        setComponents((prev) => ({ ...prev, [component]: data.data }));
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to check component'
      );
    }
  }, []);

  return {
    metrics,
    alertHistory,
    components,
    loading,
    error,
    queryMetrics,
    fetchAlertHistory,
    fetchComponentHealth,
    checkComponent,
    clearError: () => setError(null),
  };
};

export default useMonitoring;
