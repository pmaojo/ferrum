import { useMemo } from 'react';
import { GraphEditor } from './GraphEditor';
import { useKthuluStatus } from '@/hooks/use-graph';
import type {
  GraphNode as GraphNodeType,
  GraphEdge as GraphEdgeType,
} from '@shared/schema';
import type { GraphNodeData } from '@/types/graph';
import { Node } from 'reactflow';

interface SmartGraphEditorProps {
  graphData?: { nodes: GraphNodeType[]; edges: GraphEdgeType[] };
  projectId: string;
  onNodeSelect: (node: Node<GraphNodeData> | null) => void;
  focusNodeId?: string;
}

/**
 * @kthulu:extend - Smart graph editor that automatically detects Kthulu projects
 * and uses semantic visualization for enhanced architecture understanding
 */
export function SmartGraphEditor(props: SmartGraphEditorProps) {
  const { data: kthuluStatus } = useKthuluStatus(props.projectId);

  // Detect if this is a Kthulu project with semantic architecture
  const useSemanticVisualization = useMemo(() => {
    // Check if Kthulu is connected
    if (kthuluStatus?.isConnected) {
      return true;
    }

    // Check if nodes contain semantic Kthulu types
    const semanticTypes = [
      'module',
      'usecase',
      'adapter',
      'port',
      'domainentity',
      'domainevent',
    ];
    const hasSemanticNodes = props.graphData?.nodes?.some((node) =>
      semanticTypes.includes(node.type.toLowerCase())
    );

    if (hasSemanticNodes) {
      return true;
    }

    // Check if nodes have OWL metadata
    const hasOwlMetadata = props.graphData?.nodes?.some(
      (node) =>
        node.metadata &&
        ((node.metadata as any).owlClass ||
          (node.metadata as any).semantic ||
          (node.metadata as any).moduleNamespace)
    );

    return hasOwlMetadata;
  }, [kthuluStatus, props.graphData]);

  return (
    <GraphEditor
      {...props}
      focusNodeId={props.focusNodeId}
      useSemanticVisualization={useSemanticVisualization}
    />
  );
}
