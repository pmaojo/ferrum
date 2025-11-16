/**
 * Semantic Knowledge Base Component
 *
 * Main interface for accessing the semantic knowledge base, including
 * pattern search, best practices, architectural insights, and community
 * contributions.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  BookOpen,
  Users,
  Lightbulb,
  TrendingUp,
  Filter,
} from 'lucide-react';
import { createLogger } from '../../utils/logger';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { PatternLibrary } from './PatternLibrary';
import { BestPracticesPanel } from './BestPracticesPanel';
import { ArchitecturalInsights } from './ArchitecturalInsights';
import { CommunityContributions } from './CommunityContributions';
import { KnowledgeSearch } from './KnowledgeSearch';

interface KnowledgeBaseStats {
  patterns: {
    total_patterns: number;
    by_category: Record<string, number>;
    by_complexity: Record<string, number>;
  };
  practices: {
    total_practices: number;
    by_type: Record<string, number>;
    by_context: Record<string, number>;
  };
  community: {
    total_users: number;
    total_contributions: number;
    experts_count: number;
  };
  queries: {
    total_queries: number;
    cached_results: number;
  };
}

interface ArchitecturalComponent {
  iri: string;
  componentType: string;
  name: string;
  moduleNamespace: string;
  properties: Record<string, any>;
  relationships: Array<{
    subjectIri: string;
    predicateIri: string;
    objectIri: string;
    relationshipType: string;
  }>;
}

interface SemanticKnowledgeBaseProps {
  components?: ArchitecturalComponent[];
  projectContext?: string[];
  onPatternApply?: (patternId: string) => void;
  onSuggestionApply?: (suggestionId: string) => void;
}

export const SemanticKnowledgeBase: React.FC<SemanticKnowledgeBaseProps> = ({
  components = [],
  projectContext = [],
  onPatternApply,
  onSuggestionApply,
}) => {
  const [activeTab, setActiveTab] = useState('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState<
    'all' | 'patterns' | 'practices' | 'community'
  >('all');
  const [stats, setStats] = useState<KnowledgeBaseStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState<any[]>([]);
  const { toast } = useToast();
  const logger = createLogger('SemanticKnowledgeBase');

  // Load knowledge base statistics
  useEffect(() => {
    loadStatistics();
  }, []);

  // Generate insights when components change
  useEffect(() => {
    if (components.length > 0) {
      generateInsights();
    }
  }, [components, projectContext]);

  const loadStatistics = async () => {
    try {
      const response = await fetch('/api/knowledge-base/stats');
      const data = await response.json();

      if (data.success) {
        setStats(data.data.statistics);
      }
    } catch (error) {
      logger.error('Failed to load knowledge base statistics', error instanceof Error ? error : new Error(String(error)));
    }
  };

  const generateInsights = async () => {
    if (components.length === 0) return;

    try {
      setLoading(true);
      const response = await fetch('/api/knowledge-base/insights', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          components,
          projectContext,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setInsights(data.data.insights);
      } else {
        throw new Error(data.error);
      }
    } catch (error) {
      logger.error('Failed to generate insights', error instanceof Error ? error : new Error(String(error)));
      toast({
        title: 'Error',
        description: 'Failed to generate architectural insights',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = useCallback(async (query: string, type: string) => {
    setSearchQuery(query);
    setSearchType(type as any);

    if (query.trim()) {
      setActiveTab('search');
    }
  }, []);

  const handlePatternApply = useCallback(
    (patternId: string) => {
      onPatternApply?.(patternId);
      toast({
        title: 'Pattern Applied',
        description:
          'The architectural pattern has been applied to your project.',
      });
    },
    [onPatternApply, toast]
  );

  const handleSuggestionApply = useCallback(
    (suggestionId: string) => {
      onSuggestionApply?.(suggestionId);
      toast({
        title: 'Suggestion Applied',
        description: 'The improvement suggestion has been applied.',
      });
    },
    [onSuggestionApply, toast]
  );

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold">Semantic Knowledge Base</h1>
              <p className="text-muted-foreground">
                Explore architectural patterns, best practices, and community
                wisdom
              </p>
            </div>

            {stats && (
              <div className="flex gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {stats.patterns.total_patterns}
                  </div>
                  <div className="text-sm text-muted-foreground">Patterns</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {stats.practices.total_practices}
                  </div>
                  <div className="text-sm text-muted-foreground">Practices</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {stats.community.total_contributions}
                  </div>
                  <div className="text-sm text-muted-foreground">Community</div>
                </div>
              </div>
            )}
          </div>

          {/* Search Bar */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
              <Input
                placeholder="Search patterns, practices, or ask for architectural guidance..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) =>
                  e.key === 'Enter' && handleSearch(searchQuery, searchType)
                }
                className="pl-10"
              />
            </div>
            <Select
              value={searchType}
              onValueChange={(value) => setSearchType(value as any)}
            >
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="patterns">Patterns</SelectItem>
                <SelectItem value="practices">Practices</SelectItem>
                <SelectItem value="community">Community</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={() => handleSearch(searchQuery, searchType)}>
              Search
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="h-full flex flex-col"
        >
          <TabsList className="grid w-full grid-cols-5 mx-6 mt-4">
            <TabsTrigger value="search" className="flex items-center gap-2">
              <Search className="h-4 w-4" />
              Search
            </TabsTrigger>
            <TabsTrigger value="patterns" className="flex items-center gap-2">
              <BookOpen className="h-4 w-4" />
              Patterns
            </TabsTrigger>
            <TabsTrigger value="practices" className="flex items-center gap-2">
              <Lightbulb className="h-4 w-4" />
              Practices
            </TabsTrigger>
            <TabsTrigger value="insights" className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Insights
              {insights.length > 0 && (
                <Badge variant="secondary" className="ml-1">
                  {insights.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="community" className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Community
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-hidden p-6">
            <TabsContent value="search" className="h-full mt-0">
              <KnowledgeSearch
                query={searchQuery}
                searchType={searchType}
                onPatternApply={handlePatternApply}
                onSuggestionApply={handleSuggestionApply}
              />
            </TabsContent>

            <TabsContent value="patterns" className="h-full mt-0">
              <PatternLibrary
                onPatternApply={handlePatternApply}
                projectContext={projectContext}
              />
            </TabsContent>

            <TabsContent value="practices" className="h-full mt-0">
              <BestPracticesPanel
                components={components}
                projectContext={projectContext}
                onSuggestionApply={handleSuggestionApply}
              />
            </TabsContent>

            <TabsContent value="insights" className="h-full mt-0">
              <ArchitecturalInsights
                insights={insights}
                loading={loading}
                components={components}
                onRefresh={generateInsights}
                onPatternApply={handlePatternApply}
                onSuggestionApply={handleSuggestionApply}
              />
            </TabsContent>

            <TabsContent value="community" className="h-full mt-0">
              <CommunityContributions
                onPatternApply={handlePatternApply}
                onContribute={() => {
                  toast({
                    title: 'Feature Coming Soon',
                    description:
                      'Community contributions will be available soon.',
                  });
                }}
              />
            </TabsContent>
          </div>
        </Tabs>
      </div>

      {/* Quick Actions */}
      {components.length > 0 && (
        <div className="border-t bg-card p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="h-2 w-2 bg-green-500 rounded-full"></div>
              Analyzing {components.length} components
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={generateInsights}
                disabled={loading}
              >
                {loading ? 'Analyzing...' : 'Refresh Insights'}
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => handleSearch('architectural guidance', 'all')}
              >
                Get Guidance
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SemanticKnowledgeBase;
