import { render, screen, fireEvent } from '@testing-library/react';
import { render as renderDiffPreview } from '../DiffPreview';
import type { FileDiff } from '../DiffViewer';

describe('DiffPreview', () => {
  it('renders file path', () => {
    const diffs: FileDiff[] = [
      { filePath: 'file.txt', oldContent: 'old', newContent: 'new' },
    ];

    render(renderDiffPreview(diffs));
    expect(screen.getByText('file.txt')).toBeInTheDocument();
  });

  it('handles empty diffs', () => {
    render(renderDiffPreview([]));
    expect(screen.getByText(/NO_DIFFS_TO_DISPLAY/i)).toBeInTheDocument();
  });

  it('renders jump to requirement', () => {
    const diffs: FileDiff[] = [
      {
        filePath: 'file.ts',
        oldContent: 'old',
        newContent: 'new',
        requirementId: 'REQ-1',
        requirementText: 'Requirement text',
      },
    ];
    const handler = jest.fn();
    window.addEventListener('jump-to-requirement', handler);
    render(renderDiffPreview(diffs));
    const btn = screen.getByText('Jump');
    fireEvent.click(btn);
    expect(handler).toHaveBeenCalled();
    window.removeEventListener('jump-to-requirement', handler);
  });
});
