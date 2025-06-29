import ReactFlow, {
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
} from "react-flow-renderer";
import type { Edge, Node } from "react-flow-renderer";
import { useMemo, useRef, useState } from "react";
import * as jsYaml from "js-yaml";
import { FeatureSidebar } from "./FeatureSidebar";

interface Props {
  /** Source `grafo.yaml` text */
  yaml: string;
  /** Callback when YAML is updated */
  onChange: (y: string) => void;
}

/** Visual editor arranging nodes graphically */
export function VisualEditor({ yaml, onChange }: Props) {
  const initial = useMemo(() => {
    try {
      const doc = jsYaml.load(yaml) as any;
      const yamlNodes = Array.isArray(doc?.nodes) ? doc.nodes : [];
      const nodes: Node[] = yamlNodes.map((n: any, idx: number) => ({
        id: String(n.id),
        data: { label: String(n.id), type: n.type },
        position: { x: 0, y: idx * 80 },
      }));
      const edges: Edge[] = [];
      yamlNodes.forEach((n: any) => {
        if (Array.isArray(n.depends_on)) {
          n.depends_on.forEach((dep: string, i: number) => {
            edges.push({
              id: `${n.id}-${dep}-${i}`,
              source: String(n.id),
              target: String(dep),
            });
          });
        }
      });
      return { nodes, edges };
    } catch {
      return { nodes: [], edges: [] };
    }
  }, [yaml]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);
  const [features, setFeatures] = useState<Record<string, boolean>>({
    auth: false,
    jobs: false,
  });
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [rfInstance, setRfInstance] = useState<any>(null);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const type = e.dataTransfer.getData("application/node-type");
    if (type && rfInstance && wrapperRef.current) {
      const bounds = wrapperRef.current.getBoundingClientRect();
      const position = rfInstance.project({
        x: e.clientX - bounds.left,
        y: e.clientY - bounds.top,
      });
      const id = `${type}-${nodes.length + 1}`;
      setNodes((nds) => nds.concat({ id, data: { label: id, type }, position }));
    }
  };

  const onSave = async () => {
    const yamlNodes = nodes.map((n) => {
      const deps = edges
        .filter((e) => e.source === n.id)
        .map((e) => e.target);
      const obj: any = { id: n.id, type: n.data.type };
      if (deps.length) obj.depends_on = deps;
      return obj;
    });
    const yamlObj: any = { module: "demo", nodes: yamlNodes };
    const feats = Object.keys(features).filter((k) => features[k]);
    if (feats.length) yamlObj.app = { features: feats };
    const newYaml = jsYaml.dump(yamlObj);
    onChange(newYaml);
    await fetch("http://localhost:3001/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ yaml: newYaml }),
    });
  };

  return (
    <div className="flex h-[80vh] border rounded">
      <FeatureSidebar
        features={features}
        onToggle={(k, v) => setFeatures((f) => ({ ...f, [k]: v }))}
      />
      <div
        className="flex-1"
        ref={wrapperRef}
        onDrop={onDrop}
        onDragOver={(e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = "move";
        }}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={(c) => setEdges((eds) => addEdge(c, eds))}
          onInit={setRfInstance}
        >
          <Background />
        </ReactFlow>
        <button
          className="absolute bottom-2 right-2 bg-blue-600 text-white px-3 py-1 rounded"
          onClick={onSave}
        >
          Save &amp; Compile
        </button>
      </div>
    </div>
  );
}
