import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import CommandPalette from '../CommandPalette';
import { useCommandPalette } from '@/hooks/useCommandPalette';
import { useQuery } from '@tanstack/react-query';
import { kthuluService } from '@/services/kthuluService';
import { backgroundTaskManager } from '@/services/backgroundTaskManager';

jest.mock('@/hooks/useCommandPalette', () => ({
  useCommandPalette: jest.fn(),
}));
jest.mock('@tanstack/react-query', () => ({
  useQuery: jest.fn(),
}));
jest.mock('@/services/kthuluService', () => ({
  kthuluService: { executeCommand: jest.fn() },
}));
jest.mock('@/services/backgroundTaskManager', () => ({
  backgroundTaskManager: { submitTask: jest.fn() },
}));

expect.extend(toHaveNoViolations);

describe('CommandPalette', () => {
  const mockOperations = {
    operations: [
      {
        key: 'plan',
        label: 'Plan Architecture',
        description: 'Plan the graph',
      },
    ],
  };

  beforeEach(() => {
    (useCommandPalette as jest.Mock).mockReturnValue({
      open: true,
      setOpen: jest.fn(),
    });
    (useQuery as jest.Mock).mockReturnValue({ data: mockOperations });
  });

  it('has no accessibility violations', async () => {
    render(<CommandPalette projectId="123" />);
    const results = await axe(document.body);
    expect(results).toHaveNoViolations();
  });

  it('executes command when selected', () => {
    const setOpen = jest.fn();
    (useCommandPalette as jest.Mock).mockReturnValue({ open: true, setOpen });
    (useQuery as jest.Mock).mockReturnValue({ data: mockOperations });
    const submitTask = backgroundTaskManager.submitTask as jest.Mock;
    const exec = kthuluService.executeCommand as jest.Mock;
    submitTask.mockResolvedValue('1');
    exec.mockResolvedValue({});

    render(<CommandPalette projectId="123" />);

    const item = screen.getByText('Plan Architecture');
    fireEvent.mouseDown(item);

    expect(submitTask).toHaveBeenCalled();
    expect(exec).toHaveBeenCalledWith('123', 'plan', []);
    expect(setOpen).toHaveBeenCalledWith(false);
  });

  it('renders form for args and executes with provided values', async () => {
    const opWithArgs = {
      key: 'build',
      label: 'Build',
      argsSchema: {
        type: 'object',
        properties: { path: { type: 'string' } },
        required: ['path'],
      },
    };
    (useCommandPalette as jest.Mock).mockReturnValue({
      open: true,
      setOpen: jest.fn(),
    });
    (useQuery as jest.Mock).mockReturnValue({
      data: { operations: [opWithArgs] },
    });
    const submitTask = backgroundTaskManager.submitTask as jest.Mock;
    const exec = kthuluService.executeCommand as jest.Mock;
    submitTask.mockResolvedValue('1');
    exec.mockResolvedValue({});

    render(<CommandPalette projectId="123" />);

    fireEvent.mouseDown(screen.getByText('Build'));

    const input = await screen.findByLabelText('path');
    const run = screen.getByText('Execute') as HTMLButtonElement;
    expect(run).toBeDisabled();
    fireEvent.change(input, { target: { value: 'src' } });
    expect(run).not.toBeDisabled();
    fireEvent.click(run);

    expect(submitTask).toHaveBeenCalled();
    expect(exec).toHaveBeenCalledWith('123', 'build', ['--path', 'src']);
  });
});
