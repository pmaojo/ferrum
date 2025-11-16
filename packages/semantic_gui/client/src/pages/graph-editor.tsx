import OnboardingTGAInterface from '@/components/OnboardingTGAInterface';
import ConnectorManager from '@/components/ConnectorManager';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function GraphEditor() {
  return (
    <Tabs defaultValue="graph" className="w-full h-full">
      <TabsList className="mb-4">
        <TabsTrigger value="graph">Graph</TabsTrigger>
        <TabsTrigger value="connector">Connector</TabsTrigger>
      </TabsList>
      <TabsContent value="graph" className="h-full">
        <OnboardingTGAInterface />
      </TabsContent>
      <TabsContent value="connector" className="h-full overflow-auto">
        <ConnectorManager />
      </TabsContent>
    </Tabs>
  );
}
