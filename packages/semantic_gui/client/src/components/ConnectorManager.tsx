import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import useConnector from '@/hooks/useConnector';

export function ConnectorManager() {
  const [projectId, setProjectId] = useState('');
  const [projectPath, setProjectPath] = useState('');
  const [templateId, setTemplateId] = useState('');
  const [command, setCommand] = useState('');
  const [args, setArgs] = useState('');
  const [graphOutput, setGraphOutput] = useState<any | null>(null);
  const [validationResult, setValidationResult] = useState<any | null>(null);

  const { toast } = useToast();
  const connector = useConnector(projectId);

  const handleInit = async () => {
    try {
      await connector.initConnector(projectPath, templateId);
      toast({ title: 'Connector initialized' });
    } catch (e: any) {
      toast({
        title: 'Initialization failed',
        description: e.message,
        variant: 'destructive',
      });
    }
  };

  const handleExecute = async () => {
    try {
      const result = await connector.executeCommand(
        command,
        args ? args.split(' ') : []
      );
      toast({ title: 'Command executed' });
      console.log(result.output || result);
    } catch (e: any) {
      toast({
        title: 'Command failed',
        description: e.message,
        variant: 'destructive',
      });
    }
  };

  const handleGraph = async () => {
    try {
      const result = await connector.generateGraph();
      setGraphOutput(result.scgGraph || result.graphData);
    } catch (e: any) {
      toast({
        title: 'Graph generation failed',
        description: e.message,
        variant: 'destructive',
      });
    }
  };

  const handleValidate = async () => {
    try {
      const result = await connector.validateArchitecture();
      setValidationResult(result.validation);
    } catch (e: any) {
      toast({
        title: 'Validation failed',
        description: e.message,
        variant: 'destructive',
      });
    }
  };

  return (
    <Card className="space-y-4">
      <CardHeader>
        <CardTitle>Connector Manager</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="projectId">Project ID</Label>
          <Input
            id="projectId"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="projectPath">Project Path</Label>
          <Input
            id="projectPath"
            value={projectPath}
            onChange={(e) => setProjectPath(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="templateId">Template ID</Label>
          <Input
            id="templateId"
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
          />
        </div>
        <Button
          onClick={handleInit}
          disabled={!projectId || connector.status.isLoading}
        >
          Initialize Connector
        </Button>

        <hr />

        <div className="space-y-2">
          <Label htmlFor="command">Command</Label>
          <Input
            id="command"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="args">Arguments</Label>
          <Input
            id="args"
            value={args}
            onChange={(e) => setArgs(e.target.value)}
            placeholder="arg1 arg2"
          />
        </div>
        <Button
          onClick={handleExecute}
          disabled={!projectId || connector.status.isLoading}
        >
          Run Command
        </Button>

        <hr />

        <Button
          onClick={handleGraph}
          disabled={!projectId || connector.status.isLoading}
        >
          Generate Graph
        </Button>
        {graphOutput && (
          <Textarea
            className="h-40"
            readOnly
            value={JSON.stringify(graphOutput, null, 2)}
          />
        )}

        <hr />

        <Button
          onClick={handleValidate}
          disabled={!projectId || connector.status.isLoading}
        >
          Validate Architecture
        </Button>
        {validationResult && (
          <Textarea
            className="h-40"
            readOnly
            value={JSON.stringify(validationResult, null, 2)}
          />
        )}
      </CardContent>
    </Card>
  );
}

export default ConnectorManager;
