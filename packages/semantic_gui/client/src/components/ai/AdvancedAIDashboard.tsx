import React, { useState } from 'react';
import {
  Brain,
  MessageSquare,
  FileSearch,
  Code,
  AlertTriangle,
  Settings,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { NaturalLanguageQueryInterface } from './NaturalLanguageQueryInterface';
import { AICodeReviewPanel } from './AICodeReviewPanel';
import { SemanticCodeCompletion } from './SemanticCodeCompletion';
import { AntiPatternDetectionDashboard } from './AntiPatternDetectionDashboard';

interface AdvancedAIDashboardProps {
  selectedFiles?: string[];
  onComponentSelect?: (component: any) => void;
  onFileSelect?: (filePath: string) => void;
  className?: string;
}

export const AdvancedAIDashboard: React.FC<AdvancedAIDashboardProps> = ({
  selectedFiles = [],
  onComponentSelect,
  onFileSelect,
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState('query');
  const [aiSettings, setAiSettings] = useState({
    autoScan: false,
    completionEnabled: true,
    reviewFocus: ['architecture', 'patterns', 'quality'],
    confidenceThreshold: 0.7,
  });

  const handleComponentSelect = (component: any) => {
    if (onComponentSelect) {
      onComponentSelect(component);
    }
  };

  const handleFileSelect = (filePath: string) => {
    if (onFileSelect) {
      onFileSelect(filePath);
    }
  };

  const getTabIcon = (tab: string) => {
    const icons: Record<string, React.ReactNode> = {
      query: <MessageSquare className="h-4 w-4" />,
      review: <FileSearch className="h-4 w-4" />,
      completion: <Code className="h-4 w-4" />,
      antipatterns: <AlertTriangle className="h-4 w-4" />,
      settings: <Settings className="h-4 w-4" />,
    };
    return icons[tab] || <Brain className="h-4 w-4" />;
  };

  const getTabBadge = (tab: string) => {
    switch (tab) {
      case 'review':
        return selectedFiles.length > 0 ? (
          <Badge variant="secondary" className="ml-2 text-xs">
            {selectedFiles.length}
          </Badge>
        ) : null;
      case 'antipatterns':
        return (
          <Badge variant="destructive" className="ml-2 text-xs">
            Live
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-xl flex items-center gap-2">
              <Brain className="h-6 w-6 text-blue-600" />
              Advanced AI Architecture Assistant
            </CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                Powered by LLM + Knowledge Graph
              </Badge>
              <Badge variant="outline" className="text-xs">
                Semantic Analysis
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600">
            Intelligent assistance for architecture development with natural
            language queries, AI-powered code review, semantic completion, and
            anti-pattern detection.
          </p>
        </CardContent>
      </Card>

      {/* AI Capabilities Tabs */}
      <Card>
        <CardContent className="p-0">
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="w-full"
          >
            <div className="border-b">
              <TabsList className="grid w-full grid-cols-5 h-auto p-1">
                <TabsTrigger
                  value="query"
                  className="flex items-center gap-2 py-3 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700"
                >
                  {getTabIcon('query')}
                  <span className="hidden sm:inline">Natural Language</span>
                  <span className="sm:hidden">Query</span>
                  {getTabBadge('query')}
                </TabsTrigger>
                <TabsTrigger
                  value="review"
                  className="flex items-center gap-2 py-3 data-[state=active]:bg-green-50 data-[state=active]:text-green-700"
                >
                  {getTabIcon('review')}
                  <span className="hidden sm:inline">Code Review</span>
                  <span className="sm:hidden">Review</span>
                  {getTabBadge('review')}
                </TabsTrigger>
                <TabsTrigger
                  value="completion"
                  className="flex items-center gap-2 py-3 data-[state=active]:bg-purple-50 data-[state=active]:text-purple-700"
                >
                  {getTabIcon('completion')}
                  <span className="hidden sm:inline">Code Completion</span>
                  <span className="sm:hidden">Complete</span>
                  {getTabBadge('completion')}
                </TabsTrigger>
                <TabsTrigger
                  value="antipatterns"
                  className="flex items-center gap-2 py-3 data-[state=active]:bg-red-50 data-[state=active]:text-red-700"
                >
                  {getTabIcon('antipatterns')}
                  <span className="hidden sm:inline">Anti-Patterns</span>
                  <span className="sm:hidden">Issues</span>
                  {getTabBadge('antipatterns')}
                </TabsTrigger>
                <TabsTrigger
                  value="settings"
                  className="flex items-center gap-2 py-3 data-[state=active]:bg-gray-50 data-[state=active]:text-gray-700"
                >
                  {getTabIcon('settings')}
                  <span className="hidden sm:inline">Settings</span>
                  <span className="sm:hidden">Config</span>
                  {getTabBadge('settings')}
                </TabsTrigger>
              </TabsList>
            </div>

            <div className="p-6">
              <TabsContent value="query" className="mt-0">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 mb-4">
                    <MessageSquare className="h-5 w-5 text-blue-600" />
                    <h3 className="text-lg font-medium">
                      Natural Language Architecture Queries
                    </h3>
                  </div>
                  <p className="text-sm text-gray-600 mb-6">
                    Ask questions about your architecture in natural language.
                    Get intelligent responses with component suggestions,
                    relationship analysis, and architectural insights.
                  </p>
                  <NaturalLanguageQueryInterface
                    onComponentSelect={handleComponentSelect}
                  />
                </div>
              </TabsContent>

              <TabsContent value="review" className="mt-0">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 mb-4">
                    <FileSearch className="h-5 w-5 text-green-600" />
                    <h3 className="text-lg font-medium">
                      AI-Powered Code Review
                    </h3>
                  </div>
                  <p className="text-sm text-gray-600 mb-6">
                    Get intelligent code review suggestions focusing on
                    architectural patterns, SOLID principles, and hexagonal
                    architecture compliance.
                  </p>
                  <AICodeReviewPanel
                    selectedFiles={selectedFiles}
                    onFileSelect={handleFileSelect}
                  />
                </div>
              </TabsContent>

              <TabsContent value="completion" className="mt-0">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 mb-4">
                    <Code className="h-5 w-5 text-purple-600" />
                    <h3 className="text-lg font-medium">
                      Semantic Code Completion
                    </h3>
                  </div>
                  <p className="text-sm text-gray-600 mb-6">
                    Get intelligent code completions based on architectural
                    context, domain knowledge, and established patterns in your
                    codebase.
                  </p>
                  <SemanticCodeCompletion
                    filePath={selectedFiles[0] || ''}
                    language="go"
                    onCompletionApply={(completion) => {
                      console.log('Applied completion:', completion);
                    }}
                  />
                </div>
              </TabsContent>

              <TabsContent value="antipatterns" className="mt-0">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 mb-4">
                    <AlertTriangle className="h-5 w-5 text-red-600" />
                    <h3 className="text-lg font-medium">
                      Architectural Anti-Pattern Detection
                    </h3>
                  </div>
                  <p className="text-sm text-gray-600 mb-6">
                    Automatically detect and analyze architectural
                    anti-patterns, code smells, and design violations in your
                    codebase.
                  </p>
                  <AntiPatternDetectionDashboard
                    onComponentSelect={(componentName) => {
                      // Convert component name to component object
                      handleComponentSelect({ name: componentName });
                    }}
                  />
                </div>
              </TabsContent>

              <TabsContent value="settings" className="mt-0">
                <div className="space-y-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Settings className="h-5 w-5 text-gray-600" />
                    <h3 className="text-lg font-medium">
                      AI Assistant Settings
                    </h3>
                  </div>

                  {/* General Settings */}
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">
                        General Settings
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">
                            Auto-scan for Anti-patterns
                          </label>
                          <p className="text-xs text-gray-600">
                            Automatically scan for issues every 30 seconds
                          </p>
                        </div>
                        <Button
                          variant={aiSettings.autoScan ? 'default' : 'outline'}
                          size="sm"
                          onClick={() =>
                            setAiSettings((prev) => ({
                              ...prev,
                              autoScan: !prev.autoScan,
                            }))
                          }
                        >
                          {aiSettings.autoScan ? 'ON' : 'OFF'}
                        </Button>
                      </div>

                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">
                            Semantic Code Completion
                          </label>
                          <p className="text-xs text-gray-600">
                            Enable intelligent code completions
                          </p>
                        </div>
                        <Button
                          variant={
                            aiSettings.completionEnabled ? 'default' : 'outline'
                          }
                          size="sm"
                          onClick={() =>
                            setAiSettings((prev) => ({
                              ...prev,
                              completionEnabled: !prev.completionEnabled,
                            }))
                          }
                        >
                          {aiSettings.completionEnabled ? 'ON' : 'OFF'}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Code Review Settings */}
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">
                        Code Review Focus
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {[
                        'architecture',
                        'patterns',
                        'quality',
                        'performance',
                        'security',
                      ].map((focus) => (
                        <div
                          key={focus}
                          className="flex items-center justify-between"
                        >
                          <label className="text-sm capitalize">{focus}</label>
                          <Button
                            variant={
                              aiSettings.reviewFocus.includes(focus)
                                ? 'default'
                                : 'outline'
                            }
                            size="sm"
                            onClick={() => {
                              setAiSettings((prev) => ({
                                ...prev,
                                reviewFocus: prev.reviewFocus.includes(focus)
                                  ? prev.reviewFocus.filter((f) => f !== focus)
                                  : [...prev.reviewFocus, focus],
                              }));
                            }}
                          >
                            {aiSettings.reviewFocus.includes(focus)
                              ? 'ON'
                              : 'OFF'}
                          </Button>
                        </div>
                      ))}
                    </CardContent>
                  </Card>

                  {/* Confidence Threshold */}
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">
                        Confidence Threshold
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm">
                            Minimum confidence for suggestions
                          </span>
                          <span className="text-sm font-medium">
                            {(aiSettings.confidenceThreshold * 100).toFixed(0)}%
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0.1"
                          max="1.0"
                          step="0.1"
                          value={aiSettings.confidenceThreshold}
                          onChange={(e) =>
                            setAiSettings((prev) => ({
                              ...prev,
                              confidenceThreshold: parseFloat(e.target.value),
                            }))
                          }
                          className="w-full"
                        />
                        <div className="flex justify-between text-xs text-gray-500">
                          <span>10%</span>
                          <span>50%</span>
                          <span>100%</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Model Information */}
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">
                        AI Model Information
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Language Model:</span>
                        <span className="font-medium">GPT-4 / Claude-3</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Knowledge Graph:</span>
                        <span className="font-medium">PermaGraph Ontology</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Reasoning Engine:</span>
                        <span className="font-medium">
                          Hybrid (ELK + HermiT)
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Pattern Detection:</span>
                        <span className="font-medium">
                          Architectural Analysis
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
            </div>
          </Tabs>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <MessageSquare className="h-8 w-8 mx-auto text-blue-600 mb-2" />
            <div className="text-2xl font-bold">∞</div>
            <div className="text-xs text-gray-600">
              Natural Language Queries
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <FileSearch className="h-8 w-8 mx-auto text-green-600 mb-2" />
            <div className="text-2xl font-bold">{selectedFiles.length}</div>
            <div className="text-xs text-gray-600">Files Ready for Review</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Code className="h-8 w-8 mx-auto text-purple-600 mb-2" />
            <div className="text-2xl font-bold">AI</div>
            <div className="text-xs text-gray-600">Semantic Completions</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <AlertTriangle className="h-8 w-8 mx-auto text-red-600 mb-2" />
            <div className="text-2xl font-bold">0</div>
            <div className="text-xs text-gray-600">Critical Issues</div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
