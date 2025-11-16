import { useEffect, useState } from 'react';
import { useGraphRefresh } from '@/hooks/use-graph';
import { DiffPreview, FileDiff } from '@/components/diff';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface Props {
  projectId: string;
  moduleName: string;
  open: boolean;
  onClose: () => void;
}

export function ModuleScaffoldDialog({
  projectId,
  moduleName,
  open,
  onClose,
}: Props) {
  const [diffs, setDiffs] = useState<FileDiff[]>([]);
  const { mutateAsync: refreshGraph } = useGraphRefresh();

  useEffect(() => {
    if (!open) return;
    fetch(`/api/projects/${projectId}/scaffold/module`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: moduleName }),
    })
      .then((r) => r.json())
      .then((data) => setDiffs(data.diffs || []));
  }, [open, projectId, moduleName]);

  const apply = async () => {
    await fetch(`/api/projects/${projectId}/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        files: diffs.map((d) => ({ path: d.filePath, content: d.newContent })),
      }),
    });
    await refreshGraph(projectId);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Module Scaffold</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 max-h-[60vh] overflow-auto">
          <DiffPreview diffs={diffs} />
        </div>
        <DialogFooter>
          <Button onClick={apply}>Apply</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ModuleScaffoldDialog;
