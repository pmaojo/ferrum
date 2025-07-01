import { useState } from "react";

interface Entry {
  user: string;
  backend: string;
  frontend: string;
  ux: string;
}

function parseReply(text: string) {
  const backend = text.split("Backend Expert:\n")[1]?.split("\n\n")[0] || "";
  const frontend = text.split("Frontend Expert:\n")[1]?.split("\n\n")[0] || "";
  const ux = text.split("UX Designer:\n")[1] || "";
  return { backend, frontend, ux };
}

export default function AiTeamPage() {
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(false);

  const send = async () => {
    if (!input) return;
    const question = input;
    setInput("");
    setLoading(true);
    try {
      const res = await fetch("/api/ai-team", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [{ role: "user", content: question }] }),
      });
      const json = await res.json();
      const parts = parseReply(json.message as string);
      setHistory((h) => [...h, { user: question, ...parts }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="space-y-4">
        {history.map((h, idx) => (
          <div key={idx} className="border p-2">
            <div className="font-bold mb-1">You:</div>
            <div className="mb-2">{h.user}</div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <div className="font-bold">Backend</div>
                <div>{h.backend}</div>
              </div>
              <div>
                <div className="font-bold">Frontend</div>
                <div>{h.frontend}</div>
              </div>
              <div>
                <div className="font-bold">UX</div>
                <div>{h.ux}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          className="border flex-1 p-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button
          onClick={send}
          disabled={loading}
          className="bg-blue-500 text-white px-4 py-2 rounded"
        >
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
