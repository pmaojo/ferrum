import { FolderOpen, File } from 'lucide-react';
import React from 'react';

export interface ArchitectureTreeNode {
  name: string;
  type: 'file' | 'folder';
  path: string;
  nodeId?: string;
  children?: ArchitectureTreeNode[];
}

interface ArchitectureTreeProps {
  tree: ArchitectureTreeNode[];
  onSelectNode?: (node: ArchitectureTreeNode) => void;
}

export function ArchitectureTree({
  tree,
  onSelectNode,
}: ArchitectureTreeProps) {
  const renderNodes = (
    nodes: ArchitectureTreeNode[],
    level = 0
  ): React.ReactNode => {
    return nodes.map((node) => (
      <div key={node.path} style={{ marginLeft: level * 16 }}>
        <div
          className="flex items-center space-x-2 py-1 px-2 hover:bg-[#00FF41]/10 cursor-pointer rounded"
          onClick={() => onSelectNode && onSelectNode(node)}
        >
          {node.type === 'folder' ? (
            <FolderOpen className="h-4 w-4 text-[#00FFFF]" />
          ) : (
            <File className="h-4 w-4 text-[#00FF41]" />
          )}
          <span className="text-[#00FF41] text-sm font-mono">{node.name}</span>
        </div>
        {node.children && renderNodes(node.children, level + 1)}
      </div>
    ));
  };

  return <div>{renderNodes(tree)}</div>;
}
