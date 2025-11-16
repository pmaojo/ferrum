import React, { useEffect, useState, useRef } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { javascript } from '@codemirror/lang-javascript';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import DiffViewer, { FileDiff } from '@/components/diff/DiffViewer';

interface ProjectFileViewerProps {
  projectId: string;
  path: string;
  line?: number;
  open: boolean;
  onClose: () => void;
  diff?: FileDiff | null;
}

export function ProjectFileViewer({
  projectId,
  path,
  line,
  open,
  onClose,
  diff: initialDiff,
}: ProjectFileViewerProps) {
  const [content, setContent] = useState('');
  const [editedContent, setEditedContent] = useState('');
  const [diff, setDiff] = useState<FileDiff | null>(initialDiff || null);
  const editorRef = useRef<any>(null);

  useEffect(() => {
    setDiff(initialDiff || null);
  }, [initialDiff]);

  useEffect(() => {
    if (!open || !path || initialDiff) return;
    fetch(`/api/projects/${projectId}/files/${encodeURIComponent(path)}`)
      .then((r) => r.text())
      .then((text) => {
        setContent(text);
        setEditedContent(text);
        setDiff(null);
      });
  }, [projectId, path, open, initialDiff]);

  useEffect(() => {
    if (!open || !line || !editorRef.current) return;
    const view = editorRef.current;
    const lineInfo = view.state.doc.line(line);
    view.dispatch({
      selection: { anchor: lineInfo.from },
      scrollIntoView: true,
    });
  }, [open, line]);

  const applyChanges = () => {
    setDiff({ filePath: path, oldContent: content, newContent: editedContent });
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{path}</DialogTitle>
        </DialogHeader>
        {diff ? (
          <DiffViewer diff={diff} />
        ) : (
          <>
            <CodeMirror
              value={editedContent}
              height="16rem"
              extensions={[javascript()]}
              onCreateEditor={(view) => (editorRef.current = view)}
              onChange={(value) => setEditedContent(value)}
            />
            <div className="mt-4 flex justify-end">
              <Button onClick={applyChanges}>Apply Changes</Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default ProjectFileViewer;
