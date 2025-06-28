import { useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs";
import { GrafoEditor } from "./features/grafo/GrafoEditor";
import { VisualEditor } from "./features/visual/VisualEditor";
import { OutputPreview } from "./features/output/OutputPreview";
import { DocsViewer } from "./features/docs/DocsViewer";
import { PromptGenerator } from "./features/prompt/PromptGenerator";
import AiScaffoldPage from "./features/ai-scaffold/pages/AiScaffoldPage";
import { ProjectInit } from "./features/init/ProjectInit";

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
          <VisualEditor yaml={yaml} />
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
      </Tabs>
    </div>
  );
}
