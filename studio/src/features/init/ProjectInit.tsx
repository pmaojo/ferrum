import { useState } from "react";

/** Form to initialize a new Ferrum project */
export function ProjectInit() {
  const [name, setName] = useState("");
  const [withGraph, setWithGraph] = useState(false);
  const [withAi, setWithAi] = useState(false);
  const [withDb, setWithDb] = useState(false);
  const [loading, setLoading] = useState(false);

  const initProject = async () => {
    if (!name) return;
    setLoading(true);
    try {
      const res = await fetch("http://localhost:3001/init", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          with_graph: withGraph,
          with_ai: withAi,
          with_db: withDb,
        }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${name}.zip`;
        a.click();
      } else {
        alert("Init failed");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-2 max-w-md">
      <input
        className="border rounded p-2 w-full"
        placeholder="project name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <label className="block">
        <input
          type="checkbox"
          checked={withGraph}
          onChange={(e) => setWithGraph(e.target.checked)}
          className="mr-2"
        />
        With graph database
      </label>
      <label className="block">
        <input
          type="checkbox"
          checked={withDb}
          onChange={(e) => setWithDb(e.target.checked)}
          className="mr-2"
        />
        With PostgreSQL
      </label>
      <label className="block">
        <input
          type="checkbox"
          checked={withAi}
          onChange={(e) => setWithAi(e.target.checked)}
          className="mr-2"
        />
        With AI service
      </label>
      <button
        className="bg-purple-500 text-white px-4 py-2 rounded"
        onClick={initProject}
        disabled={loading}
      >
        {loading ? "Initializing..." : "Initialize"}
      </button>
    </div>
  );
}

