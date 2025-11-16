import { useState, useEffect, useCallback, useRef } from 'react';
import { Node, Edge, Viewport } from 'reactflow';

interface PerformanceMetrics {
  renderTime: number;
  nodeCount: number;
  edgeCount: number;
  visibleNodeCount: number;
  visibleEdgeCount: number;
  memoryUsage: number;
  fps: number;
  lastUpdate: number;
}

interface PerformanceConfig {
  enableMonitoring: boolean;
  sampleInterval: number;
  maxSamples: number;
  performanceThresholds: {
    maxRenderTime: number;
    minFps: number;
    maxMemoryMB: number;
  };
}

interface PerformanceAlert {
  type: 'render_time' | 'fps' | 'memory' | 'node_count';
  message: string;
  severity: 'warning' | 'error';
  timestamp: number;
  value: number;
  threshold: number;
}

const defaultConfig: PerformanceConfig = {
  enableMonitoring: true,
  sampleInterval: 1000, // 1 second
  maxSamples: 60, // Keep 1 minute of data
  performanceThresholds: {
    maxRenderTime: 16, // 60 FPS target
    minFps: 30,
    maxMemoryMB: 100,
  },
};

/**
 * Hook for monitoring React Flow performance
 *
 * Features:
 * 1. Real-time performance metrics
 * 2. Performance alerts and warnings
 * 3. Automatic optimization suggestions
 * 4. Memory usage tracking
 * 5. FPS monitoring
 */
export const useGraphPerformance = (
  nodes: Node[],
  edges: Edge[],
  viewport: Viewport,
  config: Partial<PerformanceConfig> = {}
) => {
  const finalConfig = { ...defaultConfig, ...config };

  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    renderTime: 0,
    nodeCount: 0,
    edgeCount: 0,
    visibleNodeCount: 0,
    visibleEdgeCount: 0,
    memoryUsage: 0,
    fps: 60,
    lastUpdate: Date.now(),
  });

  const [metricsHistory, setMetricsHistory] = useState<PerformanceMetrics[]>(
    []
  );
  const [alerts, setAlerts] = useState<PerformanceAlert[]>([]);
  const [optimizationSuggestions, setOptimizationSuggestions] = useState<
    string[]
  >([]);

  const frameCountRef = useRef(0);
  const lastFrameTimeRef = useRef(performance.now());
  const renderStartTimeRef = useRef(0);
  const monitoringIntervalRef = useRef<NodeJS.Timeout>();

  // Start render timing
  const startRenderTiming = useCallback(() => {
    if (finalConfig.enableMonitoring) {
      renderStartTimeRef.current = performance.now();
    }
  }, [finalConfig.enableMonitoring]);

  // End render timing
  const endRenderTiming = useCallback(() => {
    if (finalConfig.enableMonitoring && renderStartTimeRef.current > 0) {
      const renderTime = performance.now() - renderStartTimeRef.current;

      setMetrics((prev) => ({
        ...prev,
        renderTime,
        lastUpdate: Date.now(),
      }));
    }
  }, [finalConfig.enableMonitoring]);

  // Calculate visible elements
  const calculateVisibleElements = useCallback(
    (allNodes: Node[], allEdges: Edge[], currentViewport: Viewport) => {
      const viewportBounds = {
        x: -currentViewport.x / currentViewport.zoom,
        y: -currentViewport.y / currentViewport.zoom,
        width: window.innerWidth / currentViewport.zoom,
        height: window.innerHeight / currentViewport.zoom,
      };

      const visibleNodes = allNodes.filter((node) => {
        const nodeX = node.position.x;
        const nodeY = node.position.y;
        const nodeWidth = node.width || 150;
        const nodeHeight = node.height || 50;

        return (
          nodeX + nodeWidth >= viewportBounds.x &&
          nodeX <= viewportBounds.x + viewportBounds.width &&
          nodeY + nodeHeight >= viewportBounds.y &&
          nodeY <= viewportBounds.y + viewportBounds.height
        );
      });

      const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));
      const visibleEdges = allEdges.filter(
        (edge) =>
          visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)
      );

      return {
        visibleNodeCount: visibleNodes.length,
        visibleEdgeCount: visibleEdges.length,
      };
    },
    []
  );

  // Get memory usage (if available)
  const getMemoryUsage = useCallback((): number => {
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      return memory.usedJSHeapSize / (1024 * 1024); // Convert to MB
    }
    return 0;
  }, []);

  // Calculate FPS
  const calculateFPS = useCallback(() => {
    frameCountRef.current++;
    const now = performance.now();
    const deltaTime = now - lastFrameTimeRef.current;

    if (deltaTime >= 1000) {
      // Update every second
      const fps = Math.round((frameCountRef.current * 1000) / deltaTime);
      frameCountRef.current = 0;
      lastFrameTimeRef.current = now;
      return fps;
    }

    return metrics.fps; // Return previous FPS if not time to update
  }, [metrics.fps]);

  // Check for performance alerts
  const checkPerformanceAlerts = useCallback(
    (currentMetrics: PerformanceMetrics) => {
      const newAlerts: PerformanceAlert[] = [];
      const { performanceThresholds } = finalConfig;

      // Check render time
      if (currentMetrics.renderTime > performanceThresholds.maxRenderTime) {
        newAlerts.push({
          type: 'render_time',
          message: `Render time (${currentMetrics.renderTime.toFixed(1)}ms) exceeds threshold (${performanceThresholds.maxRenderTime}ms)`,
          severity:
            currentMetrics.renderTime > performanceThresholds.maxRenderTime * 2
              ? 'error'
              : 'warning',
          timestamp: Date.now(),
          value: currentMetrics.renderTime,
          threshold: performanceThresholds.maxRenderTime,
        });
      }

      // Check FPS
      if (currentMetrics.fps < performanceThresholds.minFps) {
        newAlerts.push({
          type: 'fps',
          message: `FPS (${currentMetrics.fps}) below threshold (${performanceThresholds.minFps})`,
          severity:
            currentMetrics.fps < performanceThresholds.minFps / 2
              ? 'error'
              : 'warning',
          timestamp: Date.now(),
          value: currentMetrics.fps,
          threshold: performanceThresholds.minFps,
        });
      }

      // Check memory usage
      if (currentMetrics.memoryUsage > performanceThresholds.maxMemoryMB) {
        newAlerts.push({
          type: 'memory',
          message: `Memory usage (${currentMetrics.memoryUsage.toFixed(1)}MB) exceeds threshold (${performanceThresholds.maxMemoryMB}MB)`,
          severity:
            currentMetrics.memoryUsage > performanceThresholds.maxMemoryMB * 1.5
              ? 'error'
              : 'warning',
          timestamp: Date.now(),
          value: currentMetrics.memoryUsage,
          threshold: performanceThresholds.maxMemoryMB,
        });
      }

      // Check node count
      if (currentMetrics.visibleNodeCount > 1000) {
        newAlerts.push({
          type: 'node_count',
          message: `High visible node count (${currentMetrics.visibleNodeCount}) may impact performance`,
          severity:
            currentMetrics.visibleNodeCount > 2000 ? 'error' : 'warning',
          timestamp: Date.now(),
          value: currentMetrics.visibleNodeCount,
          threshold: 1000,
        });
      }

      if (newAlerts.length > 0) {
        setAlerts((prev) => [...prev.slice(-10), ...newAlerts]); // Keep last 10 alerts
      }
    },
    [finalConfig]
  );

  // Generate optimization suggestions
  const generateOptimizationSuggestions = useCallback(
    (currentMetrics: PerformanceMetrics) => {
      const suggestions: string[] = [];

      if (currentMetrics.visibleNodeCount > 500) {
        suggestions.push(
          'Enable node virtualization to improve rendering performance'
        );
      }

      if (currentMetrics.renderTime > 16) {
        suggestions.push(
          'Consider reducing node complexity or enabling clustering'
        );
      }

      if (currentMetrics.memoryUsage > 50) {
        suggestions.push(
          'High memory usage detected - consider implementing node recycling'
        );
      }

      if (currentMetrics.fps < 30) {
        suggestions.push(
          'Low FPS detected - try reducing visual effects or node count'
        );
      }

      if (currentMetrics.nodeCount > 1000 && viewport.zoom < 0.5) {
        suggestions.push(
          'Enable automatic clustering for better performance at low zoom levels'
        );
      }

      setOptimizationSuggestions(suggestions);
    },
    [viewport.zoom]
  );

  // Update metrics
  useEffect(() => {
    if (!finalConfig.enableMonitoring) return;

    const { visibleNodeCount, visibleEdgeCount } = calculateVisibleElements(
      nodes,
      edges,
      viewport
    );
    const fps = calculateFPS();
    const memoryUsage = getMemoryUsage();

    const newMetrics: PerformanceMetrics = {
      ...metrics,
      nodeCount: nodes.length,
      edgeCount: edges.length,
      visibleNodeCount,
      visibleEdgeCount,
      fps,
      memoryUsage,
      lastUpdate: Date.now(),
    };

    setMetrics(newMetrics);
    checkPerformanceAlerts(newMetrics);
    generateOptimizationSuggestions(newMetrics);

    // Add to history
    setMetricsHistory((prev) => {
      const newHistory = [...prev, newMetrics];
      return newHistory.slice(-finalConfig.maxSamples);
    });
  }, [
    nodes,
    edges,
    viewport,
    finalConfig.enableMonitoring,
    calculateVisibleElements,
    calculateFPS,
    getMemoryUsage,
    checkPerformanceAlerts,
    generateOptimizationSuggestions,
  ]);

  // Start monitoring interval
  useEffect(() => {
    if (finalConfig.enableMonitoring) {
      monitoringIntervalRef.current = setInterval(() => {
        // Trigger metrics update
        setMetrics((prev) => ({ ...prev, lastUpdate: Date.now() }));
      }, finalConfig.sampleInterval);

      return () => {
        if (monitoringIntervalRef.current) {
          clearInterval(monitoringIntervalRef.current);
        }
      };
    }
  }, [finalConfig.enableMonitoring, finalConfig.sampleInterval]);

  // Clear alerts
  const clearAlerts = useCallback(() => {
    setAlerts([]);
  }, []);

  // Get performance summary
  const getPerformanceSummary = useCallback(() => {
    if (metricsHistory.length === 0) return null;

    const recent = metricsHistory.slice(-10);
    const avgRenderTime =
      recent.reduce((sum, m) => sum + m.renderTime, 0) / recent.length;
    const avgFps = recent.reduce((sum, m) => sum + m.fps, 0) / recent.length;
    const maxMemory = Math.max(...recent.map((m) => m.memoryUsage));

    return {
      avgRenderTime,
      avgFps,
      maxMemory,
      alertCount: alerts.length,
      suggestionCount: optimizationSuggestions.length,
    };
  }, [metricsHistory, alerts.length, optimizationSuggestions.length]);

  return {
    metrics,
    metricsHistory,
    alerts,
    optimizationSuggestions,
    startRenderTiming,
    endRenderTiming,
    clearAlerts,
    getPerformanceSummary,
  };
};
