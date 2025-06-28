import ReactFlow, { Background, Edge, Node } from "react-flow-renderer";
import { useMemo } from "react";
import * as jsYaml from "js-yaml";

interface Props {
  /** Source `grafo.yaml` text */
  yaml: string;
}

/** Visual editor arranging nodes graphically */
export function VisualEditor({ yaml }: Props) {
  const { nodes, edges } = useMemo(() => {
    try {
      const doc = jsYaml.load(yaml) as any;
      const yamlNodes = Array.isArray(doc?.nodes) ? doc.nodes : [];

      const nodes: Node[] = yamlNodes.map((n: any, idx: number) => ({
        id: String(n.id),
        data: { label: String(n.id) },
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

  return (
    <div className="h-[80vh] border rounded">
      <ReactFlow nodes={nodes} edges={edges}>
        <Background />
      </ReactFlow>
    </div>
  );
}
