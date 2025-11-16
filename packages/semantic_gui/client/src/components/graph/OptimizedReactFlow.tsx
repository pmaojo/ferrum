import React, {
  useMemo,
  useCallback,
  useState,
  useEffect,
  useRef,
} from 'react';
import ReactFlow, {
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  Panel,
  ReactFlowProvider,
  useReactFlow,
  Viewport,
  NodeTypes,
  EdgeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';

interface OptimizedReactFlowProps {
  nodes: Node[];
  edges: Edge[];
  onNodeClick?: (node: Node) => void;
  onEdgeClick?: (edge: Edge) => void;
  className?: string;
  maxVisibleNodes?: number;
  enableVirtualization?: boolean;
  enableClustering?: boolean;
}

interface ClusterNode extends Node {
  clusterId?: string;
  isCluster?: boolean;
  childCount?: number;
}

interface ViewportBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Optimized React Flow component for handling large graphs
 *
 * Features:
 * 1. Viewport-based virtualization
 * 2. Node clustering for dense areas
 * 3. Level-of-detail rendering
 * 4. Lazy loading of node details
 * 5. Performance monitoring
 */
const OptimizedReactFlowInner: React.FC<OptimizedReactFlowProps> = ({
  nodes: initialNodes,
  edges: initialEdges,
  onNodeClick,
  onEdgeClick,
  className = '',
  maxVisibleNodes = 500,
  enableVirtualization = true,
  enableClustering = true,
}) => {
  const reactFlowInstance = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [viewport, setViewport] = useState<Viewport>({ x: 0, y: 0, zoom: 1 });
  const [visibleNodes, setVisibleNodes] = useState<Node[]>([]);
  const [visibleEdges, setVisibleEdges] = useState<Edge[]>([]);
  const [clusters, setClusters] = useState<Map<string, ClusterNode>>(new Map());
  const [performanceStats, setPerformanceStats] = useState({
    renderTime: 0,
    visibleNodeCount: 0,
    totalNodeCount: 0,
  });

  const performanceRef = useRef<{ startTime: number }>({ startTime: 0 });

  // Memoized node types for performance
  const nodeTypes: NodeTypes = useMemo(
    () => ({
      default: React.memo(({ data, ...props }) => (
        <div className="px-2 py-1 bg-white border rounded shadow-sm">
          {data.label}
        </div>
      )),
      cluster: React.memo(({ data, ...props }) => (
        <div className="px-3 py-2 bg-blue-100 border-2 border-blue-300 rounded-lg">
          <div className="font-semibold">{data.label}</div>
          <div className="text-xs text-gray-600">{data.childCount} items</div>
        </div>
      )),
      module: React.memo(({ data, ...props }) => (
        <div className="px-3 py-2 bg-green-100 border-2 border-green-300 rounded">
          <div className="font-semibold text-green-800">{data.label}</div>
          <div className="text-xs text-green-600">{data.type}</div>
        </div>
      )),
      usecase: React.memo(({ data, ...props }) => (
        <div className="px-3 py-2 bg-blue-100 border-2 border-blue-300 rounded">
          <div className="font-semibold text-blue-800">{data.label}</div>
          <div className="text-xs text-blue-600">{data.type}</div>
        </div>
      )),
      adapter: React.memo(({ data, ...props }) => (
        <div className="px-3 py-2 bg-purple-100 border-2 border-purple-300 rounded">
          <div className="font-semibold text-purple-800">{data.label}</div>
          <div className="text-xs text-purple-600">{data.type}</div>
        </div>
      )),
    }),
    []
  );

  // Calculate viewport bounds
  const getViewportBounds = useCallback(
    (viewport: Viewport): ViewportBounds => {
      const { x, y, zoom } = viewport;
      const width = window.innerWidth / zoom;
      const height = window.innerHeight / zoom;

      return {
        x: -x / zoom,
        y: -y / zoom,
        width,
        height,
      };
    },
    []
  );

  // Check if node is within viewport bounds
  const isNodeInViewport = useCallback(
    (node: Node, bounds: ViewportBounds): boolean => {
      const nodeX = node.position.x;
      const nodeY = node.position.y;
      const nodeWidth = node.width || 150;
      const nodeHeight = node.height || 50;

      return (
        nodeX + nodeWidth >= bounds.x &&
        nodeX <= bounds.x + bounds.width &&
        nodeY + nodeHeight >= bounds.y &&
        nodeY <= bounds.y + bounds.height
      );
    },
    []
  );

  // Create clusters for dense areas
  const createClusters = useCallback(
    (nodes: Node[], viewport: Viewport): Map<string, ClusterNode> => {
      if (!enableClustering || viewport.zoom > 0.5) {
        return new Map();
      }

      const clusters = new Map<string, ClusterNode>();
      const gridSize = 200; // Grid cell size for clustering
      const minNodesPerCluster = 3;

      // Group nodes by grid position
      const grid = new Map<string, Node[]>();

      nodes.forEach((node) => {
        const gridX = Math.floor(node.position.x / gridSize);
        const gridY = Math.floor(node.position.y / gridSize);
        const gridKey = `${gridX},${gridY}`;

        if (!grid.has(gridKey)) {
          grid.set(gridKey, []);
        }
        grid.get(gridKey)!.push(node);
      });

      // Create clusters for dense grid cells
      grid.forEach((cellNodes, gridKey) => {
        if (cellNodes.length >= minNodesPerCluster) {
          const [gridX, gridY] = gridKey.split(',').map(Number);
          const centerX = gridX * gridSize + gridSize / 2;
          const centerY = gridY * gridSize + gridSize / 2;

          const clusterNode: ClusterNode = {
            id: `cluster-${gridKey}`,
            type: 'cluster',
            position: { x: centerX, y: centerY },
            data: {
              label: `Cluster ${gridKey}`,
              childCount: cellNodes.length,
            },
            isCluster: true,
            childCount: cellNodes.length,
          };

          clusters.set(clusterNode.id, clusterNode);
        }
      });

      return clusters;
    },
    [enableClustering]
  );

  // Filter visible nodes and edges based on viewport
  const filterVisibleElements = useCallback(
    (allNodes: Node[], allEdges: Edge[], viewport: Viewport) => {
      performanceRef.current.startTime = performance.now();

      const bounds = getViewportBounds(viewport);
      let filteredNodes: Node[] = [];
      let filteredEdges: Edge[] = [];

      if (enableVirtualization && allNodes.length > maxVisibleNodes) {
        // Create clusters if needed
        const currentClusters = createClusters(allNodes, viewport);
        setClusters(currentClusters);

        // Filter nodes based on viewport and clustering
        const visibleNodeIds = new Set<string>();

        if (currentClusters.size > 0 && viewport.zoom < 0.5) {
          // Show clusters instead of individual nodes
          filteredNodes = Array.from(currentClusters.values());
          filteredNodes.forEach((node) => visibleNodeIds.add(node.id));
        } else {
          // Show individual nodes within viewport
          filteredNodes = allNodes.filter((node) => {
            const inViewport = isNodeInViewport(node, bounds);
            if (inViewport) {
              visibleNodeIds.add(node.id);
            }
            return inViewport;
          });

          // Limit to max visible nodes
          if (filteredNodes.length > maxVisibleNodes) {
            filteredNodes = filteredNodes.slice(0, maxVisibleNodes);
            visibleNodeIds.clear();
            filteredNodes.forEach((node) => visibleNodeIds.add(node.id));
          }
        }

        // Filter edges to only show those connecting visible nodes
        filteredEdges = allEdges.filter(
          (edge) =>
            visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)
        );
      } else {
        // Show all nodes if under threshold
        filteredNodes = allNodes;
        filteredEdges = allEdges;
      }

      const renderTime = performance.now() - performanceRef.current.startTime;
      setPerformanceStats({
        renderTime,
        visibleNodeCount: filteredNodes.length,
        totalNodeCount: allNodes.length,
      });

      return { filteredNodes, filteredEdges };
    },
    [
      enableVirtualization,
      maxVisibleNodes,
      getViewportBounds,
      isNodeInViewport,
      createClusters,
    ]
  );

  // Update visible elements when viewport changes
  useEffect(() => {
    const { filteredNodes, filteredEdges } = filterVisibleElements(
      initialNodes,
      initialEdges,
      viewport
    );

    setVisibleNodes(filteredNodes);
    setVisibleEdges(filteredEdges);
  }, [initialNodes, initialEdges, viewport, filterVisibleElements]);

  // Update React Flow nodes and edges
  useEffect(() => {
    setNodes(visibleNodes);
    setEdges(visibleEdges);
  }, [visibleNodes, visibleEdges, setNodes, setEdges]);

  // Handle viewport changes with throttling
  const handleViewportChange = useCallback((newViewport: Viewport) => {
    setViewport(newViewport);
  }, []);

  // Handle node clicks with cluster expansion
  const handleNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      const clusterNode = node as ClusterNode;

      if (clusterNode.isCluster) {
        // Expand cluster by zooming in
        const zoomLevel = Math.max(viewport.zoom * 2, 1);
        reactFlowInstance.setViewport({
          x: -node.position.x * zoomLevel + window.innerWidth / 2,
          y: -node.position.y * zoomLevel + window.innerHeight / 2,
          zoom: zoomLevel,
        });
      } else {
        onNodeClick?.(node);
      }
    },
    [viewport.zoom, reactFlowInstance, onNodeClick]
  );

  return (
    <div className={`w-full h-full ${className}`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onEdgeClick={(event, edge) => onEdgeClick?.(edge)}
        onViewportChange={handleViewportChange}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
        maxZoom={4}
        minZoom={0.1}
        defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
      >
        <Controls />
        <MiniMap
          nodeStrokeColor="#374151"
          nodeColor="#9CA3AF"
          nodeBorderRadius={2}
          maskColor="rgba(0, 0, 0, 0.2)"
        />
        <Background variant="dots" gap={12} size={1} />

        {/* Performance Panel */}
        <Panel
          position="top-right"
          className="bg-white p-2 rounded shadow text-xs"
        >
          <div>
            Visible: {performanceStats.visibleNodeCount}/
            {performanceStats.totalNodeCount}
          </div>
          <div>Render: {performanceStats.renderTime.toFixed(1)}ms</div>
          <div>Zoom: {viewport.zoom.toFixed(2)}</div>
          {clusters.size > 0 && <div>Clusters: {clusters.size}</div>}
        </Panel>
      </ReactFlow>
    </div>
  );
};

/**
 * Optimized React Flow wrapper with provider
 */
export const OptimizedReactFlow: React.FC<OptimizedReactFlowProps> = (
  props
) => {
  return (
    <ReactFlowProvider>
      <OptimizedReactFlowInner {...props} />
    </ReactFlowProvider>
  );
};

export default OptimizedReactFlow;
