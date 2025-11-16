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
import { NodeCreationForm } from '../NodeCreationForm';
import { EdgeEditDialog } from '../EdgeEditDialog';
import { NodeConnectionEditor } from '../NodeConnectionEditor';
import {
  useGraphData,
  useCreateNode,
  useUpdateNode,
  useCreateEdge,
  useDeleteNode,
  useDeleteEdge,
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

interface GraphCanvasProps {
  projectId: string;
  onNodeSelect: (node: Node<GraphNodeData> | null) => void;
}

function GraphCanvasInner({ projectId, onNodeSelect }: GraphCanvasProps) {
  const { template: selectedTemplate } = useTemplate();
  const { data: graphData, isLoading, error } = useGraphData(projectId);
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

  // Convert backend data to ReactFlow format
  useEffect(() => {
    console.log('🔄 GraphCanvas: Processing graphData:', graphData);

    if (graphData && graphData.nodes && Array.isArray(graphData.nodes)) {
      console.log('📊 GraphCanvas: Found', graphData.nodes.length, 'nodes');

      const flowNodes: Node<GraphNodeData>[] = graphData.nodes.map(
        (node: GraphNodeType, index: number) => {
          console.log(`🔧 Processing node ${index}:`, node);
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
            },
          };
        }
      );

      const flowEdges: Edge[] = (graphData.edges || []).map((edge: any) => ({
        id: edge.id,
        source: edge.sourceNodeId,
        target: edge.targetNodeId,
        type: 'custom',
        label: edge.type || 'connection',
        animated: true,
        style: { stroke: '#00FF41', strokeWidth: 2 },
        data: {
          type: edge.type,
          parameters: edge.parameters || [],
          methodCalls: edge.methodCalls || [],
          metadata: edge.metadata,
        },
      }));

      console.log(
        '✨ GraphCanvas: Setting',
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
      console.log('❌ GraphCanvas: No valid nodes found in graphData');
    }
  }, [graphData, setNodes, setEdges, fitView]);

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
      event.stopPropagation(); // Prevent pane click from firing
      console.log('🎯 Node clicked:', node.data.name, node.data);
      playQuantumResonance();
      setSelectedNode(node);
      onNodeSelect(node);
    },
    [onNodeSelect, playQuantumResonance]
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

export function GraphCanvas(props: GraphCanvasProps) {
  return (
    <ReactFlowProvider>
      <GraphCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
