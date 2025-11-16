import { useState, type DragEvent } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileUpload } from "@/components/ui/file-upload";
import { GitHubIntegration } from "@/components/github/GitHubIntegration";
import { useTemplates, useAnalyzeCode, useValidationResults, useGraphData } from "@/hooks/use-graph";
import { useGithubAnalysis } from "@/hooks/useGithubAnalysis";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { Upload, AlertCircle, CheckCircle, AlertTriangle, Github, Code2, Sparkles, File, FileText, Folder } from "lucide-react";
import type { Template } from "@shared/schema";

interface LeftSidebarProps {
  projectId: string;
  selectedTemplate: Template | null;
  onTemplateSelect: (template: Template) => void;
}

export function LeftSidebar({ projectId, selectedTemplate, onTemplateSelect }: LeftSidebarProps) {
  const { data: templates } = useTemplates();
  const { data: validationResults } = useValidationResults(projectId);
  const analyzeCodeMutation = useAnalyzeCode();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const githubAnalysis = useGithubAnalysis(projectId);
  const [showUpload, setShowUpload] = useState(false);
  const [showGitHub, setShowGitHub] = useState(false);

  const handleTemplateChange = (templateId: string) => {
    const template = templates?.find(t => t.id === templateId);
    if (template) {
      onTemplateSelect(template);
    }
  };

  const handleCodeAnalysis = (files: FileList) => {
    if (!projectId) {
      toast({
        title: "Error",
        description: "No project selected",
        variant: "destructive",
      });
      return;
    }

    analyzeCodeMutation.mutate(
      { projectId, files },
      {
        onSuccess: (result) => {
          toast({
            title: "Analysis Complete",
            description: `Created ${result.nodesCreated} nodes and ${result.edgesCreated} connections`,
          });
          setShowUpload(false);
        },
        onError: () => {
          toast({
            title: "Analysis Failed",
            description: "Failed to analyze the codebase",
            variant: "destructive",
          });
        },
      }
    );
  };

  // GitHub Repository Analysis
  // GitHub Repository Analysis
  const handleGitHubRepositoryAnalyze = (repoUrl: string) => {
    githubAnalysis.mutate({ repoUrl }, {
      onSuccess: (result: any) => {
        toast({
          title: "🎮 REPO_SCAN_COMPLETE!",
          description: `Created ${result.nodesCreated} nodes, ${result.edgesCreated} edges from ${result.filesAnalyzed} files`,
        });
        queryClient.invalidateQueries({ queryKey: ["graphData", projectId] });
      },
      onError: () => {
        toast({ title: "Analysis Failed", description: "Repository analysis failed", variant: "destructive" });
      }
    });
  };
  const onDragStart = (event: DragEvent<HTMLDivElement>, nodeType: string) => {
    event.dataTransfer.setData("application/reactflow", nodeType);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div className="flex flex-col h-full hacker-text">
      <div className="p-4 border-b-2 border-primary hacker-border">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-primary border border-primary flex items-center justify-center">
            <span className="text-black font-black text-lg">⚡</span>
          </div>
          <div>
            <h1 className="text-xl font-black text-primary hacker-text-glow terminal-font">
              ZHUL_SYS
            </h1>
            <p className="text-sm text-primary/80 terminal-font">CODE_GRAPH_ENGINE</p>
          </div>
        </div>
      </div>

      {/* Template Selection */}
      <div className="p-4 border-b-2 border-primary hacker-border">
        <h2 className="text-sm font-black text-primary mb-3 terminal-font hacker-text-glow">ARCH_TEMPLATE</h2>
        <Select value={selectedTemplate?.id} onValueChange={handleTemplateChange}>
          <SelectTrigger className="bg-input border-2 border-primary text-primary terminal-font hacker-glow">
            <SelectValue placeholder="SELECT_TEMPLATE..." />
          </SelectTrigger>
          <SelectContent className="bg-card border-2 border-primary">
            {templates?.map((template) => (
              <SelectItem key={template.id} value={template.id} className="text-primary focus:bg-primary/20 terminal-font">
                {template.name.toUpperCase()}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {selectedTemplate && (
          <div className="mt-3 p-2 bg-primary/10 border border-primary">
            <p className="text-xs text-primary/80 terminal-font">
              {">"} {selectedTemplate.description}
            </p>
          </div>
        )}
      </div>

      {/* Code Analysis Section - Reorganized */}
      <div className="p-4 border-b-2 border-primary hacker-border">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-black text-primary terminal-font hacker-text-glow">CODE_ANALYSIS</h2>
          <div className="flex space-x-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowGitHub(!showGitHub)}
              className="text-primary hover:bg-primary/20 w-8 h-8 p-0 hacker-glow"
              title="GitHub Integration"
            >
              <Github className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowUpload(!showUpload)}
              className="text-accent hover:bg-accent/20 w-8 h-8 p-0 hacker-glow"
              title="File Upload"
            >
              <Upload className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* GitHub Integration - Collapsible */}
        {showGitHub && (
          <div className="mb-4 p-3 border border-primary/30 bg-background/50 hacker-glow">
            <GitHubIntegration 
              onRepositoryAnalyze={handleGitHubRepositoryAnalyze}
              isAnalyzing={analyzeCodeMutation.isPending}
            />
          </div>
        )}

        {/* File Upload - Collapsible */}
        {showUpload && (
          <div className="p-3 border border-accent/30 bg-background/50 hacker-glow">
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Code2 className="h-4 w-4 text-accent" />
                <span className="text-sm font-black text-accent terminal-font">LOCAL_FILES</span>
              </div>
              <FileUpload onFilesSelected={handleCodeAnalysis} />

              {analyzeCodeMutation.isPending && (
                <div className="flex items-center space-x-2 text-sm text-accent mt-2">
                  <div className="animate-spin h-3 w-3 border-2 border-accent border-t-transparent rounded-full" />
                  <span className="terminal-font">PARSING_AST...</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Validation Results */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-4">
          {validationResults && validationResults.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-black text-primary terminal-font hacker-text-glow">VALIDATION_LOG</h3>
              {validationResults.map((result) => {
                const Icon = result.status === 'valid' ? CheckCircle : 
                            result.status === 'warning' ? AlertTriangle : AlertCircle;
                const colorClass = result.status === 'valid' ? 'text-green-400' : 
                                  result.status === 'warning' ? 'text-yellow-400' : 'text-red-400';
                return (
                  <div key={result.id} className={`flex items-start space-x-2 p-2 border border-primary/30 bg-background/50 ${colorClass}`}>
                    <Icon className="h-4 w-4 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs terminal-font font-black">{result.message}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Project Files */}
      <div className="p-4 border-t-2 border-primary hacker-border">
        <h2 className="text-sm font-black text-primary mb-3 terminal-font hacker-text-glow">PROJECT_FILES</h2>
        <ProjectFilesTree projectId={projectId} />
      </div>

      {/* Node Types */}
      {selectedTemplate && (
        <div className="p-4 border-t-2 border-primary hacker-border">
          <h2 className="text-sm font-black text-primary mb-3 terminal-font hacker-text-glow">NODE_TYPES</h2>
          <div className="space-y-2">
            {selectedTemplate.nodeTypes.map((nodeType) => (
              <div
                key={nodeType.type}
                className="flex items-center space-x-3 p-2 bg-primary/10 border border-primary/30 rounded cursor-pointer hover:bg-primary/20 transition-colors hacker-glow"
                draggable
                onDragStart={(e) => onDragStart(e, nodeType.type)}
              >
                <div 
                  className="w-4 h-4 rounded border border-primary"
                  style={{ backgroundColor: nodeType.color }}
                />
                <span className="text-sm font-black capitalize text-primary terminal-font">{nodeType.type}</span>
                <div className="flex-1" />
                <Badge variant="outline" className="text-xs border-primary text-primary terminal-font">
                  DRAG
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ProjectFilesTree component to show nodes with file paths
function ProjectFilesTree({ projectId }: { projectId: string }) {
  const { data: graphData } = useGraphData(projectId);

  if (!graphData?.nodes) {
    return (
      <div className="text-center py-4 text-primary/60">
        <FileText className="h-4 w-4 mx-auto mb-1" />
        <div className="text-xs terminal-font">NO_FILES_DETECTED</div>
      </div>
    );
  }

  // Get nodes with file paths
  const nodesWithPaths = graphData.nodes.filter(node => node.filePath && node.filePath.trim());

  if (nodesWithPaths.length === 0) {
    return (
      <div className="text-center py-4 text-primary/60">
        <Folder className="h-4 w-4 mx-auto mb-1" />
        <div className="text-xs terminal-font">NO_MAPPED_FILES</div>
      </div>
    );
  }

  // Build file tree structure
  const fileTree: Record<string, any> = {};
  
  nodesWithPaths.forEach(node => {
    const pathParts = node.filePath!.split('/').filter(part => part);
    let current = fileTree;
    
    pathParts.forEach((part, index) => {
      if (!current[part]) {
        current[part] = {
          isFile: index === pathParts.length - 1,
          node: index === pathParts.length - 1 ? node : null,
          children: {}
        };
      }
      current = current[part].children;
    });
  });

  const renderTreeNode = (name: string, item: any, level = 0) => {
    const isConfirmed = item.node?.metadata?.confirmed;
    const isLoaded = item.isFile && item.node; // File with associated node is "loaded"
    const statusColor = isConfirmed ? 'text-green-400' : isLoaded ? 'text-primary' : 'text-yellow-400';
    const statusIcon = isConfirmed ? '✓' : isLoaded ? '●' : '?';

    return (
      <div key={name} style={{ marginLeft: level * 12 }}>
        <div className={`flex items-center space-x-2 py-1 px-2 cursor-pointer rounded text-xs transition-all duration-200 ${
          isLoaded 
            ? 'bg-primary/20 border border-primary/50 hover:bg-primary/30 hacker-glow' 
            : 'hover:bg-primary/10'
        } ${statusColor}`}>
          {item.isFile ? (
            <div className="relative">
              <FileText className={`h-3 w-3 ${isLoaded ? 'animate-pulse-subtle' : ''}`} />
              {isLoaded && (
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-primary rounded-full animate-pulse"></div>
              )}
            </div>
          ) : (
            <Folder className="h-3 w-3" />
          )}
          <span className={`terminal-font ${isLoaded ? 'font-black text-primary hacker-text-glow' : 'font-medium'}`}>
            {name}
          </span>
          {item.isFile && (
            <div className="flex items-center space-x-1 ml-auto">
              {isLoaded && (
                <Badge 
                  variant="outline" 
                  className="text-xs h-4 px-1 bg-primary/10 text-primary border-primary animate-pulse-subtle"
                >
                  {item.node?.type?.toUpperCase()}
                </Badge>
              )}
              <span className={`text-xs font-black ${isLoaded ? 'text-primary animate-pulse' : ''}`}>
                {statusIcon}
              </span>
              {isLoaded && (
                <span className="text-xs text-primary/80 terminal-font font-black">LOADED</span>
              )}
            </div>
          )}
        </div>
        
        {!item.isFile && Object.keys(item.children).length > 0 && (
          <div>
            {Object.entries(item.children).map(([childName, childItem]) =>
              renderTreeNode(childName, childItem, level + 1)
            )}
          </div>
        )}
      </div>
    );
  };

  const loadedFilesCount = nodesWithPaths.length;
  const confirmedFilesCount = nodesWithPaths.filter(node => node.metadata?.confirmed).length;

  return (
    <div className="space-y-2">
      {/* Status Header */}
      <div className="flex items-center justify-between p-2 bg-primary/10 border border-primary/30 rounded">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
          <span className="text-xs terminal-font font-black text-primary">
            {loadedFilesCount} LOADED
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs terminal-font text-green-400">
            {confirmedFilesCount}✓
          </span>
          <span className="text-xs terminal-font text-yellow-400">
            {loadedFilesCount - confirmedFilesCount}?
          </span>
        </div>
      </div>

      {/* File Tree */}
      <div className="space-y-1 max-h-64 overflow-y-auto border border-primary/30 rounded p-2 bg-background/50 hacker-glow">
        {Object.entries(fileTree).map(([name, item]) =>
          renderTreeNode(name, item)
        )}
      </div>
    </div>
  );
}