import { useState } from "react";

export const useGenerateYaml = () => {
  const [data, setData] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = async (text: string) => {
    setLoading(true);
    try {
      const res = await fetch("/generate/yaml", {
        method: "POST",
        body: JSON.stringify({ text }),
      });
      const json = await res.json();
      setData(json.yaml);
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, generate };
};
