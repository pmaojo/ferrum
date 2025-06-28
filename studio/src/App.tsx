import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs";
import { GrafoEditor } from "./features/grafo/GrafoEditor";
import { VisualEditor } from "./features/visual/VisualEditor";
import { OutputPreview } from "./features/output/OutputPreview";
import { DocsViewer } from "./features/docs/DocsViewer";

export default function App() {
  return (
    <div className="p-4">
      <Tabs defaultValue="grafo">
        <TabsList>
          <TabsTrigger value="grafo">grafo.yaml</TabsTrigger>
          <TabsTrigger value="visual">Visual</TabsTrigger>
          <TabsTrigger value="docs">Docs</TabsTrigger>
          <TabsTrigger value="output">Output</TabsTrigger>
        </TabsList>
        <TabsContent value="grafo">
          <GrafoEditor />
        </TabsContent>
        <TabsContent value="visual">
          <VisualEditor />
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
