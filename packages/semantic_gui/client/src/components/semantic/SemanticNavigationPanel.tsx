import React, { useState } from 'react';
import { Search, Navigation, Lightbulb } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';

import { useSemanticSearch } from '@/hooks/useSemanticSearch';
import { useSemanticRecommendations } from '@/hooks/useSemanticRecommendations';

interface ArchitecturalComponent {
  iri: string;
  component_type: string;
  name: string;
  module_namespace: string;
  framework?: string;
}

interface SemanticNavigationPanelProps {
  tenantId: string;
  onComponentSelect?: (component: ArchitecturalComponent) => void;
  onPathSelect?: (path: any) => void;
  onPatternSelect?: (pattern: any) => void;
}

export const SemanticNavigationPanel: React.FC<
  SemanticNavigationPanelProps
> = ({ tenantId, onComponentSelect }) => {
  const [query, setQuery] = useState('');
  const { search, results, loading: searchLoading } = useSemanticSearch();
  const {
    fetchRecommendations,
    recommendations,
    loading: recLoading,
  } = useSemanticRecommendations();

  const handleSearch = async () => {
    if (!query.trim()) return;
    await search(query, tenantId);
  };

  const handleResultClick = async (result: any) => {
    if (result.component) {
      onComponentSelect?.(result.component);
      await fetchRecommendations(result.component.iri, tenantId);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const getComponentTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      module: 'bg-blue-100 text-blue-800',
      usecase: 'bg-green-100 text-green-800',
      port: 'bg-purple-100 text-purple-800',
      adapter: 'bg-orange-100 text-orange-800',
      entity: 'bg-yellow-100 text-yellow-800',
      event: 'bg-red-100 text-red-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  return (
    <Card className="w-full h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Navigation className="h-5 w-5" />
          Semantic Navigation
        </CardTitle>
        <div className="flex gap-2 mt-2">
          <Input
            placeholder="Search architecture components or concepts..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            className="flex-1"
          />
          <Button onClick={handleSearch} disabled={searchLoading}>
            <Search className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="results" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="results">
              Results ({results.length})
            </TabsTrigger>
            <TabsTrigger value="recommendations">
              Recommendations ({recommendations.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="results">
            {searchLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : (
              <ScrollArea className="h-96">
                <div className="space-y-3">
                  {results.map((result: any, index: number) => (
                    <Card
                      key={index}
                      className="cursor-pointer hover:bg-gray-50 transition-colors"
                      onClick={() => handleResultClick(result)}
                    >
                      <CardContent className="p-3">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="font-medium">
                                {result.component?.name || 'Result'}
                              </h4>
                              {result.component?.component_type && (
                                <Badge
                                  className={getComponentTypeColor(
                                    result.component.component_type
                                  )}
                                >
                                  {result.component.component_type}
                                </Badge>
                              )}
                              {result.component?.framework && (
                                <Badge variant="outline">
                                  {result.component.framework}
                                </Badge>
                              )}
                            </div>
                            {result.component?.module_namespace && (
                              <p className="text-sm text-gray-600 mb-1">
                                Module: {result.component.module_namespace}
                              </p>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                  {results.length === 0 && !searchLoading && (
                    <p className="text-center text-sm text-gray-500 py-4">
                      No results
                    </p>
                  )}
                </div>
              </ScrollArea>
            )}
          </TabsContent>

          <TabsContent value="recommendations">
            {recLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : (
              <ScrollArea className="h-96">
                <div className="space-y-2">
                  {recommendations.map((rec, index) => (
                    <div
                      key={index}
                      className="p-2 bg-blue-50 rounded text-sm flex items-center gap-2"
                    >
                      <Lightbulb className="h-4 w-4" />
                      {rec}
                    </div>
                  ))}
                  {recommendations.length === 0 && !recLoading && (
                    <p className="text-center text-sm text-gray-500 py-4">
                      No recommendations
                    </p>
                  )}
                </div>
              </ScrollArea>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};

export default SemanticNavigationPanel;
