import { useState } from "react";

interface Props {
  yaml: string;
}

export function Toolchain({ yaml }: Props) {
  const [withGraph, setWithGraph] = useState(false);
  const [withAi, setWithAi] = useState(false);
  const [uri, setUri] = useState("bolt://localhost:7687");
  const [user, setUser] = useState("neo4j");
  const [password, setPassword] = useState("test");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);

  const startDev = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:3001/dev", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ with_graph: withGraph, with_ai: withAi }),
      });
      const data = await res.json();
      setOutput(data.output ?? "");
    } finally {
      setLoading(false);
    }
  };

  const syncGraph = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:3001/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml, uri, user, password }),
      });
      const data = await res.json();
      setOutput(data.output ?? "");
    } finally {
      setLoading(false);
    }
  };

  const migrate = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:3001/migrate", {
        method: "POST",
      });
      const data = await res.json();
      setOutput(data.output ?? "");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-bold mb-1">Development Environment</h3>
        <label className="block">
          <input type="checkbox" className="mr-2" checked={withGraph} onChange={(e)=>setWithGraph(e.target.checked)} />
          With graph database
        </label>
        <label className="block mb-2">
          <input type="checkbox" className="mr-2" checked={withAi} onChange={(e)=>setWithAi(e.target.checked)} />
          With AI service
        </label>
        <button className="bg-purple-500 text-white px-4 py-2 rounded" onClick={startDev} disabled={loading}>
          {loading ? "Starting..." : "Start"}
        </button>
      </div>
      <div>
        <h3 className="font-bold mb-1">Sync to Neo4j</h3>
        <input className="border p-1 mr-2" value={uri} onChange={(e)=>setUri(e.target.value)} />
        <input className="border p-1 mr-2" value={user} onChange={(e)=>setUser(e.target.value)} />
        <input className="border p-1 mr-2" type="password" value={password} onChange={(e)=>setPassword(e.target.value)} />
        <button className="bg-green-600 text-white px-4 py-2 rounded" onClick={syncGraph} disabled={loading}>
          {loading ? "Syncing..." : "Sync"}
        </button>
      </div>
      <div>
        <h3 className="font-bold mb-1">Database Migrations</h3>
        <button className="bg-blue-600 text-white px-4 py-2 rounded" onClick={migrate} disabled={loading}>
          {loading ? "Running..." : "Migrate"}
        </button>
      </div>
      {output && <pre className="bg-gray-800 text-green-300 p-2 whitespace-pre-wrap">{output}</pre>}
    </div>
  );
}
