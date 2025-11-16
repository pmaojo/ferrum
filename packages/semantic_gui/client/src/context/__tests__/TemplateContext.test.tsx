import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TemplateProvider, useTemplate } from '../TemplateContext';

const mockProject = { templateId: 'test-template' };

// Mock the useProject hook
jest.mock('@/hooks/use-graph', () => ({
  useProject: jest.fn(() => ({
    data: mockProject,
  })),
}));

// Mock fetch
global.fetch = jest.fn();

const TestComponent = () => {
  const { currentTemplate, nodeTypes, configSchema, isLoading } = useTemplate();

  if (isLoading) return <div>Loading...</div>;
  if (!currentTemplate) return <div>No template</div>;

  return (
    <div>
      <div data-testid="template-name">{currentTemplate.name}</div>
      <div data-testid="node-types-count">{nodeTypes.length}</div>
      <div data-testid="config-schema-count">
        {Object.keys(configSchema || {}).length}
      </div>
    </div>
  );
};

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <TemplateProvider projectId="test-project">{component}</TemplateProvider>
    </QueryClientProvider>
  );
};

describe('TemplateContext', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
  });

  it('should provide template data correctly', async () => {
    const mockTemplate = {
      id: 'test-template',
      name: 'Test Template Architecture',
      nodeTypes: [
        {
          type: 'domain',
          label: 'Domain',
          description: 'Core domain logic',
          template: 'export class {name}Domain {}',
          bestPractices: ['Single responsibility'],
        },
        {
          type: 'port',
          label: 'Port',
          description: 'Interface contract',
          template: 'export interface {name}Port {}',
          bestPractices: ['Interface segregation'],
        },
      ],
      metadata: {
        configSchema: {
          type: 'object',
          required: ['projectName'],
          properties: {
            projectName: { type: 'string', title: 'Project Name' },
          },
        },
      },
    };

    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockTemplate,
    });

    renderWithProviders(<TestComponent />);

    // Initially should show loading
    expect(screen.getByText('Loading...')).toBeInTheDocument();

    // Wait for template to load
    await waitFor(() => {
      expect(screen.getByTestId('template-name')).toHaveTextContent(
        'Test Template Architecture'
      );
    });

    expect(fetch).toHaveBeenCalledWith(
      `/api/v1/templates/${mockProject.templateId}`,
      expect.any(Object)
    );

    expect(screen.getByTestId('node-types-count')).toHaveTextContent('2');
    expect(screen.getByTestId('config-schema-count')).toHaveTextContent('1');
  });

  it('should handle template loading error', async () => {
    (fetch as jest.Mock).mockRejectedValueOnce(new Error('Failed to fetch'));

    renderWithProviders(<TestComponent />);

    await waitFor(() => {
      expect(screen.getByText('No template')).toBeInTheDocument();
    });
  });

  it('should transform nodeTypes correctly', async () => {
    const mockTemplate = {
      id: 'test-template',
      name: 'Test Template',
      nodeTypes: [
        {
          type: 'component',
          description: 'Test component',
          // Missing label - should be auto-generated
        },
      ],
      metadata: {},
    };

    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockTemplate,
    });

    const TestNodeTypes = () => {
      const { nodeTypes } = useTemplate();
      return (
        <div>
          {nodeTypes.map((nt, i) => (
            <div key={i}>
              <span data-testid={`node-type-${i}-value`}>{nt.value}</span>
              <span data-testid={`node-type-${i}-label`}>{nt.label}</span>
            </div>
          ))}
        </div>
      );
    };

    renderWithProviders(<TestNodeTypes />);

    await waitFor(() => {
      expect(screen.getByTestId('node-type-0-value')).toHaveTextContent(
        'component'
      );
      expect(screen.getByTestId('node-type-0-label')).toHaveTextContent(
        'Component'
      );
    });
  });
});
