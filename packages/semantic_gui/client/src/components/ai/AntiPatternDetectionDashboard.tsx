import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  XCircle,
  TrendingDown,
  RefreshCw,
  Eye,
  EyeOff,
  Filter,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';

interface AntiPattern {
  type: string;
  confidence: string;
  description: string;
  components: string[];
  evidence: string[];
  recommendations: string[];
  severity: string;
}

interface AntiPatternReport {
  anti_patterns: AntiPattern[];
  overall_assessment: {
    status: string;
    message: string;
    priority_actions: string[];
    severity_breakdown: {
      high: number;
      medium: number;
      low: number;
    };
  };
  timestamp: string;
}

interface AntiPatternDetectionDashboardProps {
  onComponentSelect?: (componentName: string) => void;
  className?: string;
}

export const AntiPatternDetectionDashboard: React.FC<
  AntiPatternDetectionDashboardProps
> = ({ onComponentSelect, className = '' }) => {
  const [isScanning, setIsScanning] = useState(false);
  const [report, setReport] = useState<AntiPatternReport | null>(null);
  const [selectedAntiPattern, setSelectedAntiPattern] =
    useState<AntiPattern | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [showResolved, setShowResolved] = useState(false);
  const [autoScan, setAutoScan] = useState(false);

  const { toast } = useToast();

  // Auto-scan if enabled
  useEffect(() => {
    if (autoScan) {
      const interval = setInterval(() => {
        handleScanAntiPatterns();
      }, 30000); // Scan every 30 seconds

      return () => clearInterval(interval);
    }
  }, [autoScan]);

  const handleScanAntiPatterns = async () => {
    setIsScanning(true);

    try {
      const response = await fetch('/api/ai/anti-pattern-detection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scan_type: 'full',
          include_resolved: showResolved,
        }),
      });

      if (response.ok) {
        const data: AntiPatternReport = await response.json();
        setReport(data);

        if (data.anti_patterns.length > 0) {
          setSelectedAntiPattern(data.anti_patterns[0]);
        }

        const highSeverityCount =
          data.overall_assessment.severity_breakdown.high;
        if (highSeverityCount > 0) {
          toast({
            title: 'High severity anti-patterns detected',
            description: `Found ${highSeverityCount} high severity issues that need immediate attention.`,
            variant: 'destructive',
          });
        } else {
          toast({
            title: 'Anti-pattern scan completed',
            description: `Found ${data.anti_patterns.length} potential issues.`,
          });
        }
      } else {
        throw new Error('Failed to scan for anti-patterns');
      }
    } catch (error) {
      console.error('Error scanning anti-patterns:', error);
      toast({
        title: 'Scan failed',
        description: 'Failed to scan for anti-patterns. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsScanning(false);
    }
  };

  const getFilteredAntiPatterns = () => {
    if (!report) return [];

    return report.anti_patterns.filter((pattern) => {
      const severityMatch =
        severityFilter === 'all' || pattern.severity === severityFilter;
      const typeMatch =
        typeFilter === 'all' ||
        pattern.type.toLowerCase().includes(typeFilter.toLowerCase());
      return severityMatch && typeMatch;
    });
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'medium':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'low':
        return <TrendingDown className="h-5 w-5 text-blue-500" />;
      default:
        return <AlertTriangle className="h-5 w-5 text-gray-500" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'critical':
        return 'text-red-600';
      case 'warning':
        return 'text-yellow-600';
      case 'healthy':
        return 'text-green-600';
      default:
        return 'text-gray-600';
    }
  };

  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'very_high':
        return 'text-red-600';
      case 'high':
        return 'text-orange-600';
      case 'medium':
        return 'text-yellow-600';
      case 'low':
        return 'text-green-600';
      default:
        return 'text-gray-600';
    }
  };

  const handleComponentClick = (componentName: string) => {
    if (onComponentSelect) {
      onComponentSelect(componentName);
    }
  };

  const getAntiPatternTypes = () => {
    if (!report) return [];
    const types = [...new Set(report.anti_patterns.map((p) => p.type))];
    return types;
  };

  const calculateHealthScore = () => {
    if (!report) return 100;

    const { high, medium, low } = report.overall_assessment.severity_breakdown;
    const totalIssues = high + medium + low;

    if (totalIssues === 0) return 100;

    // Weight issues by severity
    const weightedScore = high * 3 + medium * 2 + low * 1;
    const maxPossibleScore = totalIssues * 3;

    return Math.max(0, 100 - (weightedScore / maxPossibleScore) * 100);
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Control Panel */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Anti-Pattern Detection
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setAutoScan(!autoScan)}
                className={autoScan ? 'bg-green-50 border-green-200' : ''}
              >
                {autoScan ? (
                  <EyeOff className="h-4 w-4 mr-2" />
                ) : (
                  <Eye className="h-4 w-4 mr-2" />
                )}
                Auto-scan {autoScan ? 'ON' : 'OFF'}
              </Button>
              <Button
                onClick={handleScanAntiPatterns}
                disabled={isScanning}
                className="min-w-[120px]"
              >
                {isScanning ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                {isScanning ? 'Scanning...' : 'Scan Now'}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <Select value={severityFilter} onValueChange={setSeverityFilter}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Severity" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Severity</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Pattern Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {getAntiPatternTypes().map((type) => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Overall Assessment */}
      {report && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">
              Architecture Health Assessment
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div
                  className={`text-3xl font-bold ${getStatusColor(report.overall_assessment.status)}`}
                >
                  {calculateHealthScore().toFixed(0)}
                </div>
                <div className="text-sm text-gray-600">Health Score</div>
                <Progress value={calculateHealthScore()} className="mt-2" />
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">
                  {report.overall_assessment.severity_breakdown.high}
                </div>
                <div className="text-sm text-gray-600">High Severity</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">
                  {report.overall_assessment.severity_breakdown.medium}
                </div>
                <div className="text-sm text-gray-600">Medium Severity</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {report.overall_assessment.severity_breakdown.low}
                </div>
                <div className="text-sm text-gray-600">Low Severity</div>
              </div>
            </div>

            <div className="space-y-2">
              <div
                className={`text-lg font-medium ${getStatusColor(report.overall_assessment.status)}`}
              >
                Status: {report.overall_assessment.status.toUpperCase()}
              </div>
              <p className="text-gray-600">
                {report.overall_assessment.message}
              </p>
            </div>

            {report.overall_assessment.priority_actions.length > 0 && (
              <div>
                <h4 className="font-medium mb-2">Priority Actions</h4>
                <ul className="text-sm space-y-1">
                  {report.overall_assessment.priority_actions.map(
                    (action, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="text-red-500 mt-1">•</span>
                        <span>{action}</span>
                      </li>
                    )
                  )}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Anti-Pattern Details */}
      {report && getFilteredAntiPatterns().length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Anti-Pattern List */}
          <Card className="lg:col-span-1">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">
                Detected Anti-Patterns ({getFilteredAntiPatterns().length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="max-h-96">
                <div className="space-y-2">
                  {getFilteredAntiPatterns().map((pattern, index) => (
                    <button
                      key={index}
                      onClick={() => setSelectedAntiPattern(pattern)}
                      className={`w-full text-left p-3 rounded-lg border transition-colors ${
                        selectedAntiPattern === pattern
                          ? 'bg-red-50 border-red-200'
                          : 'hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {getSeverityIcon(pattern.severity)}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-medium truncate">
                              {pattern.type.replace('_', ' ')}
                            </span>
                            <Badge
                              className={getSeverityColor(pattern.severity)}
                            >
                              {pattern.severity}
                            </Badge>
                          </div>
                          <p className="text-xs text-gray-600 line-clamp-2">
                            {pattern.description}
                          </p>
                          <div className="flex items-center gap-2 mt-2">
                            <Badge
                              variant="outline"
                              className={getConfidenceColor(pattern.confidence)}
                            >
                              {pattern.confidence} confidence
                            </Badge>
                            <span className="text-xs text-gray-500">
                              {pattern.components.length} component
                              {pattern.components.length !== 1 ? 's' : ''}
                            </span>
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Selected Anti-Pattern Details */}
          {selectedAntiPattern && (
            <Card className="lg:col-span-2">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  {getSeverityIcon(selectedAntiPattern.severity)}
                  <div className="flex-1">
                    <CardTitle className="text-lg">
                      {selectedAntiPattern.type.replace('_', ' ')}
                    </CardTitle>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge
                        className={getSeverityColor(
                          selectedAntiPattern.severity
                        )}
                      >
                        {selectedAntiPattern.severity} severity
                      </Badge>
                      <Badge
                        variant="outline"
                        className={getConfidenceColor(
                          selectedAntiPattern.confidence
                        )}
                      >
                        {selectedAntiPattern.confidence} confidence
                      </Badge>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="description" className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="description">Description</TabsTrigger>
                    <TabsTrigger value="components">
                      Components ({selectedAntiPattern.components.length})
                    </TabsTrigger>
                    <TabsTrigger value="evidence">
                      Evidence ({selectedAntiPattern.evidence.length})
                    </TabsTrigger>
                    <TabsTrigger value="recommendations">
                      Fixes ({selectedAntiPattern.recommendations.length})
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="description" className="space-y-3">
                    <div className="prose prose-sm max-w-none">
                      <p>{selectedAntiPattern.description}</p>
                    </div>
                  </TabsContent>

                  <TabsContent value="components" className="space-y-3">
                    <ScrollArea className="max-h-64">
                      <div className="space-y-2">
                        {selectedAntiPattern.components.map(
                          (component, index) => (
                            <button
                              key={index}
                              onClick={() => handleComponentClick(component)}
                              className="w-full text-left p-2 rounded border hover:bg-gray-50 transition-colors"
                            >
                              <span className="font-mono text-sm">
                                {component}
                              </span>
                            </button>
                          )
                        )}
                      </div>
                    </ScrollArea>
                  </TabsContent>

                  <TabsContent value="evidence" className="space-y-3">
                    <ScrollArea className="max-h-64">
                      <ul className="text-sm space-y-2">
                        {selectedAntiPattern.evidence.map((evidence, index) => (
                          <li key={index} className="flex items-start gap-2">
                            <span className="text-gray-400 mt-1">•</span>
                            <span>{evidence}</span>
                          </li>
                        ))}
                      </ul>
                    </ScrollArea>
                  </TabsContent>

                  <TabsContent value="recommendations" className="space-y-3">
                    <ScrollArea className="max-h-64">
                      <div className="space-y-3">
                        {selectedAntiPattern.recommendations.map(
                          (recommendation, index) => (
                            <Card key={index} className="p-3">
                              <div className="flex items-start gap-2">
                                <span className="text-green-500 mt-1">✓</span>
                                <div className="flex-1">
                                  <p className="text-sm">{recommendation}</p>
                                </div>
                              </div>
                            </Card>
                          )
                        )}
                      </div>
                    </ScrollArea>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* No Anti-Patterns Found */}
      {report && report.anti_patterns.length === 0 && (
        <Card>
          <CardContent className="p-8 text-center">
            <div className="text-green-600 mb-4">
              <svg
                className="h-16 w-16 mx-auto"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-green-800 mb-2">
              No Anti-Patterns Detected
            </h3>
            <p className="text-green-600">
              Your architecture follows good design patterns and practices. Keep
              up the excellent work!
            </p>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {!report && (
        <Card>
          <CardContent className="p-8 text-center">
            <AlertTriangle className="h-16 w-16 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No Scan Results
            </h3>
            <p className="text-gray-600 mb-4">
              Click "Scan Now" to analyze your architecture for anti-patterns
              and design issues.
            </p>
            <Button onClick={handleScanAntiPatterns} disabled={isScanning}>
              {isScanning ? 'Scanning...' : 'Start Anti-Pattern Scan'}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
