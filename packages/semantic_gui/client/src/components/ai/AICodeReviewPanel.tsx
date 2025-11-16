import React, { useState, useEffect } from 'react';
import {
  FileText,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Lightbulb,
  Code,
  Zap,
  Shield,
  TrendingUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';

interface CodeReviewSuggestion {
  line_number?: number;
  suggestion_type: string;
  title: string;
  description: string;
  suggested_fix?: string;
  confidence: number;
  architectural_impact: string;
}

interface CodeReviewReport {
  file_path: string;
  overall_score: number;
  suggestions: CodeReviewSuggestion[];
  architectural_issues: Array<{
    type: string;
    line_number?: number;
    description: string;
    severity: string;
    suggestion: string;
  }>;
  pattern_violations: Array<{
    type: string;
    line_number?: number;
    description: string;
    severity: string;
    suggestion: string;
  }>;
  quality_metrics: Record<string, any>;
  summary: string;
  recommendations: string[];
}

interface AICodeReviewPanelProps {
  selectedFiles?: string[];
  onFileSelect?: (filePath: string) => void;
  className?: string;
}

export const AICodeReviewPanel: React.FC<AICodeReviewPanelProps> = ({
  selectedFiles = [],
  onFileSelect,
  className = '',
}) => {
  const [isReviewing, setIsReviewing] = useState(false);
  const [reviewReports, setReviewReports] = useState<CodeReviewReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<CodeReviewReport | null>(
    null
  );
  const [reviewSummary, setReviewSummary] = useState<any>(null);
  const [reviewFocus, setReviewFocus] = useState<string[]>([
    'architecture',
    'patterns',
    'quality',
  ]);

  const { toast } = useToast();

  const handleStartReview = async () => {
    if (selectedFiles.length === 0) {
      toast({
        title: 'No files selected',
        description: 'Please select files to review.',
        variant: 'destructive',
      });
      return;
    }

    setIsReviewing(true);
    setReviewReports([]);
    setSelectedReport(null);
    setReviewSummary(null);

    try {
      const response = await fetch('/api/ai/code-review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files: selectedFiles,
          context: {
            project_type: 'kthulu',
            architecture_style: 'hexagonal',
            review_focus: reviewFocus,
          },
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setReviewReports(data.reports || []);
        setReviewSummary(data.summary);

        if (data.reports && data.reports.length > 0) {
          setSelectedReport(data.reports[0]);
        }

        toast({
          title: 'Code review completed',
          description: `Reviewed ${data.reports?.length || 0} files`,
        });
      } else {
        throw new Error('Failed to perform code review');
      }
    } catch (error) {
      console.error('Error performing code review:', error);
      toast({
        title: 'Review failed',
        description: 'Failed to perform code review. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsReviewing(false);
    }
  };

  const getSuggestionIcon = (type: string) => {
    const icons: Record<string, React.ReactNode> = {
      architecture: <Code className="h-4 w-4" />,
      pattern: <Lightbulb className="h-4 w-4" />,
      quality: <CheckCircle className="h-4 w-4" />,
      performance: <Zap className="h-4 w-4" />,
      security: <Shield className="h-4 w-4" />,
      improvement: <TrendingUp className="h-4 w-4" />,
    };
    return icons[type] || <FileText className="h-4 w-4" />;
  };

  const getSuggestionColor = (type: string) => {
    const colors: Record<string, string> = {
      architecture: 'bg-blue-100 text-blue-800 border-blue-200',
      pattern: 'bg-purple-100 text-purple-800 border-purple-200',
      quality: 'bg-green-100 text-green-800 border-green-200',
      performance: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      security: 'bg-red-100 text-red-800 border-red-200',
      improvement: 'bg-gray-100 text-gray-800 border-gray-200',
    };
    return colors[type] || 'bg-gray-100 text-gray-800 border-gray-200';
  };

  const getImpactColor = (impact: string) => {
    const colors: Record<string, string> = {
      high: 'text-red-600',
      medium: 'text-yellow-600',
      low: 'text-green-600',
    };
    return colors[impact] || 'text-gray-600';
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const handleApplySuggestion = async (
    suggestion: CodeReviewSuggestion,
    filePath: string
  ) => {
    if (!suggestion.suggested_fix) {
      toast({
        title: 'No fix available',
        description: "This suggestion doesn't have an automated fix.",
        variant: 'destructive',
      });
      return;
    }

    try {
      const response = await fetch('/api/ai/apply-suggestion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: filePath,
          line_number: suggestion.line_number,
          suggested_fix: suggestion.suggested_fix,
        }),
      });

      if (response.ok) {
        toast({
          title: 'Suggestion applied',
          description: 'The code has been updated with the suggested fix.',
        });
      } else {
        throw new Error('Failed to apply suggestion');
      }
    } catch (error) {
      console.error('Error applying suggestion:', error);
      toast({
        title: 'Failed to apply suggestion',
        description: 'Could not apply the suggested fix automatically.',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Review Controls */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="h-5 w-5" />
            AI-Powered Code Review
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <p className="text-sm text-gray-600">
                {selectedFiles.length} file
                {selectedFiles.length !== 1 ? 's' : ''} selected for review
              </p>
            </div>
            <Button
              onClick={handleStartReview}
              disabled={isReviewing || selectedFiles.length === 0}
              className="min-w-[120px]"
            >
              {isReviewing ? 'Reviewing...' : 'Start Review'}
            </Button>
          </div>

          {/* Review Focus Options */}
          <div>
            <p className="text-sm font-medium mb-2">Review Focus:</p>
            <div className="flex flex-wrap gap-2">
              {[
                'architecture',
                'patterns',
                'quality',
                'performance',
                'security',
              ].map((focus) => (
                <Button
                  key={focus}
                  variant={reviewFocus.includes(focus) ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => {
                    if (reviewFocus.includes(focus)) {
                      setReviewFocus(reviewFocus.filter((f) => f !== focus));
                    } else {
                      setReviewFocus([...reviewFocus, focus]);
                    }
                  }}
                  className="text-xs"
                >
                  {focus}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Review Summary */}
      {reviewSummary && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Review Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {reviewSummary.summary?.total_files || 0}
                </div>
                <div className="text-sm text-gray-600">Files Reviewed</div>
              </div>
              <div className="text-center">
                <div
                  className={`text-2xl font-bold ${getScoreColor(reviewSummary.summary?.average_score || 0)}`}
                >
                  {reviewSummary.summary?.average_score?.toFixed(1) || 0}
                </div>
                <div className="text-sm text-gray-600">Average Score</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">
                  {reviewSummary.summary?.high_priority_issues || 0}
                </div>
                <div className="text-sm text-gray-600">High Priority</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {reviewSummary.summary?.total_suggestions || 0}
                </div>
                <div className="text-sm text-gray-600">Total Issues</div>
              </div>
            </div>

            {reviewSummary.recommendations &&
              reviewSummary.recommendations.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Key Recommendations</h4>
                  <ul className="text-sm space-y-1">
                    {reviewSummary.recommendations
                      .slice(0, 5)
                      .map((rec: string, index: number) => (
                        <li key={index} className="flex items-start gap-2">
                          <span className="text-gray-400 mt-1">•</span>
                          <span>{rec}</span>
                        </li>
                      ))}
                  </ul>
                </div>
              )}
          </CardContent>
        </Card>
      )}

      {/* Review Results */}
      {reviewReports.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* File List */}
          <Card className="lg:col-span-1">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Reviewed Files</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="max-h-96">
                <div className="space-y-2">
                  {reviewReports.map((report, index) => (
                    <button
                      key={index}
                      onClick={() => setSelectedReport(report)}
                      className={`w-full text-left p-3 rounded-lg border transition-colors ${
                        selectedReport?.file_path === report.file_path
                          ? 'bg-blue-50 border-blue-200'
                          : 'hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium truncate">
                          {report.file_path.split('/').pop()}
                        </span>
                        <span
                          className={`text-sm font-bold ${getScoreColor(report.overall_score)}`}
                        >
                          {report.overall_score.toFixed(0)}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 truncate">
                        {report.file_path}
                      </div>
                      <div className="flex items-center gap-2 mt-2">
                        <Progress
                          value={report.overall_score}
                          className="flex-1 h-2"
                        />
                        <span className="text-xs text-gray-500">
                          {report.suggestions.length} issues
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* File Details */}
          {selectedReport && (
            <Card className="lg:col-span-2">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg truncate">
                    {selectedReport.file_path.split('/').pop()}
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge
                      className={`${getScoreColor(selectedReport.overall_score)} bg-transparent border`}
                    >
                      Score: {selectedReport.overall_score.toFixed(0)}/100
                    </Badge>
                  </div>
                </div>
                <p className="text-sm text-gray-600">
                  {selectedReport.summary}
                </p>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="suggestions" className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="suggestions">
                      Suggestions ({selectedReport.suggestions.length})
                    </TabsTrigger>
                    <TabsTrigger value="architecture">
                      Architecture ({selectedReport.architectural_issues.length}
                      )
                    </TabsTrigger>
                    <TabsTrigger value="patterns">
                      Patterns ({selectedReport.pattern_violations.length})
                    </TabsTrigger>
                    <TabsTrigger value="metrics">Metrics</TabsTrigger>
                  </TabsList>

                  <TabsContent value="suggestions" className="space-y-3">
                    <ScrollArea className="max-h-96">
                      {selectedReport.suggestions.map((suggestion, index) => (
                        <Card key={index} className="mb-3">
                          <CardContent className="p-4">
                            <div className="flex items-start gap-3">
                              <div
                                className={`p-2 rounded-lg ${getSuggestionColor(suggestion.suggestion_type)}`}
                              >
                                {getSuggestionIcon(suggestion.suggestion_type)}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <h4 className="font-medium text-sm">
                                    {suggestion.title}
                                  </h4>
                                  <Badge
                                    variant="outline"
                                    className={getImpactColor(
                                      suggestion.architectural_impact
                                    )}
                                  >
                                    {suggestion.architectural_impact} impact
                                  </Badge>
                                  {suggestion.line_number && (
                                    <Badge
                                      variant="outline"
                                      className="text-xs"
                                    >
                                      Line {suggestion.line_number}
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-sm text-gray-600 mb-2">
                                  {suggestion.description}
                                </p>
                                {suggestion.suggested_fix && (
                                  <div className="bg-gray-50 p-2 rounded text-xs font-mono mb-2">
                                    {suggestion.suggested_fix}
                                  </div>
                                )}
                                <div className="flex items-center justify-between">
                                  <span className="text-xs text-gray-500">
                                    Confidence:{' '}
                                    {(suggestion.confidence * 100).toFixed(0)}%
                                  </span>
                                  {suggestion.suggested_fix && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() =>
                                        handleApplySuggestion(
                                          suggestion,
                                          selectedReport.file_path
                                        )
                                      }
                                      className="text-xs"
                                    >
                                      Apply Fix
                                    </Button>
                                  )}
                                </div>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </ScrollArea>
                  </TabsContent>

                  <TabsContent value="architecture" className="space-y-3">
                    <ScrollArea className="max-h-96">
                      {selectedReport.architectural_issues.map(
                        (issue, index) => (
                          <Card key={index} className="mb-3">
                            <CardContent className="p-4">
                              <div className="flex items-start gap-3">
                                <AlertTriangle
                                  className={`h-5 w-5 mt-1 ${
                                    issue.severity === 'high'
                                      ? 'text-red-500'
                                      : issue.severity === 'medium'
                                        ? 'text-yellow-500'
                                        : 'text-blue-500'
                                  }`}
                                />
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <h4 className="font-medium text-sm">
                                      {issue.type}
                                    </h4>
                                    <Badge
                                      variant="outline"
                                      className={
                                        issue.severity === 'high'
                                          ? 'text-red-600'
                                          : issue.severity === 'medium'
                                            ? 'text-yellow-600'
                                            : 'text-blue-600'
                                      }
                                    >
                                      {issue.severity}
                                    </Badge>
                                    {issue.line_number && (
                                      <Badge
                                        variant="outline"
                                        className="text-xs"
                                      >
                                        Line {issue.line_number}
                                      </Badge>
                                    )}
                                  </div>
                                  <p className="text-sm text-gray-600 mb-2">
                                    {issue.description}
                                  </p>
                                  <p className="text-sm text-blue-600">
                                    {issue.suggestion}
                                  </p>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        )
                      )}
                    </ScrollArea>
                  </TabsContent>

                  <TabsContent value="patterns" className="space-y-3">
                    <ScrollArea className="max-h-96">
                      {selectedReport.pattern_violations.map(
                        (violation, index) => (
                          <Card key={index} className="mb-3">
                            <CardContent className="p-4">
                              <div className="flex items-start gap-3">
                                <XCircle
                                  className={`h-5 w-5 mt-1 ${
                                    violation.severity === 'high'
                                      ? 'text-red-500'
                                      : violation.severity === 'medium'
                                        ? 'text-yellow-500'
                                        : 'text-blue-500'
                                  }`}
                                />
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <h4 className="font-medium text-sm">
                                      {violation.type}
                                    </h4>
                                    <Badge
                                      variant="outline"
                                      className={
                                        violation.severity === 'high'
                                          ? 'text-red-600'
                                          : violation.severity === 'medium'
                                            ? 'text-yellow-600'
                                            : 'text-blue-600'
                                      }
                                    >
                                      {violation.severity}
                                    </Badge>
                                  </div>
                                  <p className="text-sm text-gray-600 mb-2">
                                    {violation.description}
                                  </p>
                                  <p className="text-sm text-blue-600">
                                    {violation.suggestion}
                                  </p>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        )
                      )}
                    </ScrollArea>
                  </TabsContent>

                  <TabsContent value="metrics" className="space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      {Object.entries(selectedReport.quality_metrics).map(
                        ([key, value]) => (
                          <div
                            key={key}
                            className="text-center p-3 bg-gray-50 rounded-lg"
                          >
                            <div className="text-lg font-bold">
                              {typeof value === 'number'
                                ? value.toFixed(1)
                                : value}
                            </div>
                            <div className="text-sm text-gray-600 capitalize">
                              {key.replace('_', ' ')}
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};
