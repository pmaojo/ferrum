import { useCallback, useEffect, useMemo, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  ReactFlowProvider,
  useReactFlow,
  MiniMap,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { GraphNode } from './GraphNode';
import { ConnectionEdge } from './ConnectionEdge';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import type {
  GraphNode as GraphNodeType,
  GraphEdge as GraphEdgeType,
} from '@shared/schema';
import type { GraphNodeData } from '@/types/graph';
import { ContextualHelp } from '@/components/ContextualHelp';

interface SemanticGraphVisualizationProps {
  graphData?: { nodes: GraphNodeType[]; edges: GraphEdgeType[] };
  projectId: string;
  onNodeSelect: (node: Node<GraphNodeData> | null) => void;
  validationResults?: any[];
}

const nodeTypes = {
  custom: GraphNode,
};

const edgeTypes = {
  custom: ConnectionEdge,
};

/**
 * @kthulu:extend - Enhanced semantic visualization for Kthulu architecture
 * Shows real architecture with OWL ontology mapping, violation highlighting, and hierarchical views
 */
function SemanticGraphVisualizationInner({
  graphData,
  projectId,
  onNodeSelect,
  validationResults = [],
}: SemanticGraphVisualizationProps) {
  const { fitView } = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node<GraphNodeData> | null>(
    null
  );
  const [viewMode, setViewMode] = useState<
    'hierarchical' | 'flat' | 'semantic'
  >('hierarchical');
  const [collapsedModules, setCollapsedModules] = useState<Set<string>>(
    new Set()
  );
  const [violationFilter, setViolationFilter] = useState<
    'all' | 'violations' | 'clean'
  >('all');

  // Semantic edge colors based on OWL relationships
  const semanticEdgeColors = {
    definesUseCase: '#3b82f6', // blue
    hasPort: '#10b981', // green
    implementsPort: '#f59e0b', // amber
    usesPort: '#8b5cf6', // violet
    dependsOnModule: '#ef4444', // red
    emitsEvent: '#f97316', // orange
    handlesEvent: '#06b6d4', // cyan
    calls: '#6b7280', // gray
    default: '#00FF41', // matrix green
  };

  // Calculate semantic statistics
  const semanticStats = useMemo(() => {
    const stats = {
      totalNodes: nodes.length,
      modules: nodes.filter((n) => n.data.type === 'module').length,
      useCases: nodes.filter((n) => n.data.type === 'usecase').length,
      adapters: nodes.filter((n) => n.data.type === 'adapter').length,
      ports: nodes.filter((n) => n.data.type === 'port').length,
      entities: nodes.filter((n) => n.data.type === 'domainentity').length,
      events: nodes.filter((n) => n.data.type === 'domainevent').length,
      violations: nodes.filter((n) => n.data.violation).length,
      semanticRelations: edges.length,
    };
    return stats;
  }, [nodes, edges]);

  // Toggle module collapse/expand
  const toggleModule = useCallback((moduleId: string) => {
    setCollapsedModules((prev) => {
      const next = new Set(prev);
      if (next.has(moduleId)) {
        next.delete(moduleId);
      } else {
        next.add(moduleId);
      }
      return next;
    });
  }, []);

  // Convert backend data to ReactFlow format with semantic enhancements
  useEffect(() => {
    if (!graphData?.nodes) return;

    console.log(
      '🧠 SemanticGraph: Processing',
      graphData.nodes.length,
      'semantic nodes'
    );

    const flowNodes: Node<GraphNodeData>[] = graphData.nodes.map(
      (node: GraphNodeType, index: number) => {
        const parentId =
          (node.metadata as any)?.moduleId || (node.metadata as any)?.parentId;
        const isCollapsed = parentId ? collapsedModules.has(parentId) : false;

        // Enhanced positioning for hierarchical view
        let position = node.position;
        if (!position) {
          if (viewMode === 'hierarchical' && node.type === 'module') {
            // Modules in a grid
            position = {
              x: (index % 3) * 350,
              y: Math.floor(index / 3) * 300,
            };
          } else if (parentId) {
            // Child nodes positioned relative to parent
            const parentIndex = graphData.nodes.findIndex(
              (n) => n.id === parentId
            );
            const childIndex = graphData.nodes
              .filter(
                (n) =>
                  (n.metadata as any)?.moduleId === parentId ||
                  (n.metadata as any)?.parentId === parentId
              )
              .indexOf(node);

            position = {
              x: (parentIndex % 3) * 350 + 20 + (childIndex % 2) * 120,
              y:
                Math.floor(parentIndex / 3) * 300 +
                60 +
                Math.floor(childIndex / 2) * 80,
            };
          } else {
            // Default positioning
            position = {
              x: (index % 4) * 200 + 100,
              y: Math.floor(index / 4) * 150 + 100,
            };
          }
        }

        return {
          id: node.id,
          type: 'custom',
          position,
          data: {
            id: node.id,
            name: node.name,
            type: node.type,
            filePath: node.filePath,
            description: node.description,
            metadata: {
              ...node.metadata,
              semantic: true, // Mark as semantic node
              owlClass: `kth:${node.type.charAt(0).toUpperCase() + node.type.slice(1)}`,
            },
            collapsed:
              node.type === 'module' ? collapsedModules.has(node.id) : false,
          },
          parentNode: parentId,
          extent: parentId ? 'parent' : undefined,
          hidden: viewMode === 'hierarchical' && isCollapsed,
        };
      }
    );

    const flowEdges: Edge[] = (graphData.edges || []).map((edge: any) => {
      const edgeType = edge.type || 'default';
      const color =
        semanticEdgeColors[edgeType as keyof typeof semanticEdgeColors] ||
        semanticEdgeColors.default;

      // Check if edge should be hidden based on collapsed modules
      const sourceNode = flowNodes.find((n) => n.id === edge.sourceNodeId);
      const targetNode = flowNodes.find((n) => n.id === edge.targetNodeId);
      const isHidden = sourceNode?.hidden || targetNode?.hidden;

      return {
        id: edge.id,
        source: edge.sourceNodeId,
        target: edge.targetNodeId,
        type: 'custom',
        label: edge.type || 'relation',
        animated: true,
        style: {
          stroke: color,
          strokeWidth: 2,
          strokeDasharray: edge.type === 'dependsOnModule' ? '5,5' : undefined,
        },
        data: {
          type: edge.type,
          strokeColor: color,
          parameters: edge.parameters || [],
          methodCalls: edge.methodCalls || [],
          metadata: {
            ...edge.metadata,
            semantic: true,
            owlProperty: `kth:${edge.type}`,
          },
        },
        hidden: isHidden,
      };
    });

    setNodes(flowNodes);
    setEdges(flowEdges);

    // Auto-fit view
    if (flowNodes.length > 0) {
      setTimeout(() => {
        fitView?.({ padding: 0.1, includeHiddenNodes: false });
      }, 100);
    }
  }, [graphData, setNodes, setEdges, fitView, collapsedModules, viewMode]);

  // Apply validation results as violations
  useEffect(() => {
    if (!validationResults?.length) return;

    const nodeViolations = new Map<string, string>();
    const edgeViolations = new Map<string, string>();

    validationResults.forEach((v) => {
      if (v.status !== 'violation') return;

      if (v.sourceNodeId && v.targetNodeId) {
        const key = `${v.sourceNodeId}-${v.targetNodeId}`;
        const existing = edgeViolations.get(key);
        edgeViolations.set(
          key,
          existing ? `${existing}\n${v.message}` : v.message
        );
      } else if (v.sourceNodeId) {
        const existing = nodeViolations.get(v.sourceNodeId);
        nodeViolations.set(
          v.sourceNodeId,
          existing ? `${existing}\n${v.message}` : v.message
        );
      }
    });

    // Update nodes with violation information
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          violation: nodeViolations.has(n.id),
          violationMessage: nodeViolations.get(n.id),
        },
      }))
    );

    // Update edges with violation information
    setEdges((eds) =>
      eds.map((e) => {
        const key = `${e.source}-${e.target}`;
        const msg = edgeViolations.get(key);
        return {
          ...e,
          style: {
            ...(e.style || {}),
            stroke: msg
              ? '#ef4444'
              : e.data?.strokeColor || semanticEdgeColors.default,
            strokeWidth: msg ? 3 : 2,
          },
          data: {
            ...e.data,
            violationMessage: msg,
            violation: !!msg,
          },
        };
      })
    );
  }, [validationResults, setNodes, setEdges]);

  // Filter nodes based on violation filter
  const filteredNodes = useMemo(() => {
    if (violationFilter === 'all') return nodes;
    if (violationFilter === 'violations')
      return nodes.filter((n) => n.data.violation);
    if (violationFilter === 'clean')
      return nodes.filter((n) => !n.data.violation);
    return nodes;
  }, [nodes, violationFilter]);

  const onNodeClick = useCallback(
    (event: React.MouseEvent, node: Node<GraphNodeData>) => {
      event.stopPropagation();

      if (node.data.type === 'module') {
        toggleModule(node.id);
        return;
      }

      setSelectedNode(node);
      onNodeSelect(node);
    },
    [onNodeSelect, toggleModule]
  );

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    onNodeSelect(null);
  }, [onNodeSelect]);

  if (nodes.length === 0) {
    return (
      <Card className="w-full h-full flex items-center justify-center">
        <CardContent className="text-center">
          <p className="text-muted-foreground mb-4">No hay grafo</p>
          <Button asChild>
            <a href="/graph/refresh">Refrescar</a>
          </Button>
          <ContextualHelp state="no-graph" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="w-full h-full flex flex-col">
      {/* Semantic Control Panel */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            🧠 Semantic Architecture Visualization
            <Badge variant="outline">OWL Ontology</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between mb-4">
            <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as any)}>
              <TabsList>
                <TabsTrigger value="hierarchical">Hierarchical</TabsTrigger>
                <TabsTrigger value="flat">Flat</TabsTrigger>
                <TabsTrigger value="semantic">Semantic</TabsTrigger>
              </TabsList>
            </Tabs>

            <div className="flex items-center gap-2">
              <Button
                variant={violationFilter === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViolationFilter('all')}
              >
                All ({semanticStats.totalNodes})
              </Button>
              <Button
                variant={
                  violationFilter === 'violations' ? 'destructive' : 'outline'
                }
                size="sm"
                onClick={() => setViolationFilter('violations')}
              >
                Violations ({semanticStats.violations})
              </Button>
              <Button
                variant={violationFilter === 'clean' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViolationFilter('clean')}
              >
                Clean ({semanticStats.totalNodes - semanticStats.violations})
              </Button>
            </div>
          </div>

          {/* Semantic Statistics */}
          <div className="grid grid-cols-4 md:grid-cols-8 gap-2 text-center">
            <div className="p-2 bg-purple-50 rounded">
              <div className="text-lg font-bold text-purple-600">
                {semanticStats.modules}
              </div>
              <div className="text-xs text-purple-500">Modules</div>
            </div>
            <div className="p-2 bg-blue-50 rounded">
              <div className="text-lg font-bold text-blue-600">
                {semanticStats.useCases}
              </div>
              <div className="text-xs text-blue-500">Use Cases</div>
            </div>
            <div className="p-2 bg-orange-50 rounded">
              <div className="text-lg font-bold text-orange-600">
                {semanticStats.adapters}
              </div>
              <div className="text-xs text-orange-500">Adapters</div>
            </div>
            <div className="p-2 bg-green-50 rounded">
              <div className="text-lg font-bold text-green-600">
                {semanticStats.ports}
              </div>
              <div className="text-xs text-green-500">Ports</div>
            </div>
            <div className="p-2 bg-cyan-50 rounded">
              <div className="text-lg font-bold text-cyan-600">
                {semanticStats.entities}
              </div>
              <div className="text-xs text-cyan-500">Entities</div>
            </div>
            <div className="p-2 bg-yellow-50 rounded">
              <div className="text-lg font-bold text-yellow-600">
                {semanticStats.events}
              </div>
              <div className="text-xs text-yellow-500">Events</div>
            </div>
            <div className="p-2 bg-red-50 rounded">
              <div className="text-lg font-bold text-red-600">
                {semanticStats.violations}
              </div>
              <div className="text-xs text-red-500">Violations</div>
            </div>
            <div className="p-2 bg-gray-50 rounded">
              <div className="text-lg font-bold text-gray-600">
                {semanticStats.semanticRelations}
              </div>
              <div className="text-xs text-gray-500">Relations</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* React Flow Graph */}
      <div className="flex-1 bg-black rounded-lg overflow-hidden">
        <ReactFlow
          nodes={filteredNodes}
          edges={edges.filter((e) => {
            const sourceVisible = filteredNodes.some((n) => n.id === e.source);
            const targetVisible = filteredNodes.some((n) => n.id === e.target);
            return sourceVisible && targetVisible && !e.hidden;
          })}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          attributionPosition="bottom-left"
        >
          <Background color="#00ff41" gap={16} />
          <Controls />
          <MiniMap
            nodeColor={(node) => {
              if (node.data?.violation) return '#ef4444';
              const type = node.data?.type;
              if (type === 'module') return '#a855f7';
              if (type === 'usecase') return '#3b82f6';
              if (type === 'adapter') return '#f97316';
              if (type === 'port') return '#10b981';
              return '#6b7280';
            }}
            maskColor="rgba(0, 0, 0, 0.8)"
          />
        </ReactFlow>
      </div>
    </div>
  );
}

export function SemanticGraphVisualization(
  props: SemanticGraphVisualizationProps
) {
  return (
    <ReactFlowProvider>
      <SemanticGraphVisualizationInner {...props} />
    </ReactFlowProvider>
  );
}
