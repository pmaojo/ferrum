import Editor from "@monaco-editor/react";
import { useState } from "react";

export function GrafoEditor() {
  const [value, setValue] = useState("module: demo\nnodes: []");
  return (
    <Editor
      height="80vh"
      defaultLanguage="yaml"
      value={value}
      onChange={(v) => setValue(v ?? "")}
    />
  );
}
