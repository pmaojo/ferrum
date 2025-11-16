import DiffViewer, { FileDiff } from './DiffViewer';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface DiffPreviewProps {
  diffs: FileDiff[];
  onJumpToRequirement?: (id: string) => void;
}

export function DiffPreview({ diffs, onJumpToRequirement }: DiffPreviewProps) {
  if (!diffs.length) {
    return <div className="text-center text-[#00FF41]/70">NO_DIFFS_TO_DISPLAY</div>;
  }

  return (
    <div className="space-y-6">
      {diffs.map((diff) => (
        <Card key={diff.filePath} className="bg-black border-2 border-[#00FF41]">
          <CardHeader>
            <CardTitle
              className="text-[#00FF41] font-black flex justify-between items-center"
              title={diff.requirementText}
            >
              {diff.filePath}
              {diff.requirementId && (
                <button
                  className="ml-2 text-xs underline"
                  onClick={() =>
                    onJumpToRequirement
                      ? onJumpToRequirement(diff.requirementId as string)
                      : window.dispatchEvent(
                          new CustomEvent("jump-to-requirement", {
                            detail: diff.requirementId,
                          }),
                        )
                  }
                  title="Jump to requirement"
                >
                  Jump
                </button>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DiffViewer diff={diff} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function render(diffs: FileDiff[]) {
  return <DiffPreview diffs={diffs} />;
}

export default DiffPreview;
