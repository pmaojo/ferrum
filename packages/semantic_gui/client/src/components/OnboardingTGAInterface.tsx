import { useState, useEffect, useCallback, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ProjectSetup } from "./ProjectSetup";
import { SmartGraphEditor } from "./graph/SmartGraphEditor";
import { NodeCreationForm } from "./NodeCreationForm";
import { TemplateProvider } from '@/context/TemplateContext';
import { useProjects, useGraphData } from "@/hooks/use-graph";
import { useGithubAnalysis } from "@/hooks/useGithubAnalysis";
import { useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import {
  Plus,
  Github,
  Upload,
  FileText,
  Zap,
  Play,
  Bot,
  Menu,
  Brain,
  Sparkles,
  Target,
  Code,
  X,
} from "lucide-react";
import { AIResultsPanel } from "./AIResultsPanel";
import { AdvancedAIInsights } from "./AdvancedAIInsights";
import { AIArchitect } from "./AIArchitect";
import type { Node } from "reactflow";
import type { GraphNodeData } from "@/types/graph";
import type { Template } from "@shared/schema";
import { LeftSidebar } from "./sidebar/LeftSidebar";
import { RightSidebar } from "./sidebar/RightSidebar";
import {
  ArchitectureTree,
  type ArchitectureTreeNode,
} from "./sidebar/ArchitectureTree";
import { ProjectFileViewer } from "./file-explorer/ProjectFileViewer";

export default function OnboardingTGAInterface() {
  const { data: projects } = useProjects();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Onboarding state
  const [currentStep, setCurrentStep] = useState(0); // Start with home screen
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(
    null,
  );
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [repositoryConnected, setRepositoryConnected] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [showGlitch, setShowGlitch] = useState(false);

  // App state
  const [selectedNode, setSelectedNode] = useState<Node<GraphNodeData> | null>(
    null,
  );
  const [showNodeForm, setShowNodeForm] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [showAIAssistant, setShowAIAssistant] = useState(false);
  const [fileTree, setFileTree] = useState<ArchitectureTreeNode[]>([]);
  const [viewMode, setViewMode] = useState<'folder' | 'layered' | 'hexagonal'>('folder');
  const [focusNodeId, setFocusNodeId] = useState<string | null>(null);
  const { data: graphData } = useGraphData(selectedProjectId);
  const [githubUrl, setGithubUrl] = useState("");
  const [githubToken, setGithubToken] = useState("");
    const [pendingNodePosition, setPendingNodePosition] = useState<{ x: number; y: number } | null>(null);
  const [showFileViewer, setShowFileViewer] = useState(false);


  // AI Architect state
  const [showAiChat, setShowAiChat] = useState(false);
  const [aiRequest, setAiRequest] = useState("");
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [showValidation, setShowValidation] = useState(false);
  const [validationResults, setValidationResults] = useState<any>(null);
  const [showAdvancedInsights, setShowAdvancedInsights] = useState(false);

  // Memoize edgeTypes

  // Auto-setup projects when selecting from home screen
  const handleProjectSelect = (projectId: string) => {
    setSelectedProjectId(projectId);
    setRepositoryConnected(true);
    setCurrentStep(3); // Jump directly to main interface
  };

  const githubAnalysis = useGithubAnalysis(selectedProjectId);
  const handleGitHubConnect = () => {
    if (!githubUrl || !selectedProjectId) return;
    githubAnalysis.mutate({ repoUrl: githubUrl, accessToken: githubToken || undefined }, {
      onSuccess: (result: any) => {
        setRepositoryConnected(true);
        if (result.fileTree) setFileTree(result.fileTree);
        setCurrentStep(3);
        toast({ title: "REPOSITORY_CONNECTED", description: `${result.nodesCreated} nodes generated from codebase` });
      },
      onError: () => {
        toast({ title: "CONNECTION_FAILED", description: "GitHub repository analysis failed", variant: "destructive" });
      }
    });
  };

  const handleRequirementRefresh = async () => {
    try {
      await fetch('/api/v1/docs-ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectId: selectedProjectId }),
      });
      toast({
        title: 'DOCS_INGESTED',
        description: 'Requirement docs sent to PermaGraph',
      });
    } catch {
      toast({
        title: 'INGEST_FAILED',
        description: 'Failed to ingest requirement docs',
        variant: 'destructive',
      });
    }
  };

  const handleNodeCreation = async (nodeData: any) => {
    if (!selectedTemplate) {
      toast({
        title: "MISSING_TEMPLATE",
        description: "Please select a template first",
        variant: "destructive",
      });
      return null;
    }
    try {
      const response = await fetch("/api/nodes", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...nodeData,
          templateId: selectedTemplate.id,
          projectId: selectedProjectId,
        }),
      });

      if (response.ok) {
        const createdNode = await response.json();
        toast({
          title: "NODE_CREATED",
          description: `${nodeData.type} added to architecture`,
        });
        return createdNode;
      }
    } catch (error) {
      toast({
        title: "CREATION_FAILED",
        description: "Node creation error",
        variant: "destructive",
      });
    }
    return null;
  };

  const handleNodeUpdate = (nodeId: string, updates: Partial<GraphNodeData>) => {
    // Implementation for updating node data
    console.log("Updating node:", nodeId, updates);
  };

  const handleNodeSelect = (node: any) => {
    setSelectedNode(node);
    if (node?.data?.filePath) {
      setShowFileViewer(true);
    }
  };

  const handleTreeNodeSelect = (node: ArchitectureTreeNode) => {
    if (node.nodeId) {
      setFocusNodeId(node.nodeId);
    } else if (node.type === 'file') {
      const match = graphData?.nodes?.find((n) => n.filePath === node.path);
      if (match) setFocusNodeId(match.id);
    }
  };

  const displayedTree = useMemo<ArchitectureTreeNode[]>(() => {
    if (viewMode === 'folder') {
      return fileTree;
    }
    const nodes = graphData?.nodes || [];
    const groups: Record<string, ArchitectureTreeNode[]> = {};
    nodes.forEach((n) => {
      const meta = (n.metadata || {}) as any;
      let key = '';
      if (viewMode === 'layered') {
        key = meta.layer || meta.architectureLayer || n.type || 'misc';
      } else if (viewMode === 'hexagonal') {
        key = meta.hexagonalRole || meta.role || n.type || 'misc';
      }
      if (!groups[key]) groups[key] = [];
      groups[key].push({
        name: n.name,
        type: 'file',
        path: n.id,
        nodeId: n.id,
      });
    });
    return Object.entries(groups).map(([name, children]) => ({
      name,
      type: 'folder',
      path: name,
      children,
    }));
  }, [viewMode, fileTree, graphData]);

  // Real AI Architect Analysis Function
  const analyzeAIRequest = async () => {
    if (!aiRequest.trim() || !selectedProjectId) return;

    console.log("🤖 Starting REAL AI analysis for:", aiRequest);
    setIsAiProcessing(true);
    playBootSound();

    try {
      // Get current graph data for context
      const graphResponse = await fetch(
        `/api/projects/${selectedProjectId}/graph`,
      );
      const graphData = await graphResponse.json();

      // Call the real AI analysis endpoint
      if (!selectedTemplate) {
        toast({
          title: "MISSING_TEMPLATE",
          description: "Select a template before requesting analysis",
          variant: "destructive",
        });
        return;
      }
      const response = await fetch(
        `/api/projects/${selectedProjectId}/ai-analyze-request`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            request: aiRequest,
            existingNodes: graphData.nodes || [],
            existingEdges: graphData.edges || [],
            templateId: selectedTemplate.id,
          }),
        },
      );

      if (!response.ok) {
        throw new Error(`AI analysis failed: ${response.status}`);
      }

      const aiAnalysisResult = await response.json();

      const analysis = {
        request: aiRequest,
        suggestedNodes: aiAnalysisResult.suggestedNodes || [],
        reasoning: aiAnalysisResult.reasoning || "AI analysis completed",
        confidence: aiAnalysisResult.confidence || 0.8,
        architecturalPatterns: aiAnalysisResult.architecturalPatterns || [],
      };

      console.log("🎯 REAL AI Analysis complete:", analysis);
      setAiAnalysis(analysis);

      toast({
        title: "🧠 AI_ANALYSIS_COMPLETE",
        description: `Generated ${analysis.suggestedNodes.length} architecture suggestions`,
      });
    } catch (error) {
      console.error("AI analysis failed:", error);
      toast({
        title: "🚨 AI_ANALYSIS_ERROR",
        description: "Real AI analysis temporarily unavailable",
        variant: "destructive",
      });

      // Fallback to basic pattern matching
      const basicAnalysis = generateBasicAnalysis(aiRequest);
      setAiAnalysis(basicAnalysis);
    }

    setIsAiProcessing(false);
    playGlitchSound();
  };

  // Fallback analysis for when AI is unavailable
  const generateBasicAnalysis = (request: string) => {
    const requestLower = request.toLowerCase();
    let suggestedNodes = [];

    if (requestLower.includes("auth") || requestLower.includes("login")) {
      suggestedNodes = [
        {
          name: "AuthController",
          type: "controller",
          description: "Authentication endpoints",
        },
        {
          name: "AuthService",
          type: "service",
          description: "Authentication business logic",
        },
        {
          name: "UserRepository",
          type: "repository",
          description: "User data access",
        },
        { name: "User", type: "entity", description: "User entity model" },
      ];
    } else if (requestLower.includes("payment")) {
      suggestedNodes = [
        {
          name: "PaymentController",
          type: "controller",
          description: "Payment processing API",
        },
        {
          name: "PaymentService",
          type: "service",
          description: "Payment business logic",
        },
        {
          name: "PaymentRepository",
          type: "repository",
          description: "Payment data storage",
        },
      ];
    } else {
      const baseName = request.split(" ")[0] || "Feature";
      suggestedNodes = [
        {
          name: `${baseName}Controller`,
          type: "controller",
          description: `${baseName} API endpoints`,
        },
        {
          name: `${baseName}Service`,
          type: "service",
          description: `${baseName} business logic`,
        },
      ];
    }

    return {
      request,
      suggestedNodes,
      reasoning: `Basic pattern analysis for "${request}"`,
      confidence: 0.6,
    };
  };

  const handleCreateNodeFromAI = async (nodeData: any) => {
    if (!selectedProjectId || !selectedTemplate) return;

    try {
      playBootSound();

      const newNode = {
        name: nodeData.name,
        type: nodeData.type,
        description: nodeData.description,
        projectId: selectedProjectId,
        templateId: selectedTemplate.id,
        position: { x: Math.random() * 400, y: Math.random() * 300 },
        metadata: {
          aiGenerated: true,
          reasoning: nodeData.reasoning,
          dependencies: nodeData.dependencies || [],
        },
        filePath: `src/${nodeData.type}s/${nodeData.name.toLowerCase()}.${nodeData.type}.ts`,
      };

      const response = await fetch("/api/nodes", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(newNode),
      });

      if (!response.ok) {
        throw new Error("Failed to create node");
      }

      const createdNode = await response.json();
      console.log(
        `✅ Created node: ${createdNode.name} with ID: ${createdNode.id}`,
      );

      // Wait for node to be fully persisted
      await new Promise((resolve) => setTimeout(resolve, 200));

      // Get FRESH graph data that includes the newly created node
      const graphResponse = await fetch(
        `/api/projects/${selectedProjectId}/graph?t=${Date.now()}`,
      );
      const graphData = await graphResponse.json();
      const allNodes = graphData.nodes || [];

      console.log(
        `🔍 All nodes for connections:`,
        allNodes.map((n: any) => ({ id: n.id, name: n.name, type: n.type })),
      );

      // Create architectural connections based on node type
      const architecturalConnections = generateArchitecturalConnections(
        createdNode,
        allNodes,
      );

      console.log(
        `🔗 Attempting to create ${architecturalConnections.length} connections`,
      );

      for (const conn of architecturalConnections) {
        try {
          console.log(
            `🔗 Creating connection: ${conn.sourceId} → ${conn.targetId} (${conn.reason})`,
          );

          const edgeData = {
            sourceNodeId: conn.sourceId,
            targetNodeId: conn.targetId,
            type: conn.type,
            projectId: selectedProjectId,
            metadata: {
              aiGenerated: true,
              reason: conn.reason,
              methodCalls: [],
              parameters: [],
            },
          };

          const edgeResponse = await fetch("/api/edges", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(edgeData),
          });

          if (edgeResponse.ok) {
            const edgeResult = await edgeResponse.json();
            console.log(`✅ Created edge with ID: ${edgeResult.id}`);
          } else {
            const errorText = await edgeResponse.text();
            console.error(
              `❌ Failed to create edge: ${edgeResponse.status} - ${errorText}`,
            );
          }

          // Small delay between edge creations
          await new Promise((resolve) => setTimeout(resolve, 100));
        } catch (edgeError) {
          console.error(
            "Failed to create architectural connection:",
            edgeError,
          );
        }
      }

      // Force refresh the graph data
      await new Promise((resolve) => setTimeout(resolve, 300));
      await queryClient.invalidateQueries({
        queryKey: [`/api/projects/${selectedProjectId}/graph`],
      });
      await queryClient.refetchQueries({
        queryKey: [`/api/projects/${selectedProjectId}/graph`],
      });

      toast({
        title: "🎯 NODE+CONNECTIONS_CREATED",
        description: `${nodeData.name} added with ${architecturalConnections.length} connections`,
      });
    } catch (error) {
      console.error("Error creating AI node:", error);
      toast({
        title: "❌ CREATION_FAILED",
        description: "Failed to create AI-suggested node",
        variant: "destructive",
      });
    }
  };

  // Helper function to generate architectural connections
  const generateArchitecturalConnections = (
    newNode: any,
    existingNodes: any[],
  ) => {
    const connections: any[] = [];

    // Controller connects to Services
    if (newNode.type === "controller") {
      const services = existingNodes.filter(
        (n: any) => n.type === "service" && areRelated(newNode.name, n.name),
      );
      services.forEach((service: any) => {
        connections.push({
          sourceId: newNode.id,
          targetId: service.id,
          type: "uses",
          reason: "Controller uses service for business logic",
        });
      });
    }

    // Service connects to Repositories
    if (newNode.type === "service") {
      const repositories = existingNodes.filter(
        (n: any) => n.type === "repository" && areRelated(newNode.name, n.name),
      );
      repositories.forEach((repo: any) => {
        connections.push({
          sourceId: newNode.id,
          targetId: repo.id,
          type: "depends",
          reason: "Service depends on repository for data access",
        });
      });
    }

    // Repository connects to Entities
    if (newNode.type === "repository") {
      const entities = existingNodes.filter(
        (n: any) => n.type === "entity" && areRelated(newNode.name, n.name),
      );
      entities.forEach((entity: any) => {
        connections.push({
          sourceId: newNode.id,
          targetId: entity.id,
          type: "manages",
          reason: "Repository manages entity data",
        });
      });
    }

    return connections;
  };

  // Helper function to check if two nodes are related
  const areRelated = (name1: string, name2: string): boolean => {
    const normalize = (str: string) =>
      str
        .toLowerCase()
        .replace(/controller|service|repository|entity|usecase|dto/gi, "")
        .replace(/[^a-z]/gi, "");

    const base1 = normalize(name1);
    const base2 = normalize(name2);

    // Check if they share common words or are semantically related
    return (
      base1.includes(base2) ||
      base2.includes(base1) ||
      base1 === base2 ||
      getSemanticSimilarity(base1, base2) > 0.6
    );
  };

  // Helper function for semantic similarity
  const getSemanticSimilarity = (str1: string, str2: string): number => {
    const domainConcepts = [
      ["auth", "user", "login", "authentication"],
      ["payment", "transaction", "billing", "invoice"],
      ["order", "product", "cart", "purchase"],
      ["chat", "message", "communication", "notification"],
      ["file", "upload", "storage", "media"],
      ["admin", "management", "dashboard", "control"],
    ];

    for (const concepts of domainConcepts) {
      const str1InConcept = concepts.some((concept) =>
        str1.toLowerCase().includes(concept),
      );
      const str2InConcept = concepts.some((concept) =>
        str2.toLowerCase().includes(concept),
      );

      if (str1InConcept && str2InConcept) {
        return 0.8;
      }
    }

    return 0;
  };

  // Helper function to determine architectural connections
  const getArchitecturalConnection = (
    sourceType: string,
    targetType: string,
  ): { type: string; reason: string } | null => {
    const connectionRules = [
      {
        from: "controller",
        to: "service",
        type: "uses",
        reason: "Controller uses service for business logic",
      },
      {
        from: "service",
        to: "repository",
        type: "depends_on",
        reason: "Service depends on repository for data access",
      },
      {
        from: "repository",
        to: "entity",
        type: "manages",
        reason: "Repository manages entity data",
      },
      {
        from: "usecase",
        to: "service",
        type: "orchestrates",
        reason: "Use case orchestrates service operations",
      },
      {
        from: "controller",
        to: "usecase",
        type: "uses",
        reason: "Controller uses use case for complex operations",
      },
      {
        from: "service",
        to: "entity",
        type: "transforms",
        reason: "Service transforms entity data",
      },
      {
        from: "service",
        to: "dto",
        type: "uses",
        reason: "Service uses DTO for data transfer",
      },
      {
        from: "controller",
        to: "dto",
        type: "uses",
        reason: "Controller uses DTO for request/response",
      },
    ];

    return (
      connectionRules.find(
        (rule) => rule.from === sourceType && rule.to === targetType,
      ) || null
    );
  };

  // Create all AI suggested nodes with proper connections
  const createAISuggestedNodes = async () => {
    if (!aiAnalysis?.suggestedNodes) return;
    if (!selectedTemplate) {
      toast({
        title: "MISSING_TEMPLATE",
        description: "Select a template before creating nodes",
        variant: "destructive",
      });
      return;
    }

    setIsAiProcessing(true);
    const createdNodeIds: { [name: string]: string } = {};

    console.log(
      `🚀 Starting creation of ${aiAnalysis.suggestedNodes.length} AI nodes`,
    );

    // First pass: Create all nodes sequentially
    for (let i = 0; i < aiAnalysis.suggestedNodes.length; i++) {
      const node = aiAnalysis.suggestedNodes[i];

      const nodeData = {
        name: node.name,
        type: node.type,
        position: { x: 200 + i * 150, y: 100 + i * 100 },
        description: node.description,
        projectId: selectedProjectId,
        templateId: selectedTemplate.id,
        metadata: { aiGenerated: true, functionality: aiRequest },
        filePath: `src/${node.type}s/${node.name.toLowerCase()}.${node.type}.ts`,
      };

      try {
        const response = await fetch("/api/nodes", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(nodeData),
        });

        if (response.ok) {
          const createdNode = await response.json();
          createdNodeIds[node.name] = createdNode.id;
          console.log(
            `✅ Created node: ${node.name} with ID: ${createdNode.id}`,
          );

          playGlitchSound();
          toast({
            title: `AI_CREATED: ${node.name}`,
            description: `+25 XP • ${node.description}`,
          });
        } else {
          console.error(
            `❌ Failed to create node ${node.name}: ${response.status}`,
          );
        }

        // Small delay between node creations
        await new Promise((resolve) => setTimeout(resolve, 400));
      } catch (error) {
        console.error("Failed to create AI node:", error);
      }
    }

    console.log(
      `📊 Created ${Object.keys(createdNodeIds).length} nodes, starting connection phase`,
    );

    // Wait for all nodes to be persisted
    await new Promise((resolve) => setTimeout(resolve, 800));

    // Get FRESH graph data that includes ALL newly created nodes
    const graphResponse = await fetch(
      `/api/projects/${selectedProjectId}/graph?timestamp=${Date.now()}`,
    );
    const graphData = await graphResponse.json();
    const allNodes = graphData.nodes || [];

    console.log(
      "🔗 All nodes available for connections:",
      allNodes.map((n: any) => ({ id: n.id, name: n.name, type: n.type })),
    );

    // Second pass: Create architectural connections between ALL nodes (new and existing)
    const connectionsCreated = [];

    // For each newly created node, try to connect to both new and existing nodes
    for (const [nodeName, nodeId] of Object.entries(createdNodeIds)) {
      const currentNode = allNodes.find((n: any) => n.id === nodeId);
      if (!currentNode) {
        console.warn(`❌ Could not find node ${nodeName} with ID ${nodeId}`);
        continue;
      }

      // Try to connect to ALL other nodes in the graph
      for (const targetNode of allNodes as any[]) {
        if (targetNode.id === currentNode.id) continue; // Don't connect to self

        const connectionType = getArchitecturalConnection(
          currentNode.type,
          targetNode.type,
        );

        if (connectionType && areRelated(currentNode.name, targetNode.name)) {
          try {
            const edgeData = {
              sourceNodeId: currentNode.id,
              targetNodeId: targetNode.id,
              type: connectionType.type,
              projectId: selectedProjectId,
              metadata: {
                aiGenerated: true,
                reason: connectionType.reason,
                methodCalls: [],
                parameters: [],
              },
            };

            console.log(
              `🔗 Creating connection: ${currentNode.name} (${currentNode.type}) → ${targetNode.name} (${targetNode.type})`,
            );

            const edgeResponse = await fetch("/api/edges", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(edgeData),
            });

            if (edgeResponse.ok) {
              const createdEdge = await edgeResponse.json();
              connectionsCreated.push(
                `${currentNode.name} → ${targetNode.name}`,
              );
              console.log(`✅ Created edge with ID: ${createdEdge.id}`);
              playGlitchSound();
            } else {
              const errorText = await edgeResponse.text();
              console.warn(
                `❌ Failed to create edge: ${edgeResponse.status} - ${errorText}`,
              );
            }

            // Small delay between edge creations to avoid overwhelming the server
            await new Promise((resolve) => setTimeout(resolve, 150));
          } catch (edgeError) {
            console.error("Failed to create connection:", edgeError);
          }
        }
      }
    }

    console.log(`📊 Created ${connectionsCreated.length} connections`);

    // Force refresh the graph data multiple times to ensure it updates
    await new Promise((resolve) => setTimeout(resolve, 500));

    if (selectedProjectId) {
      // Force multiple cache invalidations
      await queryClient.invalidateQueries({ queryKey: ["graph-data"] });
      await queryClient.invalidateQueries({
        queryKey: [`/api/projects/${selectedProjectId}/graph`],
      });

      // Force refetch
      await queryClient.refetchQueries({
        queryKey: [`/api/projects/${selectedProjectId}/graph`],
      });

      // Additional invalidation after a delay
      setTimeout(() => {
        queryClient.invalidateQueries({
          queryKey: [`/api/projects/${selectedProjectId}/graph`],
        });
      }, 1000);
    }

    setIsAiProcessing(false);
    setShowAIAssistant(false);
    setAiAnalysis(null);
    setAiRequest("");

    toast({
      title: "🎯 AI_ARCHITECTURE_COMPLETE!",
      description: `Created ${Object.keys(createdNodeIds).length} nodes + ${connectionsCreated.length} connections`,
    });

    console.log("🎉 AI Architecture generation complete!");
    console.log("📊 Final results:", {
      nodesCreated: Object.keys(createdNodeIds).length,
      connectionsCreated: connectionsCreated.length,
      connections: connectionsCreated,
    });
  };


  // Multi-language support
  const translations = {
    es: {
      title: "ZHUL_SYS_",
      subtitle: "INICIALIZACIÓN ARQUITECTURA",
      step1: "PASO 1/3: SELECCIONAR PLANTILLA",
      step2: "PASO 2/3: CONECTAR REPOSITORIO",
      step3: "PASO 3/3: INTERACCIÓN GRAFO",
      clickToInit: "CLICK_PARA_INICIALIZAR_ZHUL_SYS_",
      description1:
        "ZHUL_SYS_ es una plataforma de vanguardia que transforma el código fuente en grafos arquitectónicos inteligentes y visualizaciones interactivas. Utiliza análisis semántico avanzado con IA para mapear automáticamente las relaciones entre componentes, identificar patrones arquitectónicos como hexagonal, DDD y SOLID, y generar insights profundos sobre la estructura del software.",
      description2:
        "A través de una experiencia gaming con sistema de puntuación, logros y niveles, ZHUL_SYS_ convierte el análisis de arquitectura en una experiencia envolvente donde cada decisión de diseño cuenta. Los desarrolladores pueden explorar codebases existentes, crear nuevos nodos arquitectónicos, establecer conexiones semánticas y recibir retroalimentación instantánea sobre la salud del sistema.",
    },
    en: {
      title: "ZHUL_SYS_",
      subtitle: "ARCHITECTURE INITIALIZATION",
      step1: "STEP 1/3: SELECT TEMPLATE",
      step2: "STEP 2/3: CONNECT REPOSITORY",
      step3: "STEP 3/3: GRAPH INTERACTION",
      clickToInit: "CLICK_TO_INITIALIZE_ZHUL_SYS_",
      description1:
        "ZHUL_SYS_ is a cutting-edge platform that transforms source code into intelligent architectural graphs and interactive visualizations. It uses advanced AI semantic analysis to automatically map component relationships, identify architectural patterns like hexagonal, DDD and SOLID, and generate deep insights into software structure.",
      description2:
        "Through a gaming experience with scoring systems, achievements and levels, ZHUL_SYS_ turns architecture analysis into an immersive experience where every design decision counts. Developers can explore existing codebases, create new architectural nodes, establish semantic connections and receive instant feedback on system health.",
    },
    zh: {
      title: "ZHUL_SYS_",
      subtitle: "电子复古架构初始化",
      step1: "步骤 1/3: 选择模板",
      step2: "步骤 2/3: 连接存储库",
      step3: "步骤 3/3: 图形交互",
      clickToInit: "点击_初始化_ZHUL_SYS_",
      description1:
        "ZHUL_SYS_ 是一个前沿平台，将源代码转换为智能架构图和交互式可视化。它使用先进的AI语义分析来自动映射组件关系，识别六边形、DDD和SOLID等架构模式，并对软件结构产生深刻见解。",
      description2:
        "通过带有评分系统、成就和等级的游戏体验，ZHUL_SYS_ 将架构分析转变为沉浸式体验，每个设计决策都很重要。开发人员可以探索现有代码库，创建新的架构节点，建立语义连接并获得系统健康状况的即时反馈。",
    },
    fr: {
      title: "ZHUL_SYS_",
      subtitle: "INITIALISATION ARCHITECTURE ÉLECTRORÉTRO",
      step1: "ÉTAPE 1/3: SÉLECTIONNER MODÈLE",
      step2: "ÉTAPE 2/3: CONNECTER DÉPÔT",
      step3: "ÉTAPE 3/3: INTERACTION GRAPHIQUE",
      clickToInit: "CLIQUER_POUR_INITIALISER_ZHUL_SYS_",
      description1:
        "ZHUL_SYS_ est une plateforme de pointe qui transforme le code source en graphiques architecturaux intelligents et visualisations interactives. Il utilise une analyse sémantique IA avancée pour mapper automatiquement les relations entre composants, identifier les modèles architecturaux comme hexagonal, DDD et SOLID, et générer des insights profonds sur la structure logicielle.",
      description2:
        "Grâce à une expérience gaming avec systèmes de notation, succès et niveaux, ZHUL_SYS_ transforme l'analyse d'architecture en expérience immersive où chaque décision de conception compte. Les développeurs peuvent explorer les bases de code existantes, créer de nouveaux nœuds architecturaux, établir des connexions sémantiques et recevoir des commentaires instantanés sur la santé du système.",
    },
    pt: {
      title: "ZHUL_SYS_",
      subtitle: "INICIALIZAÇÃO ARQUITETURA ELETRORETRO",
      step1: "PASSO 1/3: SELECIONAR MODELO",
      step2: "PASSO 2/3: CONECTAR REPOSITÓRIO",
      step3: "PASSO 3/3: INTERAÇÃO GRÁFICO",
      clickToInit: "CLIQUE_PARA_INICIALIZAR_ZHUL_SYS_",
      description1:
        "ZHUL_SYS_ é uma plataforma de vanguarda que transforma código fonte em gráficos arquiteturais inteligentes e visualizações interativas. Usa análise semântica avançada com IA para mapear automaticamente relações entre componentes, identificar padrões arquiteturais como hexagonal, DDD e SOLID, e gerar insights profundos sobre estrutura de software.",
      description2:
        "Através de uma experiência gaming com sistemas de pontuação, conquistas e níveis, ZHUL_SYS_ transforma análise de arquitetura em experiência imersiva onde cada decisão de design conta. Desenvolvedores podem explorar codebases existentes, criar novos nós arquiteturais, estabelecer conexões semânticas e receber feedback instantâneo sobre saúde do sistema.",
    },
  };

  const [currentLang, setCurrentLang] =
    useState<keyof typeof translations>("es");
  const t = translations[currentLang];

  // Home Screen (Step 0)
  if (currentStep === 0) {
    return (
      <div className="min-h-screen bg-black text-[#00FF41] font-mono flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-4xl">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-6xl font-black text-[#00FFFF] mb-4 tracking-wider terminal-flicker">
              ZHUL_SYS_
            </h1>
            <p className="text-xl text-[#00FF41] mb-2">ARCHITECTURE PLATFORM</p>
            <p className="text-sm text-[#00FF41]/70">
              Semantic code graph visualization and AI-powered analysis
            </p>
          </div>

          {/* Action Buttons */}
          <div className="text-center mb-12 space-y-4">
            <Button
              onClick={() => setCurrentStep(1)}
              className="bg-[#00FF41] text-black hover:bg-[#00FF41]/80 text-lg px-8 py-4 font-black tracking-wider hacker-glow mr-4"
            >
              <Plus className="h-5 w-5 mr-2" />
              NEW_PROJECT
            </Button>
            <Button
              onClick={() => (window.location.href = "/templates")}
              variant="outline"
              className="border-[#FF00FF] text-[#FF00FF] hover:bg-[#FF00FF]/10 text-lg px-8 py-4 font-black tracking-wider"
            >
              <Code className="h-5 w-5 mr-2" />
              TEMPLATE_MARKETPLACE
            </Button>
          </div>

          {/* Existing Projects Grid */}
          <div className="mb-8">
            <h2 className="text-2xl font-black text-[#00FFFF] mb-6 tracking-wider">
              EXISTING_PROJECTS
            </h2>

            {projects && projects.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {projects.map((project) => (
                  <Card
                    key={project.id}
                    className="bg-black border-2 border-[#00FF41] hover:border-[#00FFFF] cursor-pointer transition-all duration-300 hacker-glow hover:bg-[#00FF41]/5"
                    onClick={() => handleProjectSelect(project.id)}
                  >
                    <CardHeader className="pb-2">
                      <CardTitle className="text-[#00FF41] font-black tracking-wider text-lg">
                        {project.name}
                      </CardTitle>
                      <CardDescription className="text-[#00FF41]/70 text-sm">
                        {project.description || "No description"}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center justify-between">
                        <div className="text-xs text-[#00FFFF]">
                          ID: {project.id}
                        </div>
                        <div className="text-xs text-[#FFFF00]">
                          TEMPLATE:{" "}
                          {project.templateId?.toUpperCase() || "UNKNOWN"}
                        </div>
                      </div>
                      <div className="mt-3 flex items-center space-x-2">
                        <Play className="h-4 w-4 text-[#00FF41]" />
                        <span className="text-sm text-[#00FF41] font-bold">
                          LOAD_PROJECT
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 border-2 border-dashed border-[#00FF41]/30 rounded-lg">
                <FileText className="h-12 w-12 mx-auto text-[#00FF41]/50 mb-4" />
                <p className="text-[#00FF41]/70 mb-2">No projects found</p>
                <p className="text-sm text-[#00FF41]/50">
                  Create your first project to get started
                </p>
              </div>
            )}
          </div>

          {/* Language Selector */}
          <div className="text-center">
            <div className="text-sm text-[#00FF41]/70 mb-2">LANGUAGE:</div>
            <div className="flex justify-center space-x-2">
              {Object.keys(translations).map((lang) => (
                <Button
                  key={lang}
                  onClick={() =>
                    setCurrentLang(lang as keyof typeof translations)
                  }
                  variant={currentLang === lang ? "default" : "outline"}
                  className={`text-xs px-3 py-1 ${
                    currentLang === lang
                      ? "bg-[#00FF41] text-black"
                      : "border-[#00FF41] text-[#00FF41] hover:bg-[#00FF41]/10"
                  }`}
                >
                  {lang.toUpperCase()}
                </Button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Advanced FM synthesizer with pitch-changing effects
  const createFMSynth = () => {
    const audioContext = new (window.AudioContext ||
      (window as any).webkitAudioContext)();

    // Multiple operators for complex FM synthesis
    const carrier1 = audioContext.createOscillator();
    const carrier2 = audioContext.createOscillator();
    const modulator1 = audioContext.createOscillator();
    const modulator2 = audioContext.createOscillator();
    const subOsc = audioContext.createOscillator();

    // Gain nodes for mixing
    const carrierGain1 = audioContext.createGain();
    const carrierGain2 = audioContext.createGain();
    const modGain1 = audioContext.createGain();
    const modGain2 = audioContext.createGain();
    const subGain = audioContext.createGain();
    const masterGain = audioContext.createGain();

    // Filter for character
    const filter = audioContext.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(800, audioContext.currentTime);

    return {
      audioContext,
      carrier1,
      carrier2,
      modulator1,
      modulator2,
      subOsc,
      carrierGain1,
      carrierGain2,
      modGain1,
      modGain2,
      subGain,
      masterGain,
      filter,
    };
  };

  const playBootSound = () => {
    const {
      audioContext,
      carrier1,
      carrier2,
      modulator1,
      modulator2,
      subOsc,
      carrierGain1,
      carrierGain2,
      modGain1,
      modGain2,
      subGain,
      masterGain,
      filter,
    } = createFMSynth();

    // Complex FM routing
    modulator1.connect(modGain1);
    modulator2.connect(modGain2);
    modGain1.connect(carrier1.frequency);
    modGain2.connect(carrier2.frequency);

    carrier1.connect(carrierGain1);
    carrier2.connect(carrierGain2);
    subOsc.connect(subGain);

    carrierGain1.connect(filter);
    carrierGain2.connect(filter);
    subGain.connect(filter);
    filter.connect(masterGain);
    masterGain.connect(audioContext.destination);

    // Pitch-changing boot sequence
    const baseFreq = 80;
    carrier1.frequency.setValueAtTime(baseFreq, audioContext.currentTime);
    carrier2.frequency.setValueAtTime(baseFreq * 1.5, audioContext.currentTime);
    subOsc.frequency.setValueAtTime(baseFreq * 0.5, audioContext.currentTime);
    modulator1.frequency.setValueAtTime(
      baseFreq * 0.7,
      audioContext.currentTime,
    );
    modulator2.frequency.setValueAtTime(
      baseFreq * 1.3,
      audioContext.currentTime,
    );

    // Pitch sweeps with complex modulation
    carrier1.frequency.exponentialRampToValueAtTime(
      baseFreq * 0.6,
      audioContext.currentTime + 0.8,
    );
    carrier2.frequency.exponentialRampToValueAtTime(
      baseFreq * 0.9,
      audioContext.currentTime + 0.8,
    );
    subOsc.frequency.exponentialRampToValueAtTime(
      baseFreq * 0.3,
      audioContext.currentTime + 0.8,
    );

    // Modulation depth changes
    modGain1.gain.setValueAtTime(100, audioContext.currentTime);
    modGain1.gain.exponentialRampToValueAtTime(
      50,
      audioContext.currentTime + 0.4,
    );
    modGain1.gain.exponentialRampToValueAtTime(
      150,
      audioContext.currentTime + 0.8,
    );

    modGain2.gain.setValueAtTime(80, audioContext.currentTime);
    modGain2.gain.exponentialRampToValueAtTime(
      120,
      audioContext.currentTime + 0.8,
    );

    // Filter sweep
    filter.frequency.setValueAtTime(1200, audioContext.currentTime);
    filter.frequency.exponentialRampToValueAtTime(
      400,
      audioContext.currentTime + 0.8,
    );

    // Amplitude envelope
    masterGain.gain.setValueAtTime(0.5, audioContext.currentTime);
    masterGain.gain.exponentialRampToValueAtTime(
      0.01,
      audioContext.currentTime + 0.8,
    );

    // Start all oscillators
    [carrier1, carrier2, modulator1, modulator2, subOsc].forEach((osc) => {
      osc.start(audioContext.currentTime);
      osc.stop(audioContext.currentTime + 0.8);
    });
  };

  const playGlitchSound = () => {
    const {
      audioContext,
      carrier1,
      carrier2,
      modulator1,
      modulator2,
      subOsc,
      carrierGain1,
      carrierGain2,
      modGain1,
      modGain2,
      subGain,
      masterGain,
      filter,
    } = createFMSynth();

    // Complex FM routing for glitch
    modulator1.connect(modGain1);
    modulator2.connect(modGain2);
    modGain1.connect(carrier1.frequency);
    modGain2.connect(carrier2.frequency);

    carrier1.connect(carrierGain1);
    carrier2.connect(carrierGain2);
    subOsc.connect(subGain);

    carrierGain1.connect(filter);
    carrierGain2.connect(filter);
    subGain.connect(filter);
    filter.connect(masterGain);
    masterGain.connect(audioContext.destination);

    // Rapid pitch sweeps for glitch effect
    carrier1.type = "square";
    carrier2.type = "sawtooth";
    subOsc.type = "triangle";

    carrier1.frequency.setValueAtTime(440, audioContext.currentTime);
    carrier1.frequency.exponentialRampToValueAtTime(
      110,
      audioContext.currentTime + 0.05,
    );
    carrier1.frequency.exponentialRampToValueAtTime(
      880,
      audioContext.currentTime + 0.1,
    );

    carrier2.frequency.setValueAtTime(330, audioContext.currentTime);
    carrier2.frequency.exponentialRampToValueAtTime(
      165,
      audioContext.currentTime + 0.1,
    );

    modGain1.gain.setValueAtTime(200, audioContext.currentTime);
    modGain2.gain.setValueAtTime(150, audioContext.currentTime);

    filter.frequency.setValueAtTime(2000, audioContext.currentTime);
    filter.frequency.exponentialRampToValueAtTime(
      500,
      audioContext.currentTime + 0.1,
    );

    masterGain.gain.setValueAtTime(0.2, audioContext.currentTime);
    masterGain.gain.exponentialRampToValueAtTime(
      0.01,
      audioContext.currentTime + 0.1,
    );

    [carrier1, carrier2, modulator1, modulator2, subOsc].forEach((osc) => {
      osc.start(audioContext.currentTime);
      osc.stop(audioContext.currentTime + 0.1);
    });
  };

  // Cool pitch-bending hover sound
  const playPitchBendSound = () => {
    const {
      audioContext,
      carrier1,
      carrier2,
      modulator1,
      modulator2,
      subOsc,
      carrierGain1,
      carrierGain2,
      modGain1,
      modGain2,
      subGain,
      masterGain,
      filter,
    } = createFMSynth();

    // Smooth FM routing
    modulator1.connect(modGain1);
    modulator2.connect(modGain2);
    modGain1.connect(carrier1.frequency);
    modGain2.connect(carrier2.frequency);

    carrier1.connect(carrierGain1);
    carrier2.connect(carrierGain2);
    subOsc.connect(subGain);

    carrierGain1.connect(filter);
    carrierGain2.connect(filter);
    subGain.connect(filter);
    filter.connect(masterGain);
    masterGain.connect(audioContext.destination);

    // Smooth pitch bend with harmonic progression
    const baseFreq = 220;
    carrier1.frequency.setValueAtTime(baseFreq, audioContext.currentTime);
    carrier1.frequency.exponentialRampToValueAtTime(
      baseFreq * 1.5,
      audioContext.currentTime + 0.15,
    );
    carrier1.frequency.exponentialRampToValueAtTime(
      baseFreq * 2,
      audioContext.currentTime + 0.3,
    );

    carrier2.frequency.setValueAtTime(
      baseFreq * 1.25,
      audioContext.currentTime,
    );
    carrier2.frequency.exponentialRampToValueAtTime(
      baseFreq * 1.875,
      audioContext.currentTime + 0.3,
    );

    subOsc.frequency.setValueAtTime(baseFreq * 0.5, audioContext.currentTime);
    subOsc.frequency.exponentialRampToValueAtTime(
      baseFreq,
      audioContext.currentTime + 0.3,
    );

    // Modulation sweep
    modGain1.gain.setValueAtTime(50, audioContext.currentTime);
    modGain1.gain.exponentialRampToValueAtTime(
      150,
      audioContext.currentTime + 0.15,
    );
    modGain1.gain.exponentialRampToValueAtTime(
      25,
      audioContext.currentTime + 0.3,
    );

    // Filter sweep for character
    filter.frequency.setValueAtTime(800, audioContext.currentTime);
    filter.frequency.exponentialRampToValueAtTime(
      1600,
      audioContext.currentTime + 0.15,
    );
    filter.frequency.exponentialRampToValueAtTime(
      400,
      audioContext.currentTime + 0.3,
    );

    // Amplitude envelope
    masterGain.gain.setValueAtTime(0.15, audioContext.currentTime);
    masterGain.gain.exponentialRampToValueAtTime(
      0.01,
      audioContext.currentTime + 0.3,
    );

    [carrier1, carrier2, modulator1, modulator2, subOsc].forEach((osc) => {
      osc.start(audioContext.currentTime);
      osc.stop(audioContext.currentTime + 0.3);
    });
  };

  // Step 1
  if (currentStep === 1) {
    return <ProjectSetup onComplete={(id, t) => {
      setSelectedProjectId(id);
      setSelectedTemplate(t);
      setCurrentStep(2);
    }} />;
  }
  // Step 2: Repository Connection
  if (currentStep === 2) {
    return (
      <div className="min-h-screen bg-black text-[#00FF41] font-mono flex items-center justify-center p-4">
        <Card className="w-full max-w-2xl bg-black border-[#00FF41] border-2">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl text-[#00FFFF] tracking-wider">
              CONNECT REPOSITORY
            </CardTitle>
            <CardDescription className="text-[#00FF41]">
              Template: {selectedTemplate?.name}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="text-center text-[#FFFF00] mb-6">
              STEP 2/3: LOAD CODEBASE
            </div>

            <Tabs defaultValue="github" className="w-full">
              <TabsList className="grid w-full grid-cols-3 bg-black border border-[#00FF41]">
                <TabsTrigger
                  value="github"
                  className="text-[#00FF41] data-[state=active]:bg-[#00FF41] data-[state=active]:text-black"
                >
                  GitHub
                </TabsTrigger>
                <TabsTrigger
                  value="upload"
                  className="text-[#00FF41] data-[state=active]:bg-[#00FF41] data-[state=active]:text-black"
                >
                  Upload
                </TabsTrigger>
                <TabsTrigger
                  value="empty"
                  className="text-[#00FF41] data-[state=active]:bg-[#00FF41] data-[state=active]:text-black"
                >
                  Empty
                </TabsTrigger>
              </TabsList>

              <TabsContent value="github" className="space-y-4">
                <div className="space-y-3">
                  <Input
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    placeholder="https://github.com/user/repo"
                    className="bg-black border-[#00FF41] text-[#00FF41] placeholder:text-[#00FF41]/50"
                  />
                  <Input
                    value={githubToken}
                    onChange={(e) => setGithubToken(e.target.value)}
                    placeholder="GitHub Token (required for private repos)"
                    type="password"
                    className="bg-black border-[#FF00FF] text-[#FF00FF] placeholder:text-[#FF00FF]/50"
                  />
                  <div className="text-[#00FF41]/70 text-xs">
                    For private repositories, create a Personal Access Token at:
                    <br />
                    https://github.com/settings/tokens
                  </div>
                  <Button
                    onClick={handleGitHubConnect}
                    disabled={!githubUrl}
                    className="w-full bg-[#00FF41] text-black hover:bg-[#00FF41]/80"
                  >
                    <Github className="h-4 w-4 mr-2" />
                    CONNECT_REPOSITORY
                  </Button>
                </div>
              </TabsContent>

              <TabsContent value="upload" className="space-y-4">
                <div className="border-2 border-dashed border-[#00FF41] rounded-lg p-8 text-center">
                  <Upload className="h-12 w-12 text-[#00FF41] mx-auto mb-4" />
                  <div className="text-[#00FF41] mb-2">
                    Drop files here or click to upload
                  </div>
                  <div className="text-[#00FF41]/70 text-sm">
                    Supports .zip, .tar.gz, individual files
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="empty" className="space-y-4">
                <div className="text-center py-8">
                  <FileText className="h-12 w-12 text-[#00FF41] mx-auto mb-4" />
                  <div className="text-[#00FF41] mb-4">
                    Start with empty architecture
                  </div>
                  <Button
                    onClick={() => setCurrentStep(3)}
                    className="bg-[#00FF41] text-black hover:bg-[#00FF41]/80"
                  >
                    CONTINUE
                  </Button>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Step 3: Main Interface
  return (
    <TemplateProvider projectId={selectedProjectId}>
      <div className="min-h-screen bg-black text-[#00FF41] font-mono flex flex-col">
      {/* TGA Header */}
      <div className="border-b-2 border-[#00FF41] bg-black p-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-4">
            <div className="text-[#00FFFF] font-bold text-lg tracking-wider">
              ZHUL_SYS_
            </div>
            <div className="text-[#FFFF00] text-sm">
              {selectedTemplate?.name} |{" "}
              {repositoryConnected ? "REPO_CONNECTED" : "MANUAL_MODE"}
            </div>
          </div>

          <div className="flex items-center space-x-2 relative">
            {/* MENU Dropdown */}
            <div className="relative">
              <Button
                onClick={() => setShowMenu(!showMenu)}
                variant="outline"
                className="border-[#FF00FF] text-[#FF00FF] hover:bg-[#FF00FF]/10 h-8"
              >
                <Menu className="h-3 w-3 mr-1" />
                MENU
              </Button>

              {showMenu && (
                <div className="absolute top-full right-0 mt-1 w-48 bg-black border-2 border-[#FF00FF] rounded z-50">
                  <div className="p-2 space-y-1">
                    <Button
                      onClick={() => {
                        setShowMenu(false);
                        setPendingNodePosition({ x: Math.random() * 400, y: Math.random() * 300 });
                        setShowNodeForm(true);
                        toast({
                          title: "🎯 NODE_CREATOR",
                          description: "Create new architecture node"
                        });
                      }}
                      disabled={!selectedProjectId}
                      className="w-full bg-[#00FF41] text-black hover:bg-[#00FF41]/80 h-8 text-xs"
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      CREATE_NODE
                    </Button>
                    <Button
                      onClick={() => {
                        setShowMenu(false);
                        setShowAIAssistant(true);
                        toast({
                          title: "🧠 AI_CHAT_ACTIVATED",
                          description: "AI Assistant ready for architecture requests"
                        });
                      }}
                      disabled={!selectedProjectId}
                      className="w-full bg-[#FF00FF] text-black hover:bg-[#FF0FF]/80 h-8 text-xs"
                    >
                      <Brain className="h-3 w-3 mr-1" />
                      AI_ASSISTANT
                    </Button>
                    <Button
                      onClick={() => {
                        setShowMenu(false);
                        setShowAdvancedInsights(true);
                        toast({
                          title: "🔍 ANALYSIS_MODE",
                          description: "Advanced AI insights activated"
                        });
                      }}
                      disabled={!selectedProjectId}
                      className="w-full bg-[#00FFFF] text-black hover:bg-[#00FFFF]/80 h-8 text-xs"
                    >
                      <Sparkles className="h-3 w-3 mr-1" />
                      AI_ANALYSIS
                    </Button>
                    <Button
                      onClick={async () => {
                        setShowMenu(false);
                        await handleRequirementRefresh();
                      }}
                      disabled={!selectedProjectId}
                      className="w-full bg-[#FFFF00] text-black hover:bg-[#FFFF00]/80 h-8 text-xs"
                    >
                      <Upload className="h-3 w-3 mr-1" />
                      REFRESH_DOCS
                    </Button>
                  </div>
                </div>
              )}
            </div>

            <Button
              onClick={() => {
                setPendingNodePosition({ x: Math.random() * 400, y: Math.random() * 300 });
                setShowNodeForm(true);
                toast({
                  title: "🎯 NODE_CREATOR",
                  description: "Create new architecture node"
                });
              }}
              disabled={!selectedProjectId}
              className="bg-[#00FF41] text-black hover:bg-[#00FF41]/80 h-8"
            >
              <Plus className="h-3 w-3 mr-1" />
              ADD_NODE
            </Button>
            <Button
              onClick={() => {
                setShowAIAssistant(true);
                toast({
                  title: "🧠 AI_CHAT_ACTIVATED",
                  description: "AI Assistant ready for architecture requests"
                });
              }}
              disabled={!selectedProjectId}
              className="bg-[#FF00FF] text-black hover:bg-[#FF00FF]/80 h-8"
            >
              <Brain className="h-3 w-3 mr-1" />
              AI_CHAT
            </Button>
            <Button
              onClick={() => {
                setShowAdvancedInsights(true);
                toast({
                  title: "🔍 INSIGHTS_MODE",
                  description: "Advanced AI insights activated"
                });
              }}
              disabled={!selectedProjectId}
              variant="outline"
              className="border-[#00FFFF] text-[#00FFFF] hover:bg-[#00FFFF]/10 h-8"
            >
              <Sparkles className="h-3 w-3 mr-1" />
              INSIGHTS
            </Button>
          </div>
        </div>
      </div>

      <div className="flex flex-1 flex-col xl:flex-row">
        {/* File Tree Sidebar */}
        <div className="w-full xl:w-80 border-b-2 xl:border-b-0 xl:border-r-2 border-[#00FF41] bg-black p-4">
          <h2 className="text-[#00FF41] font-bold text-lg mb-3 tracking-wider">
            {viewMode === "folder" ? "FILE_TREE" : "ARCHITECTURE"}
          </h2>
          <Select
            value={viewMode}
            onValueChange={(v) =>
              setViewMode(v as 'folder' | 'layered' | 'hexagonal')
            }
          >
            <SelectTrigger className="w-full mb-3 bg-black border-[#00FF41] text-[#00FF41]">
              <SelectValue placeholder="View" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="folder">Folder</SelectItem>
              <SelectItem value="layered">Layered</SelectItem>
              <SelectItem value="hexagonal">Hexagonal</SelectItem>
            </SelectContent>
          </Select>

          <div className="space-y-1 max-h-96 overflow-y-auto">
            {displayedTree.length > 0 ? (
              <ArchitectureTree
                tree={displayedTree}
                onSelectNode={handleTreeNodeSelect}
              />
            ) : (
              <div className="text-center py-8 text-[#00FF41]/70">
                <FileText className="h-8 w-8 mx-auto mb-2" />
                <div className="text-sm">No files loaded</div>
                <div className="text-xs mt-1">
                  Connect repository or upload files
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Main Graph Area */}
        <div className="flex-1 min-h-96">
          {selectedProjectId ? (
            <SmartGraphEditor
              projectId={selectedProjectId}
              onNodeSelect={handleNodeSelect}
              graphData={graphData}
              focusNodeId={focusNodeId || undefined}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="text-[#FF00FF] text-2xl font-bold mb-4 tracking-wider">
                  INITIALIZING_TERMINAL...
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar - Node Properties */}
        <RightSidebar
          selectedNode={selectedNode}
          onNodeUpdate={handleNodeUpdate}
        />
      </div>
      {showNodeForm && (
        <NodeCreationForm
          isOpen={showNodeForm}
          onClose={() => setShowNodeForm(false)}
          onSubmit={handleNodeCreation}
          position={pendingNodePosition || { x: 0, y: 0 }}
        />
      )}

      {selectedNode?.data?.filePath && (
        <ProjectFileViewer
          projectId={selectedProjectId}
          path={selectedNode.data.filePath}
          line={selectedNode.data.sourceMap?.line}
          open={showFileViewer}
          onClose={() => setShowFileViewer(false)}
        />
      )}

      {/* AI Architect Component */}
      {showAIAssistant && selectedProjectId && selectedTemplate && (
        <AIArchitect
          isOpen={showAIAssistant}
          onClose={() => setShowAIAssistant(false)}
          selectedProjectId={selectedProjectId}
        />
      )}

      {/* Advanced Insights Dialog */}
      {showAdvancedInsights && selectedProjectId && (
        <AdvancedAIInsights
          projectId={selectedProjectId}
          isOpen={showAdvancedInsights}
          onClose={() => setShowAdvancedInsights(false)}
        />
      )}
      </div>
    </TemplateProvider>
  );
}
