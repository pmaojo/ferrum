import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { GraphCanvas } from './graph/GraphCanvas';
import { NodeCreationForm } from './NodeCreationForm';
import ProjectFileViewer from './file-explorer/ProjectFileViewer';
import { TemplateProvider } from '@/context/TemplateContext';
import { useProjects, useTemplates, useCreateProject } from '@/hooks/use-graph';
import { useToast } from '@/hooks/use-toast';
import { Plus, Github, Zap, Play } from 'lucide-react';
import type { Node } from 'reactflow';
import type { GraphNodeData } from '@/types/graph';
import type { Template } from '@shared/schema';

const nodeTypes = [
  {
    id: 'controller',
    name: 'Controller',
    color: '#00FFFF',
    description: 'HTTP endpoints',
  },
  {
    id: 'service',
    name: 'Service',
    color: '#00FF41',
    description: 'Business logic',
  },
  {
    id: 'repository',
    name: 'Repository',
    color: '#FFB000',
    description: 'Data access',
  },
  {
    id: 'entity',
    name: 'Entity',
    color: '#FF4081',
    description: 'Domain models',
  },
  { id: 'dto', name: 'Dto', color: '#9C27B0', description: 'Data transfer' },
  {
    id: 'guard',
    name: 'Guard',
    color: '#E91E63',
    description: 'Auth/validation',
  },
  {
    id: 'middleware',
    name: 'Middleware',
    color: '#00BCD4',
    description: 'Request processing',
  },
  {
    id: 'usecase',
    name: 'UseCase',
    color: '#FFFF00',
    description: 'Business operations',
  },
];

export default function UnifiedTGAInterface() {
  const { data: projects } = useProjects();
  const { data: templates } = useTemplates();
  const createProjectMutation = useCreateProject();
  const { toast } = useToast();

  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(
    null
  );
  const [selectedNode, setSelectedNode] = useState<Node<GraphNodeData> | null>(
    null
  );
  const [showNodeForm, setShowNodeForm] = useState(false);
  const [githubUrl, setGithubUrl] = useState('');
  const [gameScore, setGameScore] = useState(1250);
  const [comboMultiplier, setComboMultiplier] = useState(1);

  // Auto-setup project and template
  useEffect(() => {
    if (templates && templates.length > 0 && !selectedTemplate) {
      setSelectedTemplate(templates[0]);
    }
  }, [templates, selectedTemplate]);

  useEffect(() => {
    if (
      projects &&
      projects.length === 0 &&
      selectedTemplate &&
      !createProjectMutation.isPending
    ) {
      createProjectMutation.mutate({
        name: 'TGA_TERMINAL_001',
        description: 'Tandy Graphics Adapter Terminal Project',
        templateId: selectedTemplate.id,
        projectPath: '.',
      });
    } else if (projects && projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedTemplate, selectedProjectId, createProjectMutation]);

  const handleDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  const handleNodeCreation = async (nodeData: any) => {
    try {
      if (!selectedTemplate) {
        toast({
          title: 'MISSING_TEMPLATE',
          description: 'Select a template before creating nodes',
          variant: 'destructive',
        });
        return;
      }

      const response = await fetch('/api/nodes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: nodeData.name,
          type: nodeData.type,
          position: nodeData.position || {
            x: Math.random() * 400,
            y: Math.random() * 300,
          },
          templateId: selectedTemplate.id,
          projectId: selectedProjectId,
          description: nodeData.description || null,
          filePath: nodeData.filePath || null,
          metadata: {},
        }),
      });

      if (response.ok) {
        setGameScore((prev) => prev + 50 * comboMultiplier);
        setComboMultiplier((prev) => Math.min(prev + 0.5, 5));
        toast({
          title: 'NODE_CREATED',
          description: `+${50 * comboMultiplier} SCORE`,
        });
      }
    } catch (error) {
      toast({
        title: 'CREATION_FAILED',
        description: 'Node creation error',
        variant: 'destructive',
      });
    }
  };

  const handleGitHubScan = async () => {
    if (!githubUrl || !selectedProjectId) return;

    try {
      const response = await fetch(
        `/api/projects/${selectedProjectId}/analyze-github`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ repoUrl: githubUrl }),
        }
      );

      if (response.ok) {
        const result = await response.json();
        setGameScore((prev) => prev + result.nodesCreated * 25);
        toast({
          title: 'REPO_SCANNED',
          description: `${result.nodesCreated} nodes created`,
        });
        setGithubUrl('');
      }
    } catch (error) {
      toast({
        title: 'SCAN_FAILED',
        description: 'GitHub analysis failed',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="min-h-screen bg-black text-[#00FF41] font-mono overflow-hidden tga-scanlines">
      {/* TGA Header */}
      <div className="border-b-2 border-[#00FF41] bg-black/90 backdrop-blur-sm">
        <div className="flex items-center justify-between px-4 py-2">
          <div className="flex items-center space-x-4">
            <div className="text-[#00FFFF] font-bold text-lg tracking-wider">
              TGA_TERMINAL_001
            </div>
            <div className="text-[#FFFF00] text-sm">
              SCORE: {gameScore.toLocaleString()}
            </div>
            <div className="text-[#FF00FF] text-sm">
              COMBO: x{comboMultiplier}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              onClick={() => setShowNodeForm(true)}
              disabled={!selectedProjectId}
              className="bg-[#00FF41] text-black hover:bg-[#00FF41]/80 font-mono text-xs px-3 py-1 h-8"
            >
              <Plus className="h-3 w-3 mr-1" />
              ADD_NODE
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="border-[#00FFFF] text-[#00FFFF] hover:bg-[#00FFFF]/10 font-mono text-xs h-8"
            >
              <Play className="h-3 w-3 mr-1" />
              VALIDATE
            </Button>
          </div>
        </div>
      </div>

      <div className="flex h-[calc(100vh-60px)]">
        {/* Compact NODE_TYPES Sidebar */}
        <div className="w-72 border-r-2 border-[#00FF41] bg-black/90 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="mb-4">
            <h2 className="text-[#00FF41] font-bold text-lg mb-3 tracking-wider glow-text">
              NODE_TYPES
            </h2>

            <div className="space-y-2">
              {nodeTypes.map((nodeType) => (
                <div
                  key={nodeType.id}
                  draggable
                  onDragStart={(e) => handleDragStart(e, nodeType.id)}
                  className="flex items-center justify-between p-3 border border-[#00FF41] rounded bg-black/50 hover:bg-[#00FF41]/10 cursor-grab active:cursor-grabbing transition-all duration-200 hover:border-[#00FFFF] group"
                >
                  <div className="flex items-center space-x-3">
                    <div
                      className="w-4 h-4 rounded border-2"
                      style={{
                        backgroundColor: nodeType.color + '40',
                        borderColor: nodeType.color,
                      }}
                    />
                    <div>
                      <div className="text-[#00FF41] font-semibold text-sm group-hover:text-[#00FFFF]">
                        {nodeType.name}
                      </div>
                      <div className="text-[#00FF41]/60 text-xs">
                        {nodeType.description}
                      </div>
                    </div>
                  </div>
                  <div className="text-[#00FF41] border border-[#00FF41] rounded px-2 py-1 text-xs group-hover:border-[#00FFFF] group-hover:text-[#00FFFF]">
                    DRAG
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* GitHub Scanner */}
          <div className="mt-6 p-3 border border-[#FF00FF] rounded bg-black/50">
            <h3 className="text-[#FF00FF] font-semibold text-sm mb-2 tracking-wider">
              GITHUB_SCANNER
            </h3>
            <div className="space-y-2">
              <Input
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                placeholder="github.com/user/repo"
                className="bg-black border-[#FF00FF] text-[#FF00FF] placeholder:text-[#FF00FF]/50 font-mono text-xs h-8"
              />
              <Button
                onClick={handleGitHubScan}
                disabled={!githubUrl || !selectedProjectId}
                className="w-full bg-[#FF00FF] text-black hover:bg-[#FF00FF]/80 font-mono text-xs h-8"
              >
                <Github className="h-3 w-3 mr-1" />
                SCAN_REPO
              </Button>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="mt-6 p-3 border border-[#FFFF00] rounded bg-black/50">
            <h3 className="text-[#FFFF00] font-semibold text-sm mb-2 tracking-wider">
              SYSTEM_STATUS
            </h3>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-[#00FF41]">PROJECT:</span>
                <span className="text-[#00FFFF]">ACTIVE</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#00FF41]">TEMPLATE:</span>
                <span className="text-[#00FFFF]">NESTJS</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#00FF41]">NODES:</span>
                <span className="text-[#00FFFF]">SYNCED</span>
              </div>
            </div>
          </div>
        </div>

        {/* Main Graph Area */}
        <div className="flex-1 relative">
          {selectedProjectId ? (
            <TemplateProvider projectId={selectedProjectId}>
              <GraphCanvas
                projectId={selectedProjectId}
                onNodeSelect={setSelectedNode}
              />
            </TemplateProvider>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="text-[#FF00FF] text-2xl font-bold mb-4 tracking-wider glow-text">
                  INITIALIZING_TERMINAL...
                </div>
                <div className="text-[#00FF41] text-sm">
                  Setting up TGA graphics mode
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      {/* Node Creation Form */}
      <TemplateProvider projectId={selectedProjectId}>
        <NodeCreationForm
          isOpen={showNodeForm}
          onClose={() => setShowNodeForm(false)}
          onSubmit={handleNodeCreation}
          position={{ x: 100, y: 100 }}
        />
      </TemplateProvider>

      <ProjectFileViewer
        projectId={selectedProjectId}
        path={selectedNode?.data.filePath || ''}
        line={selectedNode?.data.sourceMap?.line}
        open={Boolean(selectedNode?.data.filePath)}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  );
}
