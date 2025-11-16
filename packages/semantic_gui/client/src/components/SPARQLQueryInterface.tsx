import { useEffect, useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { useToast } from '@/hooks/use-toast';
import { usePermaGraphSPARQL, usePermaGraphQueries } from '@/hooks/use-graph';
import { GraphicalSPARQLBuilder } from './sparql/GraphicalSPARQLBuilder';
import { PredefinedQueries } from './sparql/PredefinedQueries';
import { GraphEditor } from './graph/GraphEditor';
import { TemplateProvider } from '@/context/TemplateContext';
import type {
  GraphNode as GraphNodeType,
  GraphEdge as GraphEdgeType,
} from '@shared/schema';
import { Star, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@radix-ui/react-tabs';

interface SPARQLQueryInterfaceProps {
  projectId: string;
}

interface SPARQLBinding {
  [variable: string]: {
    type: string;
    value: string;
  };
}

interface SPARQLResult {
  head: {
    vars: string[];
  };
  results: {
    bindings: SPARQLBinding[];
  };
}

interface HistoryItem {
  id: string;
  query: string;
  timestamp: string;
  favorite: boolean;
}

/**
 * @kthulu:extend - Advanced SPARQL query interface for PermaGraph
 * Provides graphical query builder and result visualization
 */
export function SPARQLQueryInterface({ projectId }: SPARQLQueryInterfaceProps) {
  const { toast } = useToast();
  const [customQuery, setCustomQuery] = useState('');
  const [queryResults, setQueryResults] = useState<SPARQLResult | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [querySearch, setQuerySearch] = useState('');
  const [viewMode, setViewMode] = useState<'table' | 'graph'>('table');
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [graphData, setGraphData] = useState<{
    nodes: GraphNodeType[];
    edges: GraphEdgeType[];
  }>({
    nodes: [],
    edges: [],
  });

  const { data: queries } = usePermaGraphQueries(projectId);
  const executeSPARQL = usePermaGraphSPARQL();
  const [favorites, setFavorites] = useState<string[]>([]);

  useEffect(() => {
    const stored = localStorage.getItem('sparqlHistory');
    if (stored) {
      setHistory(JSON.parse(stored));
    }

    const storedFavorites = localStorage.getItem('sparqlFavorites');
    if (storedFavorites) {
      setFavorites(JSON.parse(storedFavorites));
    }
  }, []);

  const saveHistory = (items: HistoryItem[]) => {
    setHistory(items);
    localStorage.setItem('sparqlHistory', JSON.stringify(items));
  };

  const addToHistory = (query: string) => {
    const entry: HistoryItem = {
      id: Date.now().toString(),
      query,
      timestamp: new Date().toISOString(),
      favorite: false,
    };
    saveHistory([...history, entry]);
  };

  const toggleFavorite = (id: string) => {
    const updated = history.map((h) =>
      h.id === id ? { ...h, favorite: !h.favorite } : h
    );
    saveHistory(updated);
  };

  const toggleQueryFavorite = (queryId: string) => {
    const newFavorites = favorites.includes(queryId)
      ? favorites.filter((id) => id !== queryId)
      : [...favorites, queryId];
    setFavorites(newFavorites);
    localStorage.setItem('sparqlFavorites', JSON.stringify(newFavorites));
  };

  const handleExecuteQuery = async (query: string) => {
    if (!query.trim()) {
      toast({
        title: 'Query Required',
        description: 'Please enter a SPARQL query',
        variant: 'destructive',
      });
      return;
    }

    setIsExecuting(true);
    try {
      const result = await executeSPARQL.mutateAsync({
        projectId,
        query,
      });

      setQueryResults(result.results);
      addToHistory(query);
      toast({
        title: 'Query Executed',
        description: `Found ${result.results.results.bindings.length} results`,
      });
    } catch (error: any) {
      toast({
        title: 'Query Failed',
        description: error.message,
        variant: 'destructive',
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const handleExecuteCustomQuery = async () => {
    await handleExecuteQuery(customQuery);
  };

  const handleExecuteLibraryQuery = async (query: string) => {
    setCustomQuery(query);
    await handleExecuteQuery(query);
  };

  const clearResults = () => {
    setQueryResults(null);
  };

  const exportJSON = () => {
    if (!queryResults) return;
    const blob = new Blob(
      [JSON.stringify(queryResults.results.bindings, null, 2)],
      { type: 'application/json' }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'results.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportCSV = () => {
    if (!queryResults) return;
    const headers = queryResults.head.vars;
    const rows = queryResults.results.bindings.map((b) =>
      headers.map((h) => b[h]?.value ?? '').join(',')
    );
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'results.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    if (!queryResults) {
      setGraphData({ nodes: [], edges: [] });
      return;
    }
    const vars = queryResults.head.vars;
    const nodeMap = new Map<string, GraphNodeType>();
    const edges: GraphEdgeType[] = [];
    let index = 0;
    queryResults.results.bindings.forEach((binding) => {
      vars.forEach((v) => {
        const val = binding[v]?.value;
        if (val && !nodeMap.has(val)) {
          nodeMap.set(val, {
            id: val,
            name: val,
            type: 'result',
            position: { x: (index % 5) * 150, y: Math.floor(index / 5) * 150 },
            filePath: null as any,
            description: null as any,
            metadata: {},
            templateId: 'query',
            projectId,
          } as any);
          index++;
        }
      });
      if (vars.length >= 2) {
        const sourceVal = binding[vars[0]]?.value;
        const targetVal = binding[vars[1]]?.value;
        if (sourceVal && targetVal) {
          edges.push({
            id: `${sourceVal}-${targetVal}-${edges.length}`,
            sourceNodeId: sourceVal,
            targetNodeId: targetVal,
            type: 'result',
            metadata: {},
            projectId,
          } as any);
        }
      }
    });
    setGraphData({ nodes: Array.from(nodeMap.values()), edges });
  }, [queryResults, projectId]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🔍 SPARQL Query Interface
            <Badge variant="outline">Semantic Queries</Badge>
          </CardTitle>
        </CardHeader>
      </Card>

      {/* Main Interface */}
      <Tabs defaultValue="predefined" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="predefined">Query Library</TabsTrigger>
          <TabsTrigger value="builder">Visual Builder</TabsTrigger>
          <TabsTrigger value="custom">Custom Query</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="predefined" className="mt-6">
          <PredefinedQueries
            onQuerySelect={setCustomQuery}
            onExecuteQuery={handleExecuteLibraryQuery}
            favorites={favorites}
            onToggleFavorite={toggleQueryFavorite}
            presets={queries?.queries ?? []}
          />
        </TabsContent>

        <TabsContent value="builder" className="mt-6">
          <GraphicalSPARQLBuilder
            onQueryChange={setCustomQuery}
            initialQuery={customQuery}
          />
        </TabsContent>

        <TabsContent value="custom" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Custom SPARQL Query</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                placeholder="PREFIX kth: <http://kthulu.io/ontology#>&#10;SELECT ?module WHERE {&#10;  ?module a kth:Module .&#10;}"
                value={customQuery}
                onChange={(e) => setCustomQuery(e.target.value)}
                rows={12}
                className="font-mono text-sm"
              />
              <div className="flex gap-2">
                <Button
                  onClick={handleExecuteCustomQuery}
                  disabled={isExecuting || !customQuery.trim()}
                  className="flex-1"
                >
                  {isExecuting ? 'Executing...' : 'Execute Query'}
                </Button>
                <Button
                  onClick={() => setCustomQuery('')}
                  variant="outline"
                  size="sm"
                >
                  Clear
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Query History</CardTitle>
            </CardHeader>
            <CardContent>
              {history.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Search className="w-12 h-12 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No History Yet</h3>
                  <p>Execute some queries to see them here.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {history
                    .slice()
                    .sort(
                      (a, b) =>
                        Number(b.favorite) - Number(a.favorite) ||
                        new Date(b.timestamp).getTime() -
                          new Date(a.timestamp).getTime()
                    )
                    .map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between p-3 border rounded hover:bg-muted/50"
                      >
                        <div className="flex-1">
                          <Button
                            variant="link"
                            className="p-0 h-auto justify-start"
                            onClick={() => setCustomQuery(item.query)}
                          >
                            <div className="text-left">
                              <div className="font-medium">
                                {new Date(item.timestamp).toLocaleString()}
                              </div>
                              <div className="text-xs text-muted-foreground line-clamp-1">
                                {item.query.split('\n')[0]}
                              </div>
                            </div>
                          </Button>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleFavorite(item.id)}
                        >
                          <Star
                            className={cn(
                              'w-4 h-4',
                              item.favorite && 'fill-current text-yellow-500'
                            )}
                          />
                        </Button>
                      </div>
                    ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Query Results */}
      {queryResults && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                📊 Query Results
                <Badge variant="secondary">
                  {queryResults.results.bindings.length} results
                </Badge>
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setViewMode(viewMode === 'table' ? 'graph' : 'table')
                  }
                >
                  {viewMode === 'table' ? 'Graph View' : 'Table View'}
                </Button>
                <Button variant="outline" size="sm" onClick={exportJSON}>
                  JSON
                </Button>
                <Button variant="outline" size="sm" onClick={exportCSV}>
                  CSV
                </Button>
                <Button onClick={clearResults} variant="outline" size="sm">
                  Clear
                </Button>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {queryResults.results.bindings.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No results found for this query.
              </div>
            ) : viewMode === 'table' ? (
              <ScrollArea className="h-96">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {queryResults.head.vars.map((variable) => (
                        <TableHead key={variable}>?{variable}</TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {queryResults.results.bindings.map((binding, index) => (
                      <TableRow key={index}>
                        {queryResults.head.vars.map((variable) => (
                          <TableCell key={variable}>
                            {binding[variable] ? (
                              <div className="space-y-1">
                                <div className="font-mono text-sm">
                                  {binding[variable].value}
                                </div>
                                <Badge variant="outline" className="text-xs">
                                  {binding[variable].type}
                                </Badge>
                              </div>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            ) : (
              <div className="h-96">
                <TemplateProvider projectId={projectId}>
                  <GraphEditor
                    graphData={graphData}
                    projectId={projectId}
                    onNodeSelect={() => {}}
                  />
                </TemplateProvider>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Query History */}
      <Card>
        <CardHeader>
          <CardTitle>Query History</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {history.length === 0 ? (
            <div className="text-sm text-muted-foreground">No history yet.</div>
          ) : (
            <div className="space-y-2">
              {history
                .slice()
                .sort(
                  (a, b) =>
                    Number(b.favorite) - Number(a.favorite) ||
                    new Date(b.timestamp).getTime() -
                      new Date(a.timestamp).getTime()
                )
                .map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between"
                  >
                    <Button
                      variant="link"
                      className="p-0 h-auto"
                      onClick={() => setCustomQuery(item.query)}
                    >
                      {new Date(item.timestamp).toLocaleString()}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleFavorite(item.id)}
                    >
                      <Star
                        className={item.favorite ? 'fill-current' : ''}
                        size={16}
                      />
                    </Button>
                  </div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Query Help */}
      <Card>
        <CardHeader>
          <CardTitle>SPARQL Query Help</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <h4 className="font-medium">Common Prefixes</h4>
            <div className="bg-muted p-3 rounded font-mono text-sm">
              PREFIX kth: &lt;http://kthulu.io/ontology#&gt;
              <br />
              PREFIX owl: &lt;http://www.w3.org/2002/07/owl#&gt;
              <br />
              PREFIX rdf: &lt;http://www.w3.org/1999/02/22-rdf-syntax-ns#&gt;
              <br />
              PREFIX rdfs: &lt;http://www.w3.org/2000/01/rdf-schema#&gt;
            </div>
          </div>

          <div className="space-y-2">
            <h4 className="font-medium">Kthulu Ontology Classes</h4>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
              <Badge variant="outline">kth:Module</Badge>
              <Badge variant="outline">kth:UseCase</Badge>
              <Badge variant="outline">kth:Port</Badge>
              <Badge variant="outline">kth:Adapter</Badge>
              <Badge variant="outline">kth:DomainEntity</Badge>
              <Badge variant="outline">kth:DomainEvent</Badge>
            </div>
          </div>

          <div className="space-y-2">
            <h4 className="font-medium">Common Properties</h4>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
              <Badge variant="outline">kth:definesUseCase</Badge>
              <Badge variant="outline">kth:hasPort</Badge>
              <Badge variant="outline">kth:implementsPort</Badge>
              <Badge variant="outline">kth:usesPort</Badge>
              <Badge variant="outline">kth:dependsOnModule</Badge>
              <Badge variant="outline">kth:emitsEvent</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
