import React, { useState } from 'react';
import ReactDiffViewer from 'react-diff-viewer';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';

export interface FileDiff {
  filePath: string;
  oldContent: string;
  newContent: string;
  requirementId?: string;
  requirementText?: string;
}

interface DiffViewerProps {
  diff: FileDiff;
}

const highlightSyntax = (str: string) => (
  <pre
    className="whitespace-pre-wrap"
    dangerouslySetInnerHTML={{ __html: hljs.highlightAuto(str).value }}
  />
);

export function DiffViewer({ diff }: DiffViewerProps) {
  const [view, setView] = useState<'split' | 'inline'>('split');

  return (
    <div>
      <div className="flex justify-end mb-2">
        <ToggleGroup
          type="single"
          value={view}
          onValueChange={(v) => v && setView(v as 'split' | 'inline')}
          size="sm"
        >
          <ToggleGroupItem value="inline">Inline</ToggleGroupItem>
          <ToggleGroupItem value="split">Split</ToggleGroupItem>
        </ToggleGroup>
      </div>
      <ReactDiffViewer
        oldValue={diff.oldContent}
        newValue={diff.newContent}
        splitView={view === 'split'}
        renderContent={highlightSyntax}
      />
    </div>
  );
}

export default DiffViewer;
