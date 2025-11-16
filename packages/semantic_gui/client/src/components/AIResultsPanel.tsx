import { useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Brain,
  AlertTriangle,
  CheckCircle,
  Lightbulb,
  Target,
  Code,
  Zap,
  RefreshCw,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

interface AIResultsPanelProps {
  projectId: string;
}

interface AIAnalysisResult {
  summary: string;
  recommendations: string[];
  complexity: 'low' | 'medium' | 'high' | 'critical';
  threats: string[];
  optimizations: string[];
  patterns?: {
    type: string;
    confidence: number;
    description: string;
    files: string[];
  }[];
  violations?: {
    type: string;
    severity: 'high' | 'medium' | 'low';
    description: string;
    file: string;
    suggestion: string;
  }[];
}

export function AIResultsPanel({ projectId }: AIResultsPanelProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Fetch AI analysis results
  const {
    data: aiResults,
    isLoading,
    refetch,
  } = useQuery<AIAnalysisResult>({
    queryKey: ['/api/ai-analysis', projectId],
    enabled: !!projectId,
  });

  const triggerAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      await refetch();
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getComplexityColor = (complexity: string) => {
    switch (complexity) {
      case 'low':
        return 'bg-green-500';
      case 'medium':
        return 'bg-yellow-500';
      case 'high':
        return 'bg-orange-500';
      case 'critical':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'medium':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'low':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      default:
        return <CheckCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  if (isLoading || isAnalyzing) {
    return (
      <Card className="h-full bg-black border-2 border-[#00FF41]">
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Brain className="h-5 w-5 text-[#00FFFF] animate-pulse" />
            <CardTitle className="text-[#00FF41] font-black">
              AI_ANALYSIS
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center">
            <RefreshCw className="h-8 w-8 text-[#00FF41] animate-spin mx-auto mb-4" />
            <p className="text-[#00FF41]/70">ANALYZING_ARCHITECTURE...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!aiResults) {
    return (
      <Card className="h-full bg-black border-2 border-[#00FF41]">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Brain className="h-5 w-5 text-[#00FFFF]" />
              <CardTitle className="text-[#00FF41] font-black">
                AI_ANALYSIS
              </CardTitle>
            </div>
            <Button
              onClick={triggerAnalysis}
              size="sm"
              className="bg-[#00FF41] text-black hover:bg-[#00FF41]/80 font-black"
            >
              <Zap className="h-4 w-4 mr-2" />
              ANALYZE
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center">
            <Brain className="h-12 w-12 text-[#00FF41]/50 mx-auto mb-4" />
            <p className="text-[#00FF41]/70 mb-4">
              No analysis results available
            </p>
            <p className="text-xs text-[#00FF41]/50">
              Click ANALYZE to run AI architecture analysis
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full bg-black border-2 border-[#00FF41]">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Brain className="h-5 w-5 text-[#00FFFF]" />
            <CardTitle className="text-[#00FF41] font-black">
              AI_ANALYSIS
            </CardTitle>
          </div>
          <div className="flex items-center space-x-2">
            <Badge
              className={`${getComplexityColor(aiResults.complexity)} text-black font-black px-2 py-1`}
            >
              {aiResults.complexity.toUpperCase()}
            </Badge>
            <Button
              onClick={triggerAnalysis}
              size="sm"
              variant="outline"
              className="border-[#00FF41] text-[#00FF41] hover:bg-[#00FF41]/10"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="h-[calc(100%-5rem)]">
        <Tabs defaultValue="summary" className="h-full">
          <TabsList className="bg-black border border-[#00FF41]/30 mb-4">
            <TabsTrigger
              value="summary"
              className="text-[#00FF41] data-[state=active]:bg-[#00FF41] data-[state=active]:text-black"
            >
              SUMMARY
            </TabsTrigger>
            <TabsTrigger
              value="patterns"
              className="text-[#00FF41] data-[state=active]:bg-[#00FF41] data-[state=active]:text-black"
            >
              PATTERNS
            </TabsTrigger>
            <TabsTrigger
              value="issues"
              className="text-[#00FF41] data-[state=active]:bg-[#00FF41] data-[state=active]:text-black"
            >
              ISSUES
            </TabsTrigger>
            <TabsTrigger
              value="recommendations"
              className="text-[#00FF41] data-[state=active]:bg-[#00FF41] data-[state=active]:text-black"
            >
              RECOMMENDATIONS
            </TabsTrigger>
          </TabsList>

          <ScrollArea className="h-[calc(100%-3rem)]">
            <TabsContent value="summary" className="space-y-4">
              <Card className="bg-black border border-[#00FF41]/30">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-[#00FFFF] font-black">
                    ARCHITECTURE_SUMMARY
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-[#00FF41]/90 text-sm leading-relaxed">
                    {aiResults.summary}
                  </p>
                </CardContent>
              </Card>

              {aiResults.optimizations &&
                aiResults.optimizations.length > 0 && (
                  <Card className="bg-black border border-[#00FF41]/30">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm text-[#FFFF00] font-black flex items-center">
                        <Lightbulb className="h-4 w-4 mr-2" />
                        OPTIMIZATIONS
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2">
                        {aiResults.optimizations.map((optimization, index) => (
                          <li
                            key={index}
                            className="text-[#00FF41]/90 text-sm flex items-start"
                          >
                            <span className="text-[#FFFF00] mr-2">→</span>
                            {optimization}
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                )}
            </TabsContent>

            <TabsContent value="patterns" className="space-y-4">
              {aiResults.patterns && aiResults.patterns.length > 0 ? (
                aiResults.patterns.map((pattern, index) => (
                  <Card
                    key={index}
                    className="bg-black border border-[#00FF41]/30"
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm text-[#00FFFF] font-black">
                          {pattern.type.toUpperCase()}
                        </CardTitle>
                        <Badge className="bg-[#00FF41] text-black font-black">
                          {Math.round(pattern.confidence * 100)}% CONFIDENCE
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-[#00FF41]/90 text-sm mb-3">
                        {pattern.description}
                      </p>
                      <div className="space-y-2">
                        <p className="text-xs text-[#00FFFF] font-black">
                          AFFECTED_FILES:
                        </p>
                        {pattern.files.map((file, fileIndex) => (
                          <div
                            key={fileIndex}
                            className="text-xs text-[#00FF41]/70 font-mono"
                          >
                            <Code className="h-3 w-3 inline mr-1" />
                            {file}
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <div className="text-center py-8">
                  <Target className="h-12 w-12 mx-auto text-[#00FF41]/50 mb-4" />
                  <p className="text-[#00FF41]/70">
                    No architectural patterns detected
                  </p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="issues" className="space-y-4">
              {aiResults.violations && aiResults.violations.length > 0 ? (
                aiResults.violations.map((violation, index) => (
                  <Card
                    key={index}
                    className="bg-black border border-[#FF0040]/30"
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          {getSeverityIcon(violation.severity)}
                          <CardTitle className="text-sm text-[#FF0040] font-black">
                            {violation.type.toUpperCase()}
                          </CardTitle>
                        </div>
                        <Badge className="bg-[#FF0040] text-white font-black">
                          {violation.severity.toUpperCase()}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-[#00FF41]/90 text-sm mb-2">
                        {violation.description}
                      </p>
                      <div className="text-xs text-[#00FF41]/70 font-mono mb-2">
                        <Code className="h-3 w-3 inline mr-1" />
                        {violation.file}
                      </div>
                      <div className="bg-[#00FF41]/10 p-2 rounded border border-[#00FF41]/30">
                        <p className="text-xs text-[#00FFFF] font-black mb-1">
                          SUGGESTION:
                        </p>
                        <p className="text-xs text-[#00FF41]/90">
                          {violation.suggestion}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <div className="text-center py-8">
                  <CheckCircle className="h-12 w-12 mx-auto text-[#00FF41] mb-4" />
                  <p className="text-[#00FF41]">
                    No architectural violations detected
                  </p>
                  <p className="text-[#00FF41]/70 text-sm">
                    Your architecture follows best practices
                  </p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="recommendations" className="space-y-4">
              {aiResults.recommendations &&
              aiResults.recommendations.length > 0 ? (
                aiResults.recommendations.map((recommendation, index) => (
                  <Card
                    key={index}
                    className="bg-black border border-[#00FF41]/30"
                  >
                    <CardContent className="pt-4">
                      <div className="flex items-start space-x-3">
                        <Lightbulb className="h-4 w-4 text-[#FFFF00] mt-0.5 flex-shrink-0" />
                        <p className="text-[#00FF41]/90 text-sm">
                          {recommendation}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <div className="text-center py-8">
                  <Brain className="h-12 w-12 mx-auto text-[#00FF41]/50 mb-4" />
                  <p className="text-[#00FF41]/70">
                    No recommendations available
                  </p>
                </div>
              )}
            </TabsContent>
          </ScrollArea>
        </Tabs>
      </CardContent>
    </Card>
  );
}
