import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useSemanticQueries, useSemanticExecuteQuery } from '@/hooks/use-graph';
import { TemplateProvider } from '@/context/TemplateContext';
import { GraphEditor } from '@/components/graph/GraphEditor';
import type {
  GraphNode as GraphNodeType,
  GraphEdge as GraphEdgeType,
} from '@shared/schema';

interface SemanticQueryPanelProps {
  projectId: string;
}

interface QueryResult {
  rows: any[];
  graph: { nodes: GraphNodeType[]; edges: GraphEdgeType[] };
}

export function SemanticQueryPanel({ projectId }: SemanticQueryPanelProps) {
  const { data } = useSemanticQueries(projectId);
  const executeQuery = useSemanticExecuteQuery();
  const [selected, setSelected] = useState<string>('');
  const [queryText, setQueryText] = useState<string>('');
  const [result, setResult] = useState<QueryResult | null>(null);
  const [view, setView] = useState<'table' | 'graph'>('table');

  const handleRun = async () => {
    if (!selected) return;
    const res = await executeQuery.mutateAsync({
      projectId,
      queryId: selected,
    });
    setResult(res);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Semantic Queries</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2 mb-4">
          {data?.queries?.map((q: any) => (
            <Button
              key={q.id}
              variant={selected === q.id ? 'default' : 'outline'}
              onClick={() => {
                setSelected(q.id);
                setQueryText(q.sparql);
                setResult(null);
              }}
            >
              {q.id}
            </Button>
          ))}
        </div>
        {queryText && (
          <pre className="p-2 bg-muted rounded mb-4 text-sm overflow-x-auto">
            {queryText}
          </pre>
        )}
        <Button
          onClick={handleRun}
          disabled={!selected || executeQuery.isPending}
        >
          Run Query
        </Button>
        {result && (
          <Tabs
            defaultValue="table"
            className="mt-4"
            onValueChange={(v) => setView(v as any)}
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="table">Table</TabsTrigger>
              <TabsTrigger value="graph">Graph</TabsTrigger>
            </TabsList>
            <TabsContent value="table">
              {result.rows.length === 0 ? (
                <div className="text-center text-sm text-muted-foreground py-8">
                  No results
                </div>
              ) : (
                <ScrollArea className="h-96">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {Object.keys(result.rows[0]).map((v) => (
                          <TableHead key={v}>?{v}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {result.rows.map((row, idx) => (
                        <TableRow key={idx}>
                          {Object.keys(row).map((v) => (
                            <TableCell key={v}>{row[v].value}</TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              )}
            </TabsContent>
            <TabsContent value="graph">
              <div className="h-96">
                <TemplateProvider projectId={projectId}>
                  <GraphEditor
                    graphData={result.graph || { nodes: [], edges: [] }}
                    projectId={projectId}
                    onNodeSelect={() => {}}
                  />
                </TemplateProvider>
              </div>
            </TabsContent>
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
}

export default SemanticQueryPanel;
