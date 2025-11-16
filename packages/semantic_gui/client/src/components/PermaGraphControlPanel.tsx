import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { SPARQLQueryInterface } from './SPARQLQueryInterface';
import { SemanticQueryPanel } from './semantic/SemanticQueryPanel';
import {
  usePermaGraphWebSocket,
  usePermaGraphAgentStatus,
  usePermaGraphEventListener,
} from '@/hooks/usePermaGraphWebSocket';
import {
  usePermaGraphInit,
  usePermaGraphSync,
  usePermaGraphAgents,
  usePermaGraphValidate,
  usePermaGraphStatus,
  usePermaGraphMetrics,
  usePermaGraphQueries,
  usePermaGraphSPARQL,
} from '@/hooks/use-graph';
import { Star } from 'lucide-react';
import { AgentManagementDashboard } from './agents/AgentManagementDashboard';

interface PermaGraphControlPanelProps {
  projectId: string;
  kthuluPath?: string;
}

/**
 * @kthulu:extend - Control panel for PermaGraph semantic engine
 * Provides UI for managing agents, executing SPARQL queries, and ontology operations
 */
export function PermaGraphControlPanel({
  projectId,
  kthuluPath,
}: PermaGraphControlPanelProps) {
  const { toast } = useToast();

  // WebSocket connection for real-time updates
  const { isConnected } = usePermaGraphWebSocket(projectId);
  usePermaGraphEventListener(projectId, 'violation-found', (data) => {
    toast({
      title: 'Violation detected',
      description: data.message,
      variant: 'destructive',
    });
  });
  const agentStatuses = usePermaGraphAgentStatus(projectId);

  const { data: status } = usePermaGraphStatus(projectId);
  const { data: agents } = usePermaGraphAgents(projectId);
  const { data: metrics } = usePermaGraphMetrics(projectId);
  const { data: sparqlPresets } = usePermaGraphQueries(projectId);
  const executePreset = usePermaGraphSPARQL();
  const [presetFavorites, setPresetFavorites] = useState<string[]>([]);
  const [presetHistory, setPresetHistory] = useState<
    { id: string; query: string; timestamp: string }[]
  >([]);

  useEffect(() => {
    const fav = localStorage.getItem('sparqlPresetFavorites');
    const hist = localStorage.getItem('sparqlPresetHistory');
    if (fav) {
      try {
        setPresetFavorites(JSON.parse(fav));
      } catch {
        // ignore
      }
    }
    if (hist) {
      try {
        setPresetHistory(JSON.parse(hist));
      } catch {
        // ignore
      }
    }
  }, []);

  const togglePresetFavorite = (id: string) => {
    const newFav = presetFavorites.includes(id)
      ? presetFavorites.filter((f) => f !== id)
      : [...presetFavorites, id];
    setPresetFavorites(newFav);
    localStorage.setItem('sparqlPresetFavorites', JSON.stringify(newFav));
  };

  const addPresetHistory = (item: { id: string; query: string }) => {
    const entry = { ...item, timestamp: new Date().toISOString() };
    const newHist = [...presetHistory, entry];
    setPresetHistory(newHist);
    localStorage.setItem('sparqlPresetHistory', JSON.stringify(newHist));
  };

  const handleExecutePreset = (q: { id: string; query: string }) => {
    executePreset.mutate({ projectId, query: q.query });
    addPresetHistory(q);
  };

  const initPermaGraph = usePermaGraphInit();
  const sync = usePermaGraphSync();
  const validate = usePermaGraphValidate();

  const handleInit = () => {
    initPermaGraph.mutate(projectId, {
      onSuccess: () => {
        toast({
          title: 'PermaGraph Initialized',
          description: 'Semantic engine is ready',
        });
      },
      onError: (error) => {
        toast({
          title: 'Initialization Failed',
          description: error.message,
          variant: 'destructive',
        });
      },
    });
  };

  const handleSync = () => {
    if (!kthuluPath) {
      toast({
        title: 'Kthulu Path Required',
        description: 'Please connect to a Kthulu project first',
        variant: 'destructive',
      });
      return;
    }

    sync.mutate(
      { projectId, kthuluPath },
      {
        onSuccess: () => {
          toast({
            title: 'PermaGraph Synced',
            description: 'Project data synchronized successfully',
          });
        },
        onError: (error) => {
          toast({
            title: 'Sync Failed',
            description: error.message,
            variant: 'destructive',
          });
        },
      }
    );
  };

  const handleValidate = () => {
    validate.mutate(projectId, {
      onSuccess: (result) => {
        const report = result.validation;
        toast({
          title: report.isConsistent
            ? 'Validation Passed'
            : 'Validation Issues Found',
          description: report.isConsistent
            ? 'Architecture is consistent'
            : `Found ${report.violatedRules.length} violations`,
          variant: report.isConsistent ? 'default' : 'destructive',
        });
      },
      onError: (error) => {
        toast({
          title: 'Validation Failed',
          description: error.message,
          variant: 'destructive',
        });
      },
    });
  };

  if (!status?.isInitialized) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🧠 PermaGraph Semantic Engine
            <Badge variant="secondary">Not Initialized</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground mb-4">
            Initialize PermaGraph to enable semantic reasoning and agent-based
            analysis.
          </p>
          <Button onClick={handleInit} disabled={initPermaGraph.isPending}>
            {initPermaGraph.isPending
              ? 'Initializing...'
              : 'Initialize PermaGraph'}
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (stats && stats.stats.totalTriples === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🧠 PermaGraph Semantic Engine
            <Badge variant="secondary">Sin ontología</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground mb-4">
            No hay ontología cargada. Sincroniza para importar los datos desde
            tu proyecto Kthulu.
          </p>
          <Button
            onClick={handleSync}
            disabled={sync.isPending || !kthuluPath}
          >
            {sync.isPending ? 'Sincronizando...' : 'Sincronizar'}
          </Button>
          <ContextualHelp state="no-ontology" />
        </CardContent>
      </Card>
    );
  }


  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          🧠 PermaGraph Control Panel
          <Badge>Active</Badge>
          <Badge variant={isConnected ? 'default' : 'secondary'}>
            {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="agents">Agents</TabsTrigger>
            <TabsTrigger value="sparql">SPARQL</TabsTrigger>
            <TabsTrigger value="presets">SPARQL Presets</TabsTrigger>
            <TabsTrigger value="semantic">Semantic Queries</TabsTrigger>
            <TabsTrigger value="validation">Validation</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6 mt-6">
            {/* Ontology Management */}
            <div className="space-y-3">
              <h4 className="font-medium">Ontology Management</h4>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  onClick={handleSync}
                  disabled={sync.isPending || !kthuluPath}
                  variant="outline"
                  size="sm"
                >
                  {sync.isPending ? 'Syncing...' : 'Sync'}
                </Button>
                <Button
                  onClick={handleValidate}
                  disabled={validate.isPending}
                  variant="outline"
                  size="sm"
                >
                  {validate.isPending ? 'Validating...' : 'Validate'}
                </Button>
              </div>
              {metrics && (
                <div className="text-sm text-muted-foreground">
                  <div>
                    Reasoner ops: {metrics.reasoning?.recent_operations || 0}
                  </div>
                  <div>Queries: {metrics.queries?.recent_queries || 0}</div>
                  <div>Syncs: {metrics.synchronization?.recent_syncs || 0}</div>
                </div>
              )}
            </div>

            <Separator />

            {/* Quick Stats */}
            <div className="space-y-3">
              <h4 className="font-medium">System Status</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-3 border rounded">
                  <div className="text-2xl font-bold text-blue-600">
                    {agents?.agents.filter(
                      (a: any) =>
                        (agentStatuses[a.id]?.status || a.status) === 'running'
                    ).length || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Active Agents
                  </div>
                </div>
                <div className="text-center p-3 border rounded">
                  <div className="text-2xl font-bold text-green-600">
                    {metrics?.reasoning?.recent_operations || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Reasoner Ops
                  </div>
                </div>
                <div className="text-center p-3 border rounded">
                  <div className="text-2xl font-bold text-purple-600">
                    {metrics?.queries?.recent_queries || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">Queries</div>
                </div>
                <div className="text-center p-3 border rounded">
                  <div className="text-2xl font-bold text-orange-600">
                    {metrics?.synchronization?.recent_syncs || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">Syncs</div>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="agents" className="mt-6">
            <AgentManagementDashboard projectId={projectId} />
          </TabsContent>

          <TabsContent value="sparql" className="mt-6">
            <SPARQLQueryInterface projectId={projectId} />
          </TabsContent>
          <TabsContent value="presets" className="space-y-6 mt-6">
            <Card>
              <CardHeader>
                <CardTitle>SPARQL Presets</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {sparqlPresets?.queries && sparqlPresets.queries.length > 0 ? (
                  sparqlPresets.queries.map((p) => (
                    <div
                      key={p.id}
                      className="flex items-center justify-between"
                    >
                      <Button
                        variant="link"
                        className="p-0 h-auto"
                        onClick={() => handleExecutePreset(p)}
                      >
                        {p.id}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => togglePresetFavorite(p.id)}
                      >
                        <Star
                          className={
                            presetFavorites.includes(p.id) ? 'fill-current' : ''
                          }
                          size={16}
                        />
                      </Button>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted-foreground">
                    No presets available
                  </div>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>History</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {presetHistory.length === 0 ? (
                  <div className="text-sm text-muted-foreground">
                    No history yet
                  </div>
                ) : (
                  presetHistory
                    .slice()
                    .sort(
                      (a, b) =>
                        new Date(b.timestamp).getTime() -
                        new Date(a.timestamp).getTime()
                    )
                    .map((h) => (
                      <div
                        key={h.timestamp}
                        className="flex items-center justify-between"
                      >
                        <Button
                          variant="link"
                          className="p-0 h-auto"
                          onClick={() => handleExecutePreset(h)}
                        >
                          {h.id}
                        </Button>
                        <span className="text-xs text-muted-foreground">
                          {new Date(h.timestamp).toLocaleString()}
                        </span>
                      </div>
                    ))
                )}
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="semantic" className="mt-6">
            <SemanticQueryPanel projectId={projectId} />
          </TabsContent>

          <TabsContent value="validation" className="space-y-6 mt-6">
            <div className="space-y-3">
              <h4 className="font-medium">Architecture Validation</h4>
              <div className="space-y-4">
                <Button
                  onClick={handleValidate}
                  disabled={validate.isPending}
                  className="w-full"
                >
                  {validate.isPending
                    ? 'Validating Architecture...'
                    : 'Run Full Validation'}
                </Button>

                <div className="text-sm text-muted-foreground space-y-2">
                  <div>
                    <strong>Validation Rules:</strong>
                  </div>
                  <ul className="list-disc list-inside space-y-1 ml-4">
                    <li>Dependency Inversion Principle (DIP)</li>
                    <li>Bounded Context Integrity</li>
                    <li>Aggregate Consistency</li>
                    <li>Port Implementation Coverage</li>
                    <li>Hexagonal Architecture Compliance</li>
                  </ul>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
