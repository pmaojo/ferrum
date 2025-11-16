import { useCallback, useRef, useState, useEffect, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  ConnectionMode,
  Connection,
  ReactFlowProvider,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { GraphNode } from './GraphNode';
import { ConnectionEdge } from './ConnectionEdge';
import { SemanticGraphVisualization } from './SemanticGraphVisualization';
import { NodeCreationForm } from '../NodeCreationForm';
import { EdgeEditDialog } from '../EdgeEditDialog';
import { NodeConnectionEditor } from '../NodeConnectionEditor';
import {
  useCreateNode,
  useUpdateNode,
  useCreateEdge,
  useDeleteNode,
  useDeleteEdge,
  useValidationResults,
} from '@/hooks/use-graph';
import { useToast } from '@/hooks/use-toast';
import { useFMSounds } from '@/hooks/useFMSounds';
import { useTemplate } from '@/context/TemplateContext';
import type {
  GraphNode as GraphNodeType,
  GraphEdge as GraphEdgeType,
} from '@shared/schema';
import type { GraphNodeData } from '@/types/graph';

// Define outside component to prevent re-renders
const nodeTypes = {
  custom: GraphNode,
};

interface GraphEditorProps {
  graphData?: { nodes: GraphNodeType[]; edges: GraphEdgeType[] };
  projectId: string;
  onNodeSelect: (node: Node<GraphNodeData> | null) => void;
  useSemanticVisualization?: boolean; // @kthulu:extend - Toggle for semantic view
  focusNodeId?: string;
}

function GraphEditorInner({
  projectId,
  onNodeSelect,
  graphData,
  useSemanticVisualization = false,
  focusNodeId,
}: GraphEditorProps) {
  const { template: selectedTemplate } = useTemplate();
  const graph = graphData;
  const isLoading = !graph;
  const error = undefined;
  const createNodeMutation = useCreateNode();
  const updateNodeMutation = useUpdateNode();
  const createEdgeMutation = useCreateEdge();
  const deleteNodeMutation = useDeleteNode();
  const deleteEdgeMutation = useDeleteEdge();
  const { toast } = useToast();
  const { screenToFlowPosition, fitView } = useReactFlow();
  const {
    playNodeCreate,
    playConnection,
    playMatrixGlitch,
    playHover,
    playTerminalBoot,
    playDataStream,
    playQuantumResonance,
  } = useFMSounds(0.6);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node<GraphNodeData> | null>(
    null
  );
  const [showNodeForm, setShowNodeForm] = useState(false);
  const [pendingNodePosition, setPendingNodePosition] = useState<{
    x: number;
    y: number;
  }>({ x: 0, y: 0 });
  const [selectedEdge, setSelectedEdge] = useState<any>(null);
  const [showEdgeEditDialog, setShowEdgeEditDialog] = useState(false);
  const [showConnectionEditor, setShowConnectionEditor] = useState(false);
  const [pendingConnection, setPendingConnection] = useState<{
    sourceNode: any;
    targetNode: any;
    edge?: any;
  } | null>(null);
  const [collapsedModules, setCollapsedModules] = useState<Set<string>>(
    new Set()
  );
  const { data: validationResults } = useValidationResults(projectId);
  const edgeColorMap: Record<string, string> = {
    dependsOnModule: '#818cf8',
    usesAdapter: '#f97316',
    default: '#00FF41',
  };
  const toggleModule = useCallback((id: string) => {
    setCollapsedModules((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  // Convert backend data to ReactFlow format
  useEffect(() => {
    console.log('🔄 GraphEditor: Processing graph:', graph);

    if (graph && graph.nodes && Array.isArray(graph.nodes)) {
      console.log('📊 GraphEditor: Found', graph.nodes.length, 'nodes');

      const flowNodes: Node<GraphNodeData>[] = graph.nodes.map(
        (node: GraphNodeType, index: number) => {
          console.log(`🔧 Processing node ${index}:`, node);
          const parentId =
            (node.metadata as any)?.moduleId ||
            (node.metadata as any)?.parentId;
          return {
            id: node.id,
            type: 'custom',
            position: node.position || {
              x: (index % 3) * 200 + 100,
              y: Math.floor(index / 3) * 200 + 100,
            },
            data: {
              id: node.id,
              name: node.name,
              type: node.type,
              filePath: node.filePath,
              description: node.description,
              metadata: node.metadata,
              collapsed: collapsedModules.has(node.id),
            },
            parentNode: parentId,
            extent: parentId ? 'parent' : undefined,
          };
        }
      );

      const flowEdges: Edge[] = (graph.edges || []).map((edge: any) => {
        const color =
          edgeColorMap[edge.type as keyof typeof edgeColorMap] ||
          edgeColorMap.default;
        return {
          id: edge.id,
          source: edge.sourceNodeId,
          target: edge.targetNodeId,
          type: 'custom',
          label: edge.type || 'connection',
          animated: true,
          style: { stroke: color, strokeWidth: 2 },
          data: {
            type: edge.type,
            strokeColor: color,
            parameters: edge.parameters || [],
            methodCalls: edge.methodCalls || [],
            metadata: edge.metadata,
          },
        };
      });

      console.log(
        '✨ GraphEditor: Setting',
        flowNodes.length,
        'nodes and',
        flowEdges.length,
        'edges'
      );

      // Always update nodes to ensure they render
      setNodes(flowNodes);
      setEdges(flowEdges);

      // Fit view after nodes are loaded
      if (flowNodes.length > 0) {
        setTimeout(() => {
          console.log('🎯 Fitting view with', flowNodes.length, 'nodes');
          fitView?.({ padding: 0.2, includeHiddenNodes: false });
          playTerminalBoot(); // Sound when graph loads
        }, 200);
      }
    } else {
      console.log('❌ GraphEditor: No valid nodes found in graph');
    }
  }, [graph, setNodes, setEdges, fitView]);

  useEffect(() => {
    if (!focusNodeId) return;
    const target = nodes.find((n) => n.id === focusNodeId);
    if (target) {
      setSelectedNode(target);
      onNodeSelect(target);
      setTimeout(() => {
        fitView?.({
          nodes: [{ id: target.id }],
          padding: 0.2,
          includeHiddenNodes: false,
        });
      }, 100);
    }
  }, [focusNodeId, nodes, fitView, onNodeSelect]);

  // Highlight validation violations
  useEffect(() => {
    if (!validationResults) return;
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
    setEdges((eds) =>
      eds.map((e) => {
        const key = `${e.source}-${e.target}`;
        const msg = edgeViolations.get(key);
        return {
          ...e,
          style: {
            ...(e.style || {}),
            stroke: msg ? '#ff0000' : e.data?.strokeColor || '#00FF41',
            strokeWidth: 2,
          },
          data: { ...e.data, violationMessage: msg },
        };
      })
    );
  }, [validationResults, setNodes, setEdges]);

  // Manage module collapse/expand
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => {
        const hidden = n.parentNode
          ? collapsedModules.has(n.parentNode)
          : false;
        const isModule = n.data.type === 'module';
        return {
          ...n,
          hidden,
          data: {
            ...n.data,
            collapsed: isModule ? collapsedModules.has(n.id) : n.data.collapsed,
          },
        };
      })
    );
  }, [collapsedModules, setNodes]);

  useEffect(() => {
    setEdges((eds) =>
      eds.map((e) => {
        const sourceNode = nodes.find((n) => n.id === e.source);
        const targetNode = nodes.find((n) => n.id === e.target);
        const hidden = !!(sourceNode?.hidden || targetNode?.hidden);
        return { ...e, hidden };
      })
    );
  }, [nodes, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => {
      if (!params.source || !params.target) return;

      // Find the source and target nodes
      const sourceNode = nodes.find((n) => n.id === params.source);
      const targetNode = nodes.find((n) => n.id === params.target);

      if (!sourceNode || !targetNode) return;

      // Create the edge first
      const newEdge = {
        sourceNodeId: params.source,
        targetNodeId: params.target,
        type: 'depends',
        metadata: {},
        projectId,
        updatedAt: new Date(),
      };

      createEdgeMutation.mutate(newEdge, {
        onSuccess: (createdEdge) => {
          playConnection();

          // Show connection editor for the newly created edge
          setPendingConnection({
            sourceNode: {
              id: sourceNode.id,
              name: sourceNode.data.name,
              type: sourceNode.data.type,
            },
            targetNode: {
              id: targetNode.id,
              name: targetNode.data.name,
              type: targetNode.data.type,
            },
            edge: createdEdge,
          });
          setShowConnectionEditor(true);

          toast({
            title: 'Connection created',
            description: 'Configure connection properties',
          });
        },
        onError: () => {
          toast({
            title: 'Error',
            description: 'Failed to create connection.',
            variant: 'destructive',
          });
        },
      });
    },
    [projectId, createEdgeMutation, toast, nodes, playConnection]
  );

  const onNodeClick = useCallback(
    (event: React.MouseEvent, node: Node<GraphNodeData>) => {
      event.stopPropagation();
      if (node.data.type === 'module') {
        toggleModule(node.id);
        return;
      }
      console.log('🎯 Node clicked:', node.data.name, node.data);
      playQuantumResonance();
      setSelectedNode(node);
      onNodeSelect(node);
    },
    [onNodeSelect, playQuantumResonance, toggleModule]
  );

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    onNodeSelect(null);
    setSelectedEdge(null);
  }, [onNodeSelect]);

  const onEdgeDoubleClick = useCallback((edge: any) => {
    console.log('🔗 Edge double-clicked:', edge);
    setSelectedEdge(edge);
    setShowEdgeEditDialog(true);
  }, []);

  // Memoize edgeTypes to prevent React Flow warning
  const edgeTypes = useMemo(
    () => ({
      custom: (props: any) => (
        <ConnectionEdge {...props} onDoubleClick={onEdgeDoubleClick} />
      ),
    }),
    [onEdgeDoubleClick]
  );

  // Handle double click to create new node
  const onDoubleClick = useCallback(
    (event: React.MouseEvent) => {
      const position = screenToFlowPosition?.({
        x: event.clientX,
        y: event.clientY,
      });
      if (!position) return;

      setPendingNodePosition(position);
      setShowNodeForm(true);
    },
    [screenToFlowPosition]
  );

  // Handle node creation from form
  const handleNodeCreation = useCallback(
    async (nodeData: any) => {
      if (!selectedTemplate) {
        toast({
          title: 'MISSING_TEMPLATE',
          description: 'Select a template before creating nodes',
          variant: 'destructive',
        });
        return;
      }
      try {
        const newNodeData = {
          name: nodeData.name,
          type: nodeData.type,
          position: nodeData.position,
          templateId: selectedTemplate.id,
          projectId: projectId,
          description: nodeData.description || null,
          filePath: nodeData.filePath || null,
          metadata: {},
        };

        const createdNode = await createNodeMutation.mutateAsync(newNodeData);

        // Immediately add the new node to the local state for instant feedback
        if (createdNode) {
          const newFlowNode: Node<GraphNodeData> = {
            id: createdNode.id,
            type: 'custom',
            position: createdNode.position || nodeData.position,
            data: {
              id: createdNode.id,
              name: createdNode.name,
              type: createdNode.type,
              filePath: createdNode.filePath,
              description: createdNode.description,
              metadata: createdNode.metadata,
            },
          };

          setNodes((currentNodes) => [...currentNodes, newFlowNode]);
        }

        playNodeCreate();
        toast({
          title: 'Node Created',
          description: `${nodeData.type} node "${nodeData.name}" created successfully`,
        });
      } catch (error) {
        console.error('Node creation error:', error);
        toast({
          title: 'Error',
          description: 'Failed to create node',
          variant: 'destructive',
        });
      }
    },
    [createNodeMutation, selectedTemplate, projectId, toast, setNodes]
  );

  const onNodeDragStop = useCallback(
    (event: React.MouseEvent, node: Node<GraphNodeData>) => {
      updateNodeMutation.mutate({
        id: node.id,
        data: {
          position: node.position,
        },
      });
    },
    [updateNodeMutation]
  );

  const onNodesDelete = useCallback(
    (nodesToDelete: Node[]) => {
      nodesToDelete.forEach((node) => {
        deleteNodeMutation.mutate(node.id, {
          onSuccess: () => {
            playMatrixGlitch();
            toast({
              title: 'Node deleted',
              description: 'Node has been removed from the graph.',
            });
          },
          onError: () => {
            toast({
              title: 'Error',
              description: 'Failed to delete node.',
              variant: 'destructive',
            });
          },
        });
      });
    },
    [deleteNodeMutation, toast]
  );

  const onEdgesDelete = useCallback(
    (edgesToDelete: Edge[]) => {
      edgesToDelete.forEach((edge) => {
        deleteEdgeMutation.mutate(edge.id, {
          onSuccess: () => {
            toast({
              title: 'Connection removed',
              description: 'Connection has been deleted.',
            });
          },
          onError: () => {
            toast({
              title: 'Error',
              description: 'Failed to delete connection.',
              variant: 'destructive',
            });
          },
        });
      });
    },
    [deleteEdgeMutation, toast]
  );

  // Handle dropping new nodes from sidebar
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const nodeType = event.dataTransfer.getData('application/reactflow');
      if (!nodeType || !selectedTemplate) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNodeData = {
        id: `node_${Date.now()}_${Math.random()}`,
        name: `New ${nodeType}`,
        type: nodeType,
        position,
        metadata: {},
        templateId: selectedTemplate.id,
        projectId,
      };

      createNodeMutation.mutate(newNodeData, {
        onSuccess: (createdNode) => {
          // Immediately add to local state
          if (createdNode) {
            const newFlowNode: Node<GraphNodeData> = {
              id: createdNode.id,
              type: 'custom',
              position: createdNode.position || position,
              data: {
                id: createdNode.id,
                name: createdNode.name,
                type: createdNode.type,
                filePath: createdNode.filePath,
                description: createdNode.description,
                metadata: createdNode.metadata,
              },
            };

            setNodes((currentNodes) => [...currentNodes, newFlowNode]);
          }

          playDataStream();
          toast({
            title: 'Node created',
            description: `New ${nodeType} node has been added to the graph.`,
          });
        },
        onError: () => {
          toast({
            title: 'Error',
            description: 'Failed to create node.',
            variant: 'destructive',
          });
        },
      });
    },
    [
      screenToFlowPosition,
      selectedTemplate,
      projectId,
      createNodeMutation,
      toast,
      setNodes,
    ]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // @kthulu:extend - Use semantic visualization for Kthulu projects
  if (useSemanticVisualization) {
    return (
      <SemanticGraphVisualization
        graphData={graphData}
        projectId={projectId}
        onNodeSelect={onNodeSelect}
        validationResults={validationResults}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600">Loading graph...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-red-600 mb-2">Failed to load graph data</p>
          <p className="text-gray-600 text-sm">
            Please try refreshing the page
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: 'black',
        position: 'relative',
        minHeight: '400px',
      }}
    >
      <ReactFlow
        style={{ width: '100%', height: '100%', minHeight: '400px' }}
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onDoubleClick={onDoubleClick}
        onNodeDragStop={onNodeDragStop}
        onNodesDelete={onNodesDelete}
        onEdgesDelete={onEdgesDelete}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        attributionPosition="bottom-left"
      >
        <Background color="#00ff41" gap={16} />
        <Controls />
      </ReactFlow>

      {/* SVG Definitions for Arrow Markers */}
      <svg
        style={{ position: 'absolute', top: 0, left: 0, width: 0, height: 0 }}
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#6B7280" />
          </marker>
        </defs>
      </svg>

      {/* Node Creation Form */}
      <NodeCreationForm
        isOpen={showNodeForm}
        onClose={() => setShowNodeForm(false)}
        onSubmit={handleNodeCreation}
        position={pendingNodePosition}
      />

      {/* Edge Edit Dialog */}
      <EdgeEditDialog
        edge={selectedEdge}
        isOpen={showEdgeEditDialog}
        onClose={() => {
          setShowEdgeEditDialog(false);
          setSelectedEdge(null);
        }}
        templateRules={selectedTemplate?.validationRules || []}
      />

      {/* Node Connection Editor */}
      <NodeConnectionEditor
        isOpen={showConnectionEditor}
        onClose={() => {
          setShowConnectionEditor(false);
          setPendingConnection(null);
        }}
        sourceNode={pendingConnection?.sourceNode || null}
        targetNode={pendingConnection?.targetNode || null}
        edge={pendingConnection?.edge || null}
      />
    </div>
  );
}

export function GraphEditor(props: GraphEditorProps) {
  return (
    <ReactFlowProvider>
      <GraphEditorInner {...props} />
    </ReactFlowProvider>
  );
}
