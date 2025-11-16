import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import DiffPreview, { type FileDiff } from './DiffPreview';

export interface ApprovalDialogProps {
  open: boolean;
  diffs: FileDiff[];
  onClose: () => void;
  onApply: (mode: 'diff' | 'write' | 'pr') => void;
}

export function ApprovalDialog({ open, diffs, onClose, onApply }: ApprovalDialogProps) {
  const [mode, setMode] = useState<'diff' | 'write' | 'pr'>('diff');

  return (
    <Dialog open={open} onOpenChange={(v) => (!v ? onClose() : undefined)}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Review Changes</DialogTitle>
        </DialogHeader>
        <div className="max-h-[60vh] overflow-y-auto pr-2">
          <DiffPreview diffs={diffs} />
        </div>
        <RadioGroup
          value={mode}
          onValueChange={(v) => setMode(v as 'diff' | 'write' | 'pr')}
          className="flex space-x-4 mt-4"
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="diff" id="mode-diff" />
            <Label htmlFor="mode-diff">Diff</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="write" id="mode-write" />
            <Label htmlFor="mode-write">Write</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="pr" id="mode-pr" />
            <Label htmlFor="mode-pr">PR</Label>
          </div>
        </RadioGroup>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => onApply(mode)}>Apply</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ApprovalDialog;
