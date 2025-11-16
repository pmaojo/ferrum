import React, { useState, useCallback, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable';
import {
  Search,
  Navigation,
  TrendingUp,
  GitBranch,
  AlertTriangle,
  Lightbulb,
  Maximize2,
  Minimize2,
  RefreshCw,
} from 'lucide-react';

import { SemanticNavigationPanel } from './SemanticNavigationPanel';
import { SemanticGraphVisualization } from '../graph/SemanticGraphVisualization';

interface ArchitecturalComponent {
  iri: string;
  component_type: string;
  name: string;
  module_namespace: string;
}

interface DependencyPath {
  source: ArchitecturalComponent;
  target: ArchitecturalComponent;
  path: ArchitecturalComponent[];
  path_type: string;
  weight: number;
  relationships: string[];
  metadata: Record<string, any>;
}

interface PatternInstance {
  pattern_type: string;
  confidence: string;
  components: ArchitecturalComponent[];
  description: string;
  evidence: string[];
  recommendations: string[];
  metadata: Record<string, any>;
}

interface ArchitecturalHotspots {
  complexity_hotspots: Array<{
    component: ArchitecturalComponent;
    score: number;
    details: Record<string, any>;
  }>;
  coupling_hotspots: Array<{
    component: ArchitecturalComponent;
    score: number;
    incoming: number;
    outgoing: number;
  }>;
  pattern_hotspots: Array<{
    component: ArchitecturalComponent;
    patterns: PatternInstance[];
  }>;
  anti_pattern_hotspots: PatternInstance[];
}

interface SemanticArchitectureExplorerProps {
  tenantId: string;
  projectId?: string;
  initialComponent?: ArchitecturalComponent;
}

export const SemanticArchitectureExplorer: React.FC<
  SemanticArchitectureExplorerProps
> = ({ tenantId, projectId, initialComponent }) => {
  const [selectedComponent, setSelectedComponent] =
    useState<ArchitecturalComponent | null>(initialComponent || null);
  const [selectedPath, setSelectedPath] = useState<DependencyPath | null>(null);
  const [selectedPattern, setSelectedPattern] =
    useState<PatternInstance | null>(null);
  const [hotspots, setHotspots] = useState<ArchitecturalHotspots | null>(null);
  const [isNavigationExpanded, setIsNavigationExpanded] = useState(true);
  const [isVisualizationExpanded, setIsVisualizationExpanded] = useState(true);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('navigation');

  // Load architectural hotspots on mount
  useEffect(() => {
    loadArchitecturalHotspots();
  }, [tenantId]);

  const loadArchitecturalHotspots = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/semantic/hotspots', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tenant_id: tenantId,
          hotspot_type: 'all',
        }),
      });

      if (response.ok) {
        const hotspotsData: ArchitecturalHotspots = await response.json();
        setHotspots(hotspotsData);
      }
    } catch (error) {
      console.error('Error loading architectural hotspots:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleComponentSelect = useCallback(
    (component: ArchitecturalComponent) => {
      setSelectedComponent(component);
      setSelectedPath(null); // Clear path selection when component changes
      setActiveTab('visualization'); // Switch to visualization tab
    },
    []
  );

  const handlePathSelect = useCallback((path: DependencyPath) => {
    setSelectedPath(path);
    setActiveTab('visualization'); // Switch to visualization tab
  }, []);

  const handlePatternSelect = useCallback((pattern: PatternInstance) => {
    setSelectedPattern(pattern);
    setActiveTab('patterns'); // Switch to patterns tab
  }, []);

  const exploreComponentNeighborhood = async (
    component: ArchitecturalComponent
  ) => {
    try {
      const response = await fetch('/api/semantic/explore-component', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          component_iri: component.iri,
          tenant_id: tenantId,
          depth: 2,
          include_patterns: true,
        }),
      });

      if (response.ok) {
        const explorationResult = await response.json();
        console.log('Component neighborhood:', explorationResult);
        // Handle exploration result - could update visualization or show in a modal
      }
    } catch (error) {
      console.error('Error exploring component neighborhood:', error);
    }
  };

  const getComponentTypeColor = (type: string) => {
    const colors = {
      module: 'bg-blue-100 text-blue-800',
      usecase: 'bg-green-100 text-green-800',
      port: 'bg-purple-100 text-purple-800',
      adapter: 'bg-orange-100 text-orange-800',
      entity: 'bg-yellow-100 text-yellow-800',
      event: 'bg-red-100 text-red-800',
    };
    return colors[type as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  const getHotspotSeverityColor = (score: number) => {
    if (score > 15) return 'bg-red-100 text-red-800';
    if (score > 10) return 'bg-orange-100 text-orange-800';
    if (score > 5) return 'bg-yellow-100 text-yellow-800';
    return 'bg-green-100 text-green-800';
  };

  return (
    <div className="h-full w-full">
      <ResizablePanelGroup direction="horizontal" className="h-full">
        {/* Navigation Panel */}
        <ResizablePanel
          defaultSize={35}
          minSize={25}
          maxSize={50}
          className={isNavigationExpanded ? '' : 'hidden'}
        >
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-between p-2 border-b">
              <h3 className="font-semibold">Semantic Navigation</h3>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={loadArchitecturalHotspots}
                  disabled={loading}
                >
                  <RefreshCw
                    className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`}
                  />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsNavigationExpanded(false)}
                >
                  <Minimize2 className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="flex-1 overflow-hidden">
              <SemanticNavigationPanel
                tenantId={tenantId}
                onComponentSelect={handleComponentSelect}
                onPathSelect={handlePathSelect}
                onPatternSelect={handlePatternSelect}
              />
            </div>
          </div>
        </ResizablePanel>

        {!isNavigationExpanded && (
          <div className="w-8 border-r flex flex-col items-center py-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsNavigationExpanded(true)}
              className="mb-2"
            >
              <Maximize2 className="h-4 w-4" />
            </Button>
            <div className="writing-mode-vertical text-xs text-gray-500">
              Navigation
            </div>
          </div>
        )}

        <ResizableHandle />

        {/* Main Content Area */}
        <ResizablePanel defaultSize={65} minSize={50}>
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-between p-2 border-b">
              <Tabs
                value={activeTab}
                onValueChange={setActiveTab}
                className="flex-1"
              >
                <TabsList>
                  <TabsTrigger value="navigation">
                    <Navigation className="h-4 w-4 mr-1" />
                    Explorer
                  </TabsTrigger>
                  <TabsTrigger value="visualization">
                    <GitBranch className="h-4 w-4 mr-1" />
                    Graph
                  </TabsTrigger>
                  <TabsTrigger value="patterns">
                    <TrendingUp className="h-4 w-4 mr-1" />
                    Patterns
                  </TabsTrigger>
                  <TabsTrigger value="hotspots">
                    <AlertTriangle className="h-4 w-4 mr-1" />
                    Hotspots
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>

            <div className="flex-1 overflow-hidden">
              <Tabs value={activeTab} className="h-full">
                {/* Explorer Tab */}
                <TabsContent value="navigation" className="h-full m-0">
                  <div className="h-full p-4">
                    {selectedComponent ? (
                      <Card>
                        <CardHeader>
                          <CardTitle className="flex items-center gap-2">
                            <Badge
                              className={getComponentTypeColor(
                                selectedComponent.component_type
                              )}
                            >
                              {selectedComponent.component_type}
                            </Badge>
                            {selectedComponent.name}
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-4">
                            <div>
                              <p className="text-sm text-gray-600">
                                <strong>Module:</strong>{' '}
                                {selectedComponent.module_namespace}
                              </p>
                              <p className="text-sm text-gray-600">
                                <strong>IRI:</strong> {selectedComponent.iri}
                              </p>
                            </div>

                            <div className="flex gap-2">
                              <Button
                                onClick={() =>
                                  exploreComponentNeighborhood(
                                    selectedComponent
                                  )
                                }
                                size="sm"
                              >
                                <Search className="h-4 w-4 mr-1" />
                                Explore Neighborhood
                              </Button>
                              <Button
                                variant="outline"
                                onClick={() => setSelectedComponent(null)}
                                size="sm"
                              >
                                Clear Selection
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        <Navigation className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>Select a component to explore its details</p>
                      </div>
                    )}
                  </div>
                </TabsContent>

                {/* Visualization Tab */}
                <TabsContent value="visualization" className="h-full m-0">
                  <SemanticGraphVisualization
                    tenantId={tenantId}
                    selectedComponent={selectedComponent}
                    selectedPath={selectedPath}
                    onComponentSelect={handleComponentSelect}
                  />
                </TabsContent>

                {/* Patterns Tab */}
                <TabsContent value="patterns" className="h-full m-0">
                  <div className="h-full p-4 overflow-auto">
                    {selectedPattern ? (
                      <Card>
                        <CardHeader>
                          <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="h-4 w-4" />
                            {selectedPattern.pattern_type.replace('_', ' ')}
                            <Badge variant="outline">
                              {selectedPattern.confidence}
                            </Badge>
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-4">
                            <p>{selectedPattern.description}</p>

                            <div>
                              <h4 className="font-medium mb-2">
                                Components ({selectedPattern.components.length})
                              </h4>
                              <div className="flex flex-wrap gap-1">
                                {selectedPattern.components.map((comp, idx) => (
                                  <Badge
                                    key={idx}
                                    className={getComponentTypeColor(
                                      comp.component_type
                                    )}
                                    onClick={() => handleComponentSelect(comp)}
                                    style={{ cursor: 'pointer' }}
                                  >
                                    {comp.name}
                                  </Badge>
                                ))}
                              </div>
                            </div>

                            {selectedPattern.evidence.length > 0 && (
                              <div>
                                <h4 className="font-medium mb-2">Evidence</h4>
                                <ul className="text-sm space-y-1">
                                  {selectedPattern.evidence.map(
                                    (evidence, idx) => (
                                      <li key={idx}>• {evidence}</li>
                                    )
                                  )}
                                </ul>
                              </div>
                            )}

                            {selectedPattern.recommendations.length > 0 && (
                              <div>
                                <h4 className="font-medium mb-2">
                                  Recommendations
                                </h4>
                                <ul className="text-sm space-y-1">
                                  {selectedPattern.recommendations.map(
                                    (rec, idx) => (
                                      <li
                                        key={idx}
                                        className="flex items-start gap-1"
                                      >
                                        <Lightbulb className="h-3 w-3 mt-0.5 text-yellow-500" />
                                        {rec}
                                      </li>
                                    )
                                  )}
                                </ul>
                              </div>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        <TrendingUp className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>Select a pattern to view its details</p>
                      </div>
                    )}
                  </div>
                </TabsContent>

                {/* Hotspots Tab */}
                <TabsContent value="hotspots" className="h-full m-0">
                  <div className="h-full p-4 overflow-auto">
                    {hotspots ? (
                      <div className="space-y-6">
                        {/* Complexity Hotspots */}
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <AlertTriangle className="h-4 w-4 text-orange-500" />
                              Complexity Hotspots
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-2">
                              {hotspots.complexity_hotspots
                                .slice(0, 5)
                                .map((hotspot, idx) => (
                                  <div
                                    key={idx}
                                    className="flex items-center justify-between p-2 border rounded cursor-pointer hover:bg-gray-50"
                                    onClick={() =>
                                      handleComponentSelect(hotspot.component)
                                    }
                                  >
                                    <div className="flex items-center gap-2">
                                      <Badge
                                        className={getComponentTypeColor(
                                          hotspot.component.component_type
                                        )}
                                      >
                                        {hotspot.component.component_type}
                                      </Badge>
                                      <span className="font-medium">
                                        {hotspot.component.name}
                                      </span>
                                    </div>
                                    <Badge
                                      className={getHotspotSeverityColor(
                                        hotspot.score
                                      )}
                                    >
                                      {hotspot.score.toFixed(1)}
                                    </Badge>
                                  </div>
                                ))}
                            </div>
                          </CardContent>
                        </Card>

                        {/* Coupling Hotspots */}
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <GitBranch className="h-4 w-4 text-red-500" />
                              Coupling Hotspots
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-2">
                              {hotspots.coupling_hotspots
                                .slice(0, 5)
                                .map((hotspot, idx) => (
                                  <div
                                    key={idx}
                                    className="flex items-center justify-between p-2 border rounded cursor-pointer hover:bg-gray-50"
                                    onClick={() =>
                                      handleComponentSelect(hotspot.component)
                                    }
                                  >
                                    <div className="flex items-center gap-2">
                                      <Badge
                                        className={getComponentTypeColor(
                                          hotspot.component.component_type
                                        )}
                                      >
                                        {hotspot.component.component_type}
                                      </Badge>
                                      <span className="font-medium">
                                        {hotspot.component.name}
                                      </span>
                                    </div>
                                    <div className="flex gap-1">
                                      <Badge
                                        variant="outline"
                                        className="text-xs"
                                      >
                                        In: {hotspot.incoming}
                                      </Badge>
                                      <Badge
                                        variant="outline"
                                        className="text-xs"
                                      >
                                        Out: {hotspot.outgoing}
                                      </Badge>
                                    </div>
                                  </div>
                                ))}
                            </div>
                          </CardContent>
                        </Card>

                        {/* Anti-pattern Hotspots */}
                        {hotspots.anti_pattern_hotspots.length > 0 && (
                          <Card>
                            <CardHeader>
                              <CardTitle className="flex items-center gap-2">
                                <AlertTriangle className="h-4 w-4 text-red-500" />
                                Anti-patterns
                              </CardTitle>
                            </CardHeader>
                            <CardContent>
                              <div className="space-y-2">
                                {hotspots.anti_pattern_hotspots.map(
                                  (pattern, idx) => (
                                    <div
                                      key={idx}
                                      className="p-2 border rounded cursor-pointer hover:bg-gray-50"
                                      onClick={() =>
                                        handlePatternSelect(pattern)
                                      }
                                    >
                                      <div className="flex items-center justify-between mb-1">
                                        <span className="font-medium">
                                          {pattern.pattern_type.replace(
                                            '_',
                                            ' '
                                          )}
                                        </span>
                                        <Badge variant="destructive">
                                          {pattern.confidence}
                                        </Badge>
                                      </div>
                                      <p className="text-sm text-gray-600">
                                        {pattern.description}
                                      </p>
                                    </div>
                                  )
                                )}
                              </div>
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        {loading ? (
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                        ) : (
                          <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        )}
                        <p>
                          {loading
                            ? 'Loading hotspots...'
                            : 'No hotspots data available'}
                        </p>
                      </div>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
};
