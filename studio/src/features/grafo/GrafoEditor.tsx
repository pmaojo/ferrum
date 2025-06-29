import Editor from "@monaco-editor/react";
import { useState } from "react";

interface Props {
  /** Current YAML value */
  value: string;
  /** Handler called when the YAML changes */
  onChange: (v: string) => void;
}

/** Editor for manually writing a `grafo.yaml` file. */

export function GrafoEditor({ value, onChange }: Props) {
  const [loading, setLoading] = useState(false);

  const compile = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:3001/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml: value }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "output.zip";
        a.click();
      } else {
        alert("Compile failed");
      }
    } finally {
      setLoading(false);
    }
  };

  const validate = async () => {
    setLoading(true);
    try {
      const endpoint = import.meta.env.VITE_AI_URL ?? "http://localhost:8001";
      const res = await fetch(`${endpoint}/validate/yaml`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml: value }),
      });
      const data = await res.json();
      if (data.valid) {
        alert("YAML válido");
      } else {
        alert("YAML inválido");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-2">
      <Editor
        height="70vh"
        defaultLanguage="yaml"
        value={value}
        onChange={(v) => onChange(v ?? "")}
      />
      <div className="space-x-2">
        <button
          className="bg-blue-500 text-white px-4 py-2 rounded"
          onClick={validate}
          disabled={loading}
        >
          {loading ? "Validating..." : "Validate"}
        </button>
        <button
          className="bg-green-500 text-white px-4 py-2 rounded"
          onClick={compile}
          disabled={loading}
        >
          {loading ? "Compiling..." : "Compile"}
        </button>
      </div>
    </div>
  );
}
