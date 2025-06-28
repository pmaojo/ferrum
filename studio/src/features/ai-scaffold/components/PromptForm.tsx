import { useState } from "react";
import { useGenerateYaml } from "../hooks/useGenerateYaml";

export function PromptForm() {
  const [prompt, setPrompt] = useState("");
  const { data, loading, generate } = useGenerateYaml();

  return (
    <div>
      <textarea
        className="w-full border p-2"
        rows={4}
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
      />
      <button
        className="bg-blue-500 text-white px-4 py-2 rounded mt-2"
        onClick={() => generate(prompt)}
        disabled={loading}
      >
        {loading ? "Generating..." : "Generate"}
      </button>
      {data && (
        <pre className="bg-gray-800 text-green-300 p-4 mt-4">{data}</pre>
      )}
    </div>
  );
}
