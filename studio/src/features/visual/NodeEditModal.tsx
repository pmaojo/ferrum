import { useState } from "react";
import type { Node, Edge } from "react-flow-renderer";

interface Field {
  name: string;
  type: string;
}

interface Props {
  node: Node;
  allNodes: Node[];
  edges: Edge[];
  onSave: (node: Node, deps: string[]) => void;
  onClose: () => void;
}

export function NodeEditModal({ node, allNodes, edges, onSave, onClose }: Props) {
  const [id, setId] = useState(node.id);
  const [type, setType] = useState(node.data.type || "usecase");
  const [description, setDescription] = useState(node.data.description || "");
  const [impl, setImpl] = useState(node.data.implements || "");
  const [output, setOutput] = useState(node.data.output || "");
  const [inputs, setInputs] = useState<Field[]>(node.data.input || []);

  const currentDeps = edges
    .filter((e) => e.source === node.id)
    .map((e) => e.target);
  const [deps, setDeps] = useState<string[]>(currentDeps);

  const toggleDep = (dep: string, checked: boolean) => {
    setDeps((d) =>
      checked ? [...d, dep] : d.filter((x) => x !== dep)
    );
  };

  const updateInput = (idx: number, key: keyof Field, value: string) => {
    setInputs((ins) => {
      const copy = [...ins];
      copy[idx] = { ...copy[idx], [key]: value } as Field;
      return copy;
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
      <div className="bg-white p-4 rounded w-80 space-y-2">
        <h3 className="font-bold text-lg">Edit Node</h3>
        <label className="block">
          <span className="block text-sm">ID</span>
          <input
            className="border p-1 w-full"
            value={id}
            onChange={(e) => setId(e.target.value)}
          />
        </label>
        <label className="block">
          <span className="block text-sm">Type</span>
          <select
            className="border p-1 w-full"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            {[
              "usecase",
              "adapter",
              "port",
              "entity",
              "component",
              "hook",
              "schema",
            ].map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="block text-sm">Description</span>
          <input
            className="border p-1 w-full"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <div className="space-y-1">
          <span className="block text-sm">Inputs</span>
          {inputs.map((inp, idx) => (
            <div key={idx} className="flex space-x-1">
              <input
                className="border p-1 flex-1"
                placeholder="name"
                value={inp.name}
                onChange={(e) => updateInput(idx, "name", e.target.value)}
              />
              <input
                className="border p-1 flex-1"
                placeholder="type"
                value={inp.type}
                onChange={(e) => updateInput(idx, "type", e.target.value)}
              />
              <button
                className="text-red-500"
                onClick={() =>
                  setInputs((ins) => ins.filter((_, i) => i !== idx))
                }
              >
                x
              </button>
            </div>
          ))}
          <button
            className="text-sm text-blue-600"
            onClick={() => setInputs((ins) => [...ins, { name: "", type: "" }])}
          >
            + add input
          </button>
        </div>
        <label className="block">
          <span className="block text-sm">Output</span>
          <input
            className="border p-1 w-full"
            value={output}
            onChange={(e) => setOutput(e.target.value)}
          />
        </label>
        <label className="block">
          <span className="block text-sm">Implements</span>
          <input
            className="border p-1 w-full"
            value={impl}
            onChange={(e) => setImpl(e.target.value)}
          />
        </label>
        <div>
          <span className="block text-sm">Depends on</span>
          {allNodes
            .filter((n) => n.id !== node.id)
            .map((n) => (
              <label key={n.id} className="block">
                <input
                  type="checkbox"
                  className="mr-1"
                  checked={deps.includes(n.id)}
                  onChange={(e) => toggleDep(n.id, e.target.checked)}
                />
                {n.id}
              </label>
            ))}
        </div>
        <div className="space-x-2 text-right">
          <button
            className="px-2 py-1 bg-gray-200 rounded"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="px-2 py-1 bg-blue-600 text-white rounded"
            onClick={() =>
              onSave(
                {
                  ...node,
                  id,
                  data: {
                    ...node.data,
                    label: id,
                    type,
                    description,
                    implements: impl,
                    input: inputs,
                    output,
                  },
                },
                deps
              )
            }
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
