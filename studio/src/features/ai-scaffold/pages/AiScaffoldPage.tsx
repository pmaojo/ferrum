import { useGenerateYaml } from "../hooks/useGenerateYaml";
import { useState } from "react";

export default function AiScaffoldPage() {
  const { data, loading, generate } = useGenerateYaml();
  const [prompt, setPrompt] = useState("");

  return (
    <div>
      <h1 className="text-xl font-bold mb-2">🧠 Generador de Arquitectura AI</h1>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        className="w-full border p-2"
      />
      <button
        onClick={() => generate(prompt)}
        disabled={loading}
        className="bg-blue-500 text-white px-4 py-2 rounded mt-2"
      >
        Generar
      </button>
      {loading && <p>Cargando...</p>}
      {data && (
        <pre className="bg-gray-800 text-green-300 p-4 whitespace-pre-wrap mt-4">
          {data}
        </pre>
      )}
    </div>
  );
}
