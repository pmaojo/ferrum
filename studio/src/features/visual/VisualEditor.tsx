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
import { NodeEditModal } from "./NodeEditModal";

const typeColors: Record<string, string> = {
  usecase: "#fef9c3",
  adapter: "#c7d2fe",
  port: "#a5b4fc",
  entity: "#bbf7d0",
  component: "#bae6fd",
  hook: "#fdba74",
  schema: "#f3e8ff",
  form: "#ddd6fe",
  validation: "#fde68a",
  resource: "#fecaca",
  policy: "#fed7aa",
  upload: "#fca5a5",
};

function colorFor(type: string): string {
  return typeColors[type] || "#e5e7eb";
}

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
        data: {
          label: String(n.id),
          type: n.type,
          description: n.description ?? "",
          implements: n.implements ?? "",
          input: n.input ?? [],
          output: n.output ?? "",
        },
        position: { x: 0, y: idx * 80 },
        style: { background: colorFor(n.type) },
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
  const [bottleneck, setBottleneck] = useState(3);
  const [analysis, setAnalysis] = useState<any | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [rfInstance, setRfInstance] = useState<any>(null);
  const [editing, setEditing] = useState<Node | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (!analysis) return;
    const cycleSet = new Set<string>(
      analysis.cycles.flat().map((id: string) => id.split(".").pop())
    );
    const bottleneckSet = new Set<string>(
      analysis.bottlenecks.map((id: string) => id.split(".").pop())
    );
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        style: {
          background: colorFor(n.data.type),
          border: bottleneckSet.has(n.id)
            ? "2px solid red"
            : cycleSet.has(n.id)
            ? "2px dashed orange"
            : "1px solid #777",
        },
      }))
    );
  }, [analysis, setNodes]);

  const buildYaml = () => {
    const yamlNodes = nodes.map((n) => {
      const deps = edges.filter((e) => e.source === n.id).map((e) => e.target);
      const obj: any = { id: n.id, type: n.data.type };
      if (n.data.description) obj.description = n.data.description;
      if (n.data.input && n.data.input.length) obj.input = n.data.input;
      if (n.data.output) obj.output = n.data.output;
      if (deps.length) obj.depends_on = deps;
      if (n.data.implements) obj.implements = n.data.implements;
      return obj;
    });
    const yamlObj: any = { module: "demo", nodes: yamlNodes };
    const feats = Object.keys(features).filter((k) => features[k]);
    if (feats.length) yamlObj.app = { features: feats };
    return jsYaml.dump(yamlObj);
  };

  const handleExport = () => {
    const data = buildYaml();
    const blob = new Blob([data], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "grafo.yaml";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      if (text) {
        onChange(text);
      }
    };
    reader.readAsText(file);
  };

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
      setNodes((nds) =>
        nds.concat({
          id,
          data: {
            label: id,
            type,
            description: "",
            implements: "",
            input: [],
            output: "",
          },
          position,
          style: { background: colorFor(type) },
        }),
      );
    }
  };

  const onSave = async () => {
    const newYaml = buildYaml();
    onChange(newYaml);
    const res = await fetch("http://localhost:3001/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ yaml: newYaml, bottleneck }),
    });
    const data = await res.json();
    if (data.analysis) {
      setAnalysis(data.analysis);
      const cycleMsg =
        data.analysis.cycles && data.analysis.cycles.length
          ? `Cycles: ${data.analysis.cycles
              .map((c: string[]) => c.join(" -> "))
              .join("; ")}`
          : "";
      const bottleneckMsg =
        data.analysis.bottlenecks && data.analysis.bottlenecks.length
          ? `Bottlenecks: ${data.analysis.bottlenecks
              .map((b: string) => b.split(".").pop())
              .join(", ")}`
          : "";
      if (cycleMsg || bottleneckMsg) {
        alert(`${cycleMsg}\n${bottleneckMsg}`.trim());
      }
    }
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
          onNodeDoubleClick={(_, n) => setEditing(n)}
        >
          <Background />
        </ReactFlow>
        <input
          type="file"
          accept=".yaml,.yml"
          ref={fileInputRef}
          className="hidden"
          onChange={handleImport}
        />
        <div className="absolute bottom-2 right-2 space-x-2">
          <button
            className="bg-gray-200 px-3 py-1 rounded"
            onClick={() => fileInputRef.current?.click()}
          >
            Import
          </button>
          <button
            className="bg-gray-200 px-3 py-1 rounded"
            onClick={handleExport}
          >
            Export
          </button>
          <label className="text-xs">
            Bottleneck
            <input
              type="number"
              className="border ml-1 w-14 px-1"
              value={bottleneck}
              onChange={(e) => setBottleneck(parseInt(e.target.value))}
            />
          </label>
          <button
            className="bg-blue-600 text-white px-3 py-1 rounded"
            onClick={onSave}
          >
            Save &amp; Compile
          </button>
        </div>
        {editing && (
          <NodeEditModal
            node={editing}
            allNodes={nodes}
            edges={edges}
            onClose={() => setEditing(null)}
            onSave={(updated, deps) => {
              const oldId = editing.id;
              setNodes((nds) =>
                nds.map((n) =>
                  n.id === oldId
                    ? { ...updated, style: { background: colorFor(updated.data.type) } }
                    : { ...n, id: n.id },
                ),
              );
              setEdges((eds) => {
                let others = eds
                  .map((e) => ({
                    ...e,
                    source: e.source === oldId ? updated.id : e.source,
                    target: e.target === oldId ? updated.id : e.target,
                  }))
                  .filter((e) => e.source !== oldId);
                const newEdges = deps.map((d, i) => ({
                  id: `${updated.id}-${d}-${i}`,
                  source: updated.id,
                  target: d,
                }));
                return [...others, ...newEdges];
              });
              setEditing(null);
            }}
          />
        )}
      </div>
    </div>
  );
}
