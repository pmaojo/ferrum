import { useState } from "react";

interface Props {
  /** Callback invoked with the generated YAML text */
  onResult?: (yaml: string) => void;
}

/** Form for generating a `grafo.yaml` file using the CLI. */

export function PromptGenerator({ onResult }: Props) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [model, setModel] = useState("openai");

  const endpoint =
    import.meta.env.VITE_AI_URL ?? "http://localhost:8001";

  const generate = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${endpoint}/generate-yaml`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, model }),
      });
      const data = await res.json();
      if (data.yaml && onResult) {
        onResult(data.yaml);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-2">
      <textarea
        className="w-full border rounded p-2"
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <select
        className="border rounded p-2"
        value={model}
        onChange={(e) => setModel(e.target.value)}
      >
        <option value="openai">OpenAI</option>
        <option value="local">Local</option>
        <option value="anthropic">Anthropic</option>
      </select>
      <button
        className="bg-blue-500 text-white px-4 py-2 rounded"
        onClick={generate}
        disabled={loading}
      >
        {loading ? "Generating..." : "Generate"}
      </button>
    </div>
  );
}
