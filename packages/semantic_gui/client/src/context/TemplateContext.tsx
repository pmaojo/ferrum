import { createContext, useContext, useMemo } from 'react';
import createClient from 'openapi-fetch';
import type { paths } from '@/sdk';
import { useProject } from '@/hooks/use-graph';
import { useQuery } from '@tanstack/react-query';
import type { Template } from '@shared/schema';

interface TemplateNodeType {
  type: string;
  label?: string;
  description?: string;
  documentation?: string;
  template?: string;
  bestPractices?: string[];
}

interface NodeType {
  value: string;
  label: string;
  description: string;
  documentation?: string;
  template?: string;
  bestPractices?: string[];
}

interface CLICommand {
  command: string;
  description?: string;
  outputFormat?: string;
  requiresProject?: boolean;
  timeout?: number;
  creates?: string[];
  [key: string]: unknown;
}

type CLICommands = Record<string, CLICommand | string>;

interface Snippet {
  code: string;
  description?: string;
}

type Snippets = Record<string, Snippet | string>;

interface ValidationRule {
  rule: string;
  type: 'required' | 'prohibited';
  description: string;
  pattern?: string;
}

interface ExtendedTemplate extends Template {
  nodeTypes?: TemplateNodeType[];
  cli?: { commands?: CLICommands } | CLICommands;
  snippets?: Snippets;
  validationRules?: ValidationRule[];
  configSchema?: Record<string, unknown>;
  metadata?: { configSchema?: Record<string, unknown> } & Record<string, unknown>;
}

interface TemplateContextValue {
  currentTemplate: ExtendedTemplate | null;
  isLoading: boolean;
  nodeTypes: NodeType[];
  configSchema: Record<string, unknown> | null;
  cliCommands: CLICommands;
  snippets: Snippets;
  validationRules: ValidationRule[];
}

const TemplateContext = createContext<TemplateContextValue>({
  currentTemplate: null,
  isLoading: false,
  nodeTypes: [],
  configSchema: null,
  cliCommands: {},
  snippets: {},
  validationRules: [],
});

interface TemplateProviderProps {
  projectId: string;
  children: React.ReactNode;
}

export function TemplateProvider({
  projectId,
  children,
}: TemplateProviderProps) {
  const { data: project } = useProject(projectId);
  const templateId = project?.templateId;

  const api = useMemo(() => createClient<paths>({ baseUrl: '/api/v1' }), []);

  const { data: template, isLoading } = useQuery<ExtendedTemplate>({
    queryKey: ['/api/v1/templates', templateId],
    queryFn: async () => {
      const { data, error } = await api.GET('/templates/{id}', {
        params: { path: { id: templateId! } },
      });
      if (error) throw error;
      return data as ExtendedTemplate;
    },
    enabled: !!templateId,
  });

  const contextValue = useMemo(() => {
    if (!template) {
      return {
        currentTemplate: null,
        isLoading,
        nodeTypes: [],
        configSchema: null,
        cliCommands: {},
        snippets: {},
        validationRules: [],
      };
    }

    const nodeTypes: NodeType[] = (template.nodeTypes || []).map(
      (nt: TemplateNodeType) => ({
        value: nt.type,
        label: nt.label ||
          nt.type.charAt(0).toUpperCase() + nt.type.slice(1),
        description: nt.description || `${nt.type} component`,
        documentation: nt.documentation,
        template: nt.template,
        bestPractices: nt.bestPractices || [],
      })
    );

    const configSchema =
      template.configSchema || template.metadata?.configSchema || null;

    const cliCommands: CLICommands = template.cli && 'commands' in template.cli
      ? (template.cli.commands as CLICommands)
      : ((template.cli as CLICommands) || {});

    const snippets: Snippets = Object.entries(template.snippets || {}).reduce(
      (acc, [key, value]) => {
        acc[key] =
          typeof value === 'string' ? { code: value } : value;
        return acc;
      },
      {} as Snippets
    );

    return {
      currentTemplate: template,
      isLoading,
      nodeTypes,
      configSchema,
      cliCommands,
      snippets,
      validationRules: template.validationRules || [],
    };
  }, [template, isLoading]);

  return (
    <TemplateContext.Provider value={contextValue}>
      {children}
    </TemplateContext.Provider>
  );
}

export function useTemplate() {
  return useContext(TemplateContext);
}
