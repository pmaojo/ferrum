import ReactFlow from "react-flow-renderer";

/** Visual editor arranging nodes graphically */
export function VisualEditor() {
  return (
    <div className="h-[80vh] border rounded">
      <ReactFlow />
    </div>
  );
}
