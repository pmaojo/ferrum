import { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Shield,
  Zap,
  TrendingDown,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  DollarSign,
  Target,
  FileText,
  Award,
  BarChart3,
} from 'lucide-react';

interface AdvancedAIInsightsProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
}

interface SecurityVulnerability {
  id: string;
  type:
    | 'injection'
    | 'authentication'
    | 'authorization'
    | 'data_exposure'
    | 'crypto'
    | 'configuration';
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  nodeId: string;
  recommendation: string;
  cweId?: string;
  estimatedFixTime: number;
}

interface PerformanceBottleneck {
  id: string;
  type: 'database' | 'network' | 'computation' | 'memory' | 'io';
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  nodeId: string;
  impactMetric: string;
  recommendation: string;
  estimatedImprovement: string;
}

interface ArchitectureDebt {
  totalScore: number;
  categories: {
    complexity: number;
    coupling: number;
    cohesion: number;
    testability: number;
    maintainability: number;
  };
  estimatedRefactoringCost: number;
  prioritizedIssues: string[];
}

interface RefactoringOpportunity {
  id: string;
  type:
    | 'extract_service'
    | 'split_responsibility'
    | 'reduce_coupling'
    | 'improve_naming'
    | 'add_abstraction';
  title: string;
  description: string;
  affectedNodes: string[];
  benefitScore: number;
  effortEstimate: number;
  businessValue: string;
}

interface ComplianceIssue {
  id: string;
  standard: 'SOC2' | 'GDPR' | 'HIPAA' | 'PCI_DSS' | 'ISO27001';
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  nodeId: string;
  requirement: string;
  remediation: string;
}

interface OptimizationSuggestion {
  id: string;
  category:
    | 'performance'
    | 'scalability'
    | 'maintainability'
    | 'security'
    | 'cost';
  title: string;
  description: string;
  implementation: string;
  expectedBenefit: string;
  priority: number;
}

interface CodeQualityMetrics {
  overallScore: number;
  maintainabilityIndex: number;
  cyclomaticComplexity: number;
  technicalDebtRatio: number;
  testCoverage: number;
  duplicationRatio: number;
  documentationScore: number;
}

interface AIInsights {
  securityVulnerabilities: SecurityVulnerability[];
  performanceBottlenecks: PerformanceBottleneck[];
  architectureDebt: ArchitectureDebt;
  refactoringOpportunities: RefactoringOpportunity[];
  complianceIssues: ComplianceIssue[];
  optimizationSuggestions: OptimizationSuggestion[];
  codeQualityMetrics: CodeQualityMetrics;
}

export function AdvancedAIInsights({
  projectId,
  isOpen,
  onClose,
}: AdvancedAIInsightsProps) {
  const [insights, setInsights] = useState<AIInsights | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (isOpen && projectId) {
      analyzeProject();
    }
  }, [isOpen, projectId]);

  const analyzeProject = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/projects/${projectId}/ai-insights`);
      if (response.ok) {
        const data = await response.json();
        setInsights(data);
      }
    } catch (error) {
      console.error('Failed to fetch AI insights:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500';
      case 'high':
        return 'bg-orange-500';
      case 'medium':
        return 'bg-yellow-500';
      case 'low':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <XCircle className="h-4 w-4" />;
      case 'high':
        return <AlertTriangle className="h-4 w-4" />;
      case 'medium':
        return <Clock className="h-4 w-4" />;
      case 'low':
        return <CheckCircle className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-black border-2 border-[#00FF41] rounded-lg max-w-6xl w-full max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-[#00FF41]">
          <div className="flex items-center space-x-3">
            <BarChart3 className="h-6 w-6 text-[#00FF41]" />
            <h2 className="text-2xl font-bold text-[#00FF41] font-mono">
              ADVANCED_AI_INSIGHTS.EXE
            </h2>
          </div>
          <Button
            onClick={onClose}
            variant="outline"
            className="border-red-500 text-red-500 hover:bg-red-500/20"
          >
            CLOSE
          </Button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <RefreshCw className="h-8 w-8 animate-spin text-[#00FF41] mx-auto mb-4" />
                <div className="text-[#00FF41] font-mono">
                  ANALYZING_ARCHITECTURE...
                </div>
              </div>
            </div>
          ) : insights ? (
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-6 bg-black border border-[#00FF41]">
                <TabsTrigger
                  value="overview"
                  className="text-[#00FF41] data-[state=active]:bg-[#00FF41] data-[state=active]:text-black"
                >
                  Overview
                </TabsTrigger>
                <TabsTrigger
                  value="security"
                  className="text-[#00FF41] data-[state=active]:bg-[#00FF41] data-[state=active]:text-black"
                >
                  Security
                </TabsTrigger>
                <TabsTrigger
                  value="performance"
                  className="text-[#00FF41] data-[state=active]:bg-[#00FF41] data-[state=active]:text-black"
                >
                  Performance
                </TabsTrigger>
                <TabsTrigger
                  value="debt"
                  className="text-[#00FF41] data-[state=active]:bg-[#00FF41] data-[state=active]:text-black"
                >
                  Tech Debt
                </TabsTrigger>
                <TabsTrigger
                  value="compliance"
                  className="text-[#00FF41] data-[state=active]:bg-[#00FF41] data-[state=active]:text-black"
                >
                  Compliance
                </TabsTrigger>
                <TabsTrigger
                  value="optimize"
                  className="text-[#00FF41] data-[state=active]:bg-[#00FF41] data-[state=active]:text-black"
                >
                  Optimize
                </TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="mt-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {/* Overall Score */}
                  <Card className="bg-black border-[#00FF41] text-[#00FF41]">
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center space-x-2">
                        <Award className="h-5 w-5" />
                        <span>Code Quality Score</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold mb-2">
                        {Math.round(insights.codeQualityMetrics.overallScore)}%
                      </div>
                      <Progress
                        value={insights.codeQualityMetrics.overallScore}
                        className="h-2 bg-gray-800"
                      />
                    </CardContent>
                  </Card>

                  {/* Security Issues */}
                  <Card className="bg-black border-red-500 text-red-500">
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center space-x-2">
                        <Shield className="h-5 w-5" />
                        <span>Security Issues</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold mb-2">
                        {insights.securityVulnerabilities.length}
                      </div>
                      <div className="text-sm">
                        {
                          insights.securityVulnerabilities.filter(
                            (v) => v.severity === 'critical'
                          ).length
                        }{' '}
                        Critical
                      </div>
                    </CardContent>
                  </Card>

                  {/* Performance Issues */}
                  <Card className="bg-black border-yellow-500 text-yellow-500">
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center space-x-2">
                        <Zap className="h-5 w-5" />
                        <span>Performance Issues</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold mb-2">
                        {insights.performanceBottlenecks.length}
                      </div>
                      <div className="text-sm">
                        {
                          insights.performanceBottlenecks.filter(
                            (p) => p.severity === 'high'
                          ).length
                        }{' '}
                        High Priority
                      </div>
                    </CardContent>
                  </Card>

                  {/* Tech Debt Score */}
                  <Card className="bg-black border-orange-500 text-orange-500">
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center space-x-2">
                        <TrendingDown className="h-5 w-5" />
                        <span>Architecture Debt</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold mb-2">
                        {Math.round(insights.architectureDebt.totalScore)}%
                      </div>
                      <div className="text-sm">
                        {insights.architectureDebt.estimatedRefactoringCost}h to
                        fix
                      </div>
                    </CardContent>
                  </Card>

                  {/* Compliance Issues */}
                  <Card className="bg-black border-purple-500 text-purple-500">
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center space-x-2">
                        <FileText className="h-5 w-5" />
                        <span>Compliance Issues</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold mb-2">
                        {insights.complianceIssues.length}
                      </div>
                      <div className="text-sm">
                        {
                          insights.complianceIssues.filter(
                            (c) => c.severity === 'high'
                          ).length
                        }{' '}
                        High Risk
                      </div>
                    </CardContent>
                  </Card>

                  {/* Optimization Opportunities */}
                  <Card className="bg-black border-blue-500 text-blue-500">
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center space-x-2">
                        <Target className="h-5 w-5" />
                        <span>Optimizations</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold mb-2">
                        {insights.optimizationSuggestions.length}
                      </div>
                      <div className="text-sm">
                        {
                          insights.optimizationSuggestions.filter(
                            (o) => o.priority >= 4
                          ).length
                        }{' '}
                        High Impact
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="security" className="mt-6">
                <div className="space-y-4">
                  {insights.securityVulnerabilities.map((vuln) => (
                    <Alert
                      key={vuln.id}
                      className="border-red-500 bg-red-500/10"
                    >
                      <div className="flex items-start space-x-3">
                        {getSeverityIcon(vuln.severity)}
                        <div className="flex-1">
                          <AlertTitle className="text-red-500">
                            {vuln.title}
                            <Badge
                              className={`ml-2 ${getSeverityColor(vuln.severity)} text-white`}
                            >
                              {vuln.severity.toUpperCase()}
                            </Badge>
                          </AlertTitle>
                          <AlertDescription className="text-red-400 mt-2">
                            <div className="mb-2">{vuln.description}</div>
                            <div className="text-sm">
                              <strong>Recommendation:</strong>{' '}
                              {vuln.recommendation}
                            </div>
                            <div className="text-sm mt-1">
                              <strong>Fix Time:</strong> {vuln.estimatedFixTime}
                              h
                              {vuln.cweId && (
                                <span className="ml-2">
                                  <strong>CWE:</strong> {vuln.cweId}
                                </span>
                              )}
                            </div>
                          </AlertDescription>
                        </div>
                      </div>
                    </Alert>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="performance" className="mt-6">
                <div className="space-y-4">
                  {insights.performanceBottlenecks.map((bottleneck) => (
                    <Alert
                      key={bottleneck.id}
                      className="border-yellow-500 bg-yellow-500/10"
                    >
                      <div className="flex items-start space-x-3">
                        {getSeverityIcon(bottleneck.severity)}
                        <div className="flex-1">
                          <AlertTitle className="text-yellow-500">
                            {bottleneck.title}
                            <Badge
                              className={`ml-2 ${getSeverityColor(bottleneck.severity)} text-white`}
                            >
                              {bottleneck.severity.toUpperCase()}
                            </Badge>
                          </AlertTitle>
                          <AlertDescription className="text-yellow-400 mt-2">
                            <div className="mb-2">{bottleneck.description}</div>
                            <div className="text-sm">
                              <strong>Impact:</strong> {bottleneck.impactMetric}
                            </div>
                            <div className="text-sm mt-1">
                              <strong>Recommendation:</strong>{' '}
                              {bottleneck.recommendation}
                            </div>
                            <div className="text-sm mt-1">
                              <strong>Expected Improvement:</strong>{' '}
                              {bottleneck.estimatedImprovement}
                            </div>
                          </AlertDescription>
                        </div>
                      </div>
                    </Alert>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="debt" className="mt-6">
                <div className="space-y-6">
                  {/* Debt Categories */}
                  <Card className="bg-black border-[#00FF41] text-[#00FF41]">
                    <CardHeader>
                      <CardTitle>Architecture Debt Breakdown</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {Object.entries(
                          insights.architectureDebt.categories
                        ).map(([category, score]) => (
                          <div
                            key={category}
                            className="flex items-center justify-between"
                          >
                            <span className="capitalize">
                              {category.replace(/([A-Z])/g, ' $1')}
                            </span>
                            <div className="flex items-center space-x-2">
                              <Progress value={score} className="w-32 h-2" />
                              <span className="text-sm w-12">
                                {Math.round(score)}%
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Refactoring Opportunities */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-bold text-[#00FF41]">
                      Refactoring Opportunities
                    </h3>
                    {insights.refactoringOpportunities.map((opportunity) => (
                      <Alert
                        key={opportunity.id}
                        className="border-blue-500 bg-blue-500/10"
                      >
                        <div className="flex items-start space-x-3">
                          <RefreshCw className="h-4 w-4 text-blue-500 mt-1" />
                          <div className="flex-1">
                            <AlertTitle className="text-blue-500">
                              {opportunity.title}
                              <Badge className="ml-2 bg-blue-500 text-white">
                                Benefit: {opportunity.benefitScore}/10
                              </Badge>
                            </AlertTitle>
                            <AlertDescription className="text-blue-400 mt-2">
                              <div className="mb-2">
                                {opportunity.description}
                              </div>
                              <div className="text-sm">
                                <strong>Business Value:</strong>{' '}
                                {opportunity.businessValue}
                              </div>
                              <div className="text-sm mt-1">
                                <strong>Effort:</strong>{' '}
                                {opportunity.effortEstimate}h
                              </div>
                            </AlertDescription>
                          </div>
                        </div>
                      </Alert>
                    ))}
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="compliance" className="mt-6">
                <div className="space-y-4">
                  {insights.complianceIssues.map((issue) => (
                    <Alert
                      key={issue.id}
                      className="border-purple-500 bg-purple-500/10"
                    >
                      <div className="flex items-start space-x-3">
                        {getSeverityIcon(issue.severity)}
                        <div className="flex-1">
                          <AlertTitle className="text-purple-500">
                            {issue.standard} - {issue.category}
                            <Badge
                              className={`ml-2 ${getSeverityColor(issue.severity)} text-white`}
                            >
                              {issue.severity.toUpperCase()}
                            </Badge>
                          </AlertTitle>
                          <AlertDescription className="text-purple-400 mt-2">
                            <div className="mb-2">{issue.description}</div>
                            <div className="text-sm">
                              <strong>Requirement:</strong> {issue.requirement}
                            </div>
                            <div className="text-sm mt-1">
                              <strong>Remediation:</strong> {issue.remediation}
                            </div>
                          </AlertDescription>
                        </div>
                      </div>
                    </Alert>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="optimize" className="mt-6">
                <div className="space-y-4">
                  {insights.optimizationSuggestions
                    .sort((a, b) => b.priority - a.priority)
                    .map((suggestion) => (
                      <Alert
                        key={suggestion.id}
                        className="border-green-500 bg-green-500/10"
                      >
                        <div className="flex items-start space-x-3">
                          <Target className="h-4 w-4 text-green-500 mt-1" />
                          <div className="flex-1">
                            <AlertTitle className="text-green-500">
                              {suggestion.title}
                              <Badge className="ml-2 bg-green-500 text-white">
                                Priority: {suggestion.priority}/5
                              </Badge>
                            </AlertTitle>
                            <AlertDescription className="text-green-400 mt-2">
                              <div className="mb-2">
                                {suggestion.description}
                              </div>
                              <div className="text-sm">
                                <strong>Implementation:</strong>{' '}
                                {suggestion.implementation}
                              </div>
                              <div className="text-sm mt-1">
                                <strong>Expected Benefit:</strong>{' '}
                                {suggestion.expectedBenefit}
                              </div>
                            </AlertDescription>
                          </div>
                        </div>
                      </Alert>
                    ))}
                </div>
              </TabsContent>
            </Tabs>
          ) : (
            <div className="text-center py-12">
              <Button
                onClick={analyzeProject}
                className="bg-[#00FF41] text-black hover:bg-[#00FF41]/80"
              >
                RUN_ANALYSIS
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
