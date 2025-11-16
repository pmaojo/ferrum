/**
 * Performance Monitor for Resource Usage and Optimization
 * Tracks service performance and provides optimization recommendations
 */

export interface PerformanceMetrics {
  timestamp: number;
  service: string;
  responseTime: number;
  memoryUsage: number;
  cpuUsage: number;
  requestCount: number;
  errorCount: number;
  cacheHitRate: number;
}

export interface OptimizationRecommendation {
  type: 'memory' | 'cpu' | 'cache' | 'network' | 'service';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  action: string;
  impact: string;
}

export interface ResourceUsage {
  memory: {
    used: number;
    total: number;
    percentage: number;
  };
  cpu: {
    usage: number;
    cores: number;
  };
  network: {
    bytesIn: number;
    bytesOut: number;
    connectionsActive: number;
  };
  services: {
    [serviceName: string]: {
      status: 'healthy' | 'degraded' | 'unhealthy';
      responseTime: number;
      uptime: number;
    };
  };
}

export class PerformanceMonitor {
  private metrics: Map<string, PerformanceMetrics[]> = new Map();
  private readonly MAX_METRICS_PER_SERVICE = 100;
  private monitoringInterval: NodeJS.Timeout | null = null;
  private readonly MONITORING_INTERVAL = 10000; // 10 seconds

  constructor() {
    this.startMonitoring();
  }

  private startMonitoring() {
    this.monitoringInterval = setInterval(() => {
      this.collectMetrics();
    }, this.MONITORING_INTERVAL);
  }

  private async collectMetrics() {
    const services = ['scg-ui', 'permagraph', 'ferrum-cli', 'ferrum-ai', 'mcp-server'];
    
    for (const service of services) {
      try {
        const metrics = await this.getServiceMetrics(service);
        this.recordMetrics(service, metrics);
      } catch (error) {
        console.warn(`Failed to collect metrics for ${service}:`, error);
      }
    }
  }

  private async getServiceMetrics(service: string): Promise<PerformanceMetrics> {
    const startTime = Date.now();
    
    // Simulate metrics collection - in real implementation, this would
    // collect actual metrics from Docker stats API or service endpoints
    const responseTime = Date.now() - startTime;
    
    return {
      timestamp: Date.now(),
      service,
      responseTime,
      memoryUsage: Math.random() * 512, // MB
      cpuUsage: Math.random() * 100, // percentage
      requestCount: Math.floor(Math.random() * 1000),
      errorCount: Math.floor(Math.random() * 10),
      cacheHitRate: Math.random() * 100 // percentage
    };
  }

  private recordMetrics(service: string, metrics: PerformanceMetrics) {
    if (!this.metrics.has(service)) {
      this.metrics.set(service, []);
    }

    const serviceMetrics = this.metrics.get(service)!;
    serviceMetrics.push(metrics);

    // Keep only the latest metrics
    if (serviceMetrics.length > this.MAX_METRICS_PER_SERVICE) {
      serviceMetrics.shift();
    }
  }

  public getMetrics(service?: string, timeRange?: number): PerformanceMetrics[] {
    if (service) {
      const serviceMetrics = this.metrics.get(service) || [];
      
      if (timeRange) {
        const cutoff = Date.now() - timeRange;
        return serviceMetrics.filter(m => m.timestamp > cutoff);
      }
      
      return serviceMetrics;
    }

    // Return all metrics
    const allMetrics: PerformanceMetrics[] = [];
    for (const serviceMetrics of this.metrics.values()) {
      allMetrics.push(...serviceMetrics);
    }

    if (timeRange) {
      const cutoff = Date.now() - timeRange;
      return allMetrics.filter(m => m.timestamp > cutoff);
    }

    return allMetrics;
  }

  public getAverageResponseTime(service: string, timeRange: number = 300000): number {
    const metrics = this.getMetrics(service, timeRange);
    if (metrics.length === 0) return 0;

    const total = metrics.reduce((sum, m) => sum + m.responseTime, 0);
    return total / metrics.length;
  }

  public getResourceUsage(): ResourceUsage {
    const services: ResourceUsage['services'] = {};
    
    for (const [serviceName, metrics] of this.metrics.entries()) {
      const latest = metrics[metrics.length - 1];
      if (latest) {
        services[serviceName] = {
          status: this.getServiceStatus(latest),
          responseTime: latest.responseTime,
          uptime: Date.now() - (metrics[0]?.timestamp || Date.now())
        };
      }
    }

    return {
      memory: {
        used: this.getTotalMemoryUsage(),
        total: 8192, // 8GB - would be dynamic in real implementation
        percentage: (this.getTotalMemoryUsage() / 8192) * 100
      },
      cpu: {
        usage: this.getAverageCpuUsage(),
        cores: 4 // Would be dynamic in real implementation
      },
      network: {
        bytesIn: this.getTotalNetworkIn(),
        bytesOut: this.getTotalNetworkOut(),
        connectionsActive: Object.keys(services).length
      },
      services
    };
  }

  private getServiceStatus(metrics: PerformanceMetrics): 'healthy' | 'degraded' | 'unhealthy' {
    if (metrics.responseTime > 5000 || metrics.errorCount > 50) {
      return 'unhealthy';
    }
    if (metrics.responseTime > 2000 || metrics.errorCount > 10) {
      return 'degraded';
    }
    return 'healthy';
  }

  private getTotalMemoryUsage(): number {
    let total = 0;
    for (const metrics of this.metrics.values()) {
      const latest = metrics[metrics.length - 1];
      if (latest) {
        total += latest.memoryUsage;
      }
    }
    return total;
  }

  private getAverageCpuUsage(): number {
    let total = 0;
    let count = 0;
    
    for (const metrics of this.metrics.values()) {
      const latest = metrics[metrics.length - 1];
      if (latest) {
        total += latest.cpuUsage;
        count++;
      }
    }
    
    return count > 0 ? total / count : 0;
  }

  private getTotalNetworkIn(): number {
    // Simulate network metrics
    return Math.floor(Math.random() * 1000000);
  }

  private getTotalNetworkOut(): number {
    // Simulate network metrics
    return Math.floor(Math.random() * 1000000);
  }

  public getOptimizationRecommendations(): OptimizationRecommendation[] {
    const recommendations: OptimizationRecommendation[] = [];
    const resourceUsage = this.getResourceUsage();

    // Memory optimization recommendations
    if (resourceUsage.memory.percentage > 80) {
      recommendations.push({
        type: 'memory',
        severity: 'high',
        message: 'High memory usage detected',
        action: 'Consider increasing memory limits or optimizing memory usage',
        impact: 'May cause service degradation or OOM kills'
      });
    }

    // CPU optimization recommendations
    if (resourceUsage.cpu.usage > 80) {
      recommendations.push({
        type: 'cpu',
        severity: 'high',
        message: 'High CPU usage detected',
        action: 'Consider scaling services or optimizing CPU-intensive operations',
        impact: 'May cause slow response times'
      });
    }

    // Service-specific recommendations
    for (const [serviceName, serviceInfo] of Object.entries(resourceUsage.services)) {
      if (serviceInfo.status === 'unhealthy') {
        recommendations.push({
          type: 'service',
          severity: 'critical',
          message: `Service ${serviceName} is unhealthy`,
          action: 'Check service logs and restart if necessary',
          impact: 'Service functionality may be impaired'
        });
      }

      if (serviceInfo.responseTime > 2000) {
        recommendations.push({
          type: 'network',
          severity: 'medium',
          message: `Slow response time for ${serviceName}`,
          action: 'Check network connectivity and service performance',
          impact: 'User experience may be degraded'
        });
      }
    }

    // Cache optimization recommendations
    const avgCacheHitRate = this.getAverageCacheHitRate();
    if (avgCacheHitRate < 50) {
      recommendations.push({
        type: 'cache',
        severity: 'medium',
        message: 'Low cache hit rate detected',
        action: 'Review caching strategy and increase cache TTL if appropriate',
        impact: 'Increased database load and slower response times'
      });
    }

    return recommendations.sort((a, b) => {
      const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
      return severityOrder[b.severity] - severityOrder[a.severity];
    });
  }

  private getAverageCacheHitRate(): number {
    let total = 0;
    let count = 0;
    
    for (const metrics of this.metrics.values()) {
      const latest = metrics[metrics.length - 1];
      if (latest) {
        total += latest.cacheHitRate;
        count++;
      }
    }
    
    return count > 0 ? total / count : 0;
  }

  public generatePerformanceReport(): {
    summary: string;
    metrics: ResourceUsage;
    recommendations: OptimizationRecommendation[];
    trends: { [service: string]: 'improving' | 'stable' | 'degrading' };
  } {
    const resourceUsage = this.getResourceUsage();
    const recommendations = this.getOptimizationRecommendations();
    const trends: { [service: string]: 'improving' | 'stable' | 'degrading' } = {};

    // Calculate trends
    for (const [serviceName, metrics] of this.metrics.entries()) {
      if (metrics.length >= 2) {
        const recent = metrics.slice(-5);
        const older = metrics.slice(-10, -5);
        
        if (recent.length > 0 && older.length > 0) {
          const recentAvg = recent.reduce((sum, m) => sum + m.responseTime, 0) / recent.length;
          const olderAvg = older.reduce((sum, m) => sum + m.responseTime, 0) / older.length;
          
          if (recentAvg < olderAvg * 0.9) {
            trends[serviceName] = 'improving';
          } else if (recentAvg > olderAvg * 1.1) {
            trends[serviceName] = 'degrading';
          } else {
            trends[serviceName] = 'stable';
          }
        }
      }
    }

    const criticalIssues = recommendations.filter(r => r.severity === 'critical').length;
    const highIssues = recommendations.filter(r => r.severity === 'high').length;
    
    let summary = 'System performance is ';
    if (criticalIssues > 0) {
      summary += `critical with ${criticalIssues} critical issues`;
    } else if (highIssues > 0) {
      summary += `degraded with ${highIssues} high-priority issues`;
    } else {
      summary += 'stable with no critical issues';
    }

    return {
      summary,
      metrics: resourceUsage,
      recommendations,
      trends
    };
  }

  public destroy() {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
    this.metrics.clear();
  }
}

// Singleton instance
export const performanceMonitor = new PerformanceMonitor();

// Graceful shutdown
process.on('SIGTERM', () => {
  performanceMonitor.destroy();
});

process.on('SIGINT', () => {
  performanceMonitor.destroy();
});