import { render, screen } from '@testing-library/react';
import TracePanel, { Trace } from '../TracePanel';

describe('TracePanel', () => {
  it('shows loading state', () => {
    render(<TracePanel isLoading />);
    expect(screen.getByText(/LOADING_TRACES/i)).toBeInTheDocument();
  });

  it('shows error state', () => {
    render(<TracePanel error="boom" />);
    expect(screen.getByText(/ERROR: boom/i)).toBeInTheDocument();
  });

  it('shows empty state', () => {
    render(<TracePanel traces={[]} />);
    expect(screen.getByText(/NO_TRACES_AVAILABLE/i)).toBeInTheDocument();
  });

  it('renders traces', () => {
    const traces: Trace[] = [{ id: '1', message: 'hello' }];
    render(<TracePanel traces={traces} />);
    expect(screen.getByText('hello')).toBeInTheDocument();
  });
});
