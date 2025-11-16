import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProjectFileViewer } from '../ProjectFileViewer';

describe('ProjectFileViewer', () => {
  beforeEach(() => {
    (global.fetch as unknown as jest.Mock) = jest.fn(() =>
      Promise.resolve({ text: () => Promise.resolve('original') })
    ) as any;
  });

  it('loads and displays file content and shows diff on apply', async () => {
    render(
      <ProjectFileViewer
        projectId="1"
        path="file.txt"
        open={true}
        onClose={() => {}}
      />
    );

    const editor = await screen.findByRole('textbox');
    await userEvent.clear(editor);
    await userEvent.type(editor, 'changed');
    await userEvent.click(screen.getByText(/Apply Changes/i));
    await screen.findByText('changed');
  });

  it('fetches new file when path changes', async () => {
    (fetch as jest.Mock)
      .mockResolvedValueOnce({ text: () => Promise.resolve('first') })
      .mockResolvedValueOnce({ text: () => Promise.resolve('second') });

    const { rerender } = render(
      <ProjectFileViewer
        projectId="1"
        path="first.txt"
        open={true}
        onClose={() => {}}
      />
    );
    await screen.findByText('first');

    rerender(
      <ProjectFileViewer
        projectId="1"
        path="second.txt"
        open={true}
        onClose={() => {}}
      />
    );
    await screen.findByText('second');
  });
});
