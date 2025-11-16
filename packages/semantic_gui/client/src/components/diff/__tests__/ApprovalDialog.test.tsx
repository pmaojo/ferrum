import { render, screen, fireEvent } from '@testing-library/react';
import { ApprovalDialog } from '../ApprovalDialog';
import type { FileDiff } from '../DiffViewer';

describe('ApprovalDialog', () => {
  const diffs: FileDiff[] = [
    { filePath: 'file.txt', oldContent: 'old', newContent: 'new' },
  ];

  it('renders apply mode options and calls onApply', () => {
    const onApply = jest.fn();
    render(
      <ApprovalDialog open diffs={diffs} onClose={() => {}} onApply={onApply} />
    );
    fireEvent.click(screen.getByLabelText('Write'));
    fireEvent.click(screen.getByText('Apply'));
    expect(onApply).toHaveBeenCalledWith('write');
  });
});
