import type React from "react";
interface Props {
  features: Record<string, boolean>;
  onToggle: (k: string, v: boolean) => void;
}

/** Sidebar with draggable nodes and feature toggles */
export function FeatureSidebar({ features, onToggle }: Props) {
  const nodeTypes = ["usecase", "adapter", "port", "entity"];
  return (
    <div className="w-48 p-2 space-y-4 border-r text-sm">
      <div>
        <h3 className="font-bold mb-1">Nodes</h3>
        {nodeTypes.map((t) => (
          <div
            key={t}
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData("application/node-type", t);
            }}
            className="p-1 border mb-1 cursor-grab bg-gray-50"
          >
            {t}
          </div>
        ))}
      </div>
      <div>
        <h3 className="font-bold mb-1">Features</h3>
        {Object.keys(features).map((f) => (
          <label key={f} className="block">
            <input
              type="checkbox"
              className="mr-1"
              checked={features[f]}
              onChange={(e) => onToggle(f, e.target.checked)}
            />
            {f}
          </label>
        ))}
      </div>
    </div>
  );
}
