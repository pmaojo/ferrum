import { useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs";
import { GrafoEditor } from "./features/grafo/GrafoEditor";
import { VisualEditor } from "./features/visual/VisualEditor";
import { OutputPreview } from "./features/output/OutputPreview";
import { DocsViewer } from "./features/docs/DocsViewer";
import { PromptGenerator } from "./features/prompt/PromptGenerator";
import AiScaffoldPage from "./features/ai-scaffold/pages/AiScaffoldPage";
import { ProjectInit } from "./features/init/ProjectInit";
import { Toolchain } from "./features/toolchain/Toolchain";
import { PreviewFrame } from "./features/preview/PreviewFrame";

export default function App() {
  const [yaml, setYaml] = useState("module: demo\nnodes: []");

  return (
    <div className="p-4">
      <Tabs defaultValue="init">
        <TabsList>
          <TabsTrigger value="init">Init</TabsTrigger>
          <TabsTrigger value="grafo">grafo.yaml</TabsTrigger>
          <TabsTrigger value="ai">Prompt</TabsTrigger>
          <TabsTrigger value="visual">Visual</TabsTrigger>
          <TabsTrigger value="ai-scaffold">AI Scaffold</TabsTrigger>
          <TabsTrigger value="docs">Docs</TabsTrigger>
          <TabsTrigger value="output">Output</TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
          <TabsTrigger value="tools">Tools</TabsTrigger>
        </TabsList>
        <TabsContent value="init">
          <ProjectInit />
        </TabsContent>
        <TabsContent value="grafo">
          <GrafoEditor value={yaml} onChange={setYaml} />
        </TabsContent>
        <TabsContent value="ai">
          <PromptGenerator onResult={setYaml} />
        </TabsContent>
        <TabsContent value="visual">
          <VisualEditor yaml={yaml} onChange={setYaml} />
        </TabsContent>
        <TabsContent value="ai-scaffold">
          <AiScaffoldPage />
        </TabsContent>
        <TabsContent value="docs">
          <DocsViewer />
        </TabsContent>
        <TabsContent value="output">
          <OutputPreview />
        </TabsContent>
        <TabsContent value="preview">
          <PreviewFrame />
        </TabsContent>
        <TabsContent value="tools">
          <Toolchain yaml={yaml} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
