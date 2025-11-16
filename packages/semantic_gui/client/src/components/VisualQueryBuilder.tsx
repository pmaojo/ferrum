import { useCallback, useEffect, useRef, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  Connection,
  Edge,
  Node,
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Button } from '@/components/ui/button';

interface VisualQueryBuilderProps {
  onQueryChange: (query: string) => void;
}

function generateSPARQL(nodes: Node[], edges: Edge[]): string {
  if (nodes.length === 0) return '';
  const selectVars = nodes.map((n) => `?${n.id}`);
  const triples: string[] = [];
  nodes.forEach((n) => {
    triples.push(`?${n.id} a ${n.data.label} .`);
  });
  edges.forEach((e) => {
    const prop = (e.data as any)?.property || e.label || '';
    if (prop) {
      triples.push(`?${e.source} ${prop} ?${e.target} .`);
    }
  });
  return `SELECT ${selectVars.join(' ')} WHERE {\n  ${triples.join('\n  ')}\n}`;
}

function VisualQueryBuilderInner({ onQueryChange }: VisualQueryBuilderProps) {
  const classOptions = [
    'kth:Module',
    'kth:UseCase',
    'kth:Port',
    'kth:Adapter',
    'kth:DomainEntity',
    'kth:DomainEvent',
  ];
  const propertyOptions = [
    'kth:definesUseCase',
    'kth:hasPort',
    'kth:implementsPort',
    'kth:usesPort',
    'kth:dependsOnModule',
    'kth:emitsEvent',
  ];
  const [selectedProperty, setSelectedProperty] = useState(propertyOptions[0]);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);
  const id = useRef(0);
  const getId = useCallback(() => `n${id.current++}`, []);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      if (!reactFlowInstance) return;
      const reactBounds = reactFlowWrapper.current?.getBoundingClientRect();
      const label = event.dataTransfer.getData('application/reactflow');
      const position = reactFlowInstance.project({
        x: event.clientX - (reactBounds?.left || 0),
        y: event.clientY - (reactBounds?.top || 0),
      });
      const newNode: Node = {
        id: getId(),
        position,
        data: { label },
        type: 'default',
      };
      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes, getId]
  );

  const onConnect = useCallback(
    (connection: Edge | Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            label: selectedProperty,
            data: { property: selectedProperty },
          },
          eds
        )
      );
    },
    [selectedProperty, setEdges]
  );

  useEffect(() => {
    onQueryChange(generateSPARQL(nodes, edges));
  }, [nodes, edges, onQueryChange]);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {classOptions.map((cls) => (
          <div
            key={cls}
            draggable
            onDragStart={(e) =>
              e.dataTransfer.setData('application/reactflow', cls)
            }
            className="px-2 py-1 bg-secondary rounded text-xs cursor-grab"
          >
            {cls}
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        {propertyOptions.map((prop) => (
          <Button
            key={prop}
            size="sm"
            variant={selectedProperty === prop ? 'default' : 'outline'}
            onClick={() => setSelectedProperty(prop)}
          >
            {prop}
          </Button>
        ))}
      </div>
      <div className="h-64 border rounded" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={setReactFlowInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          fitView
        >
          <Controls />
          <Background />
        </ReactFlow>
      </div>
    </div>
  );
}

export function VisualQueryBuilder(props: VisualQueryBuilderProps) {
  return (
    <ReactFlowProvider>
      <VisualQueryBuilderInner {...props} />
    </ReactFlowProvider>
  );
}
