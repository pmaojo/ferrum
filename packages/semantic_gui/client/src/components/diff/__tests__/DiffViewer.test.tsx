import React from 'react';
import { render, screen } from '@testing-library/react';
import DiffViewer, { FileDiff } from '../DiffViewer';

describe('DiffViewer', () => {
  it('renders old and new content', () => {
    const diff: FileDiff = {
      filePath: 'file.txt',
      oldContent: 'old line',
      newContent: 'new line',
    };

    render(<DiffViewer diff={diff} />);

    expect(screen.getByText('old line')).toBeInTheDocument();
    expect(screen.getByText('new line')).toBeInTheDocument();
  });
});
