import { useEffect, useState } from "react";

interface Props {
  /** Natural language question */
  question: string;
}

/** Fetches a GraphRAG subgraph and shows it collapsible */
export function SubgraphView({ question }: Props) {
  const [graph, setGraph] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const fetchGraph = async () => {
      const endpoint = import.meta.env.VITE_AI_URL ?? "http://localhost:8001";
      const res = await fetch(`${endpoint}/graph-rag`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: question }),
      });
      const data = await res.json();
      setGraph(data.graph ?? "");
    };
    fetchGraph();
  }, [question]);

  return (
    <div className="my-2">
      <button
        className="bg-gray-700 text-white px-4 py-1 rounded"
        onClick={() => setOpen((o) => !o)}
      >
        {open ? "Hide" : "Show"} subgraph
      </button>
      {open && (
        <pre className="bg-gray-800 text-green-300 p-2 whitespace-pre-wrap mt-2">
          {graph}
        </pre>
      )}
    </div>
  );
}
