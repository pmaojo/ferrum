import React, { useEffect, useState } from 'react';
import ProjectFileViewer from './ProjectFileViewer';
import type { FileDiff } from '@/components/diff/DiffViewer';

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
  content?: string;
  newContent?: string;
}

interface FileExplorerProps {
  projectId: string;
}

export function FileExplorer({ projectId }: FileExplorerProps) {
  const [tree, setTree] = useState<FileNode[]>([]);
  const [selected, setSelected] = useState<FileNode | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    fetch(`/api/projects/${projectId}/files`)
      .then((r) => r.json())
      .then((data) => setTree(data || []));
  }, [projectId]);

  const handleSelect = (node: FileNode) => {
    if (node.type === 'file') {
      setSelected(node);
      setOpen(true);
    }
  };

  return (
    <div>
      {tree.map((n) => (
        <FileNodeView key={n.path} node={n} onSelect={handleSelect} />
      ))}
      {selected && (
        <ProjectFileViewer
          projectId={projectId}
          path={selected.path}
          open={open}
          onClose={() => setOpen(false)}
          diff={
            selected.newContent
              ? ({
                  filePath: selected.path,
                  oldContent: selected.content || '',
                  newContent: selected.newContent,
                } as FileDiff)
              : undefined
          }
        />
      )}
    </div>
  );
}

interface FileNodeViewProps {
  node: FileNode;
  depth?: number;
  onSelect: (node: FileNode) => void;
}

const FileNodeView = ({ node, depth = 0, onSelect }: FileNodeViewProps) => {
  const [expanded, setExpanded] = useState(false);
  const paddingLeft = depth * 16;

  if (node.type === 'directory') {
    return (
      <div style={{ paddingLeft }}>
        <div
          className="cursor-pointer font-medium"
          onClick={() => setExpanded((e) => !e)}
        >
          {node.name}
        </div>
        {expanded &&
          node.children?.map((child) => (
            <FileNodeView
              key={child.path}
              node={child}
              depth={depth + 1}
              onSelect={onSelect}
            />
          ))}
      </div>
    );
  }

  return (
    <div
      style={{ paddingLeft }}
      className="cursor-pointer"
      onClick={() => onSelect(node)}
    >
      {node.name}
    </div>
  );
};

export default FileExplorer;
