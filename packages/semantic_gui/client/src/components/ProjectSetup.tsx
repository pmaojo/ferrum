import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  useTemplates,
  useCreateProject,
  useKthuluInit,
} from '@/hooks/use-graph';
import { usePermaGraphWebSocket } from '@/hooks/usePermaGraphWebSocket';
import { useToast } from '@/hooks/use-toast';
import { Settings, Code, Zap } from 'lucide-react';
import type { Template } from '@shared/schema';
import { validateConfig } from '@/utils/validateConfig';

interface ProjectSetupProps {
  onComplete: (projectId: string, template: Template) => void;
}

/**
 * Presents available templates and creates a project when one is chosen.
 * Template configuration is driven by each template's configSchema.
 */
export function ProjectSetup({ onComplete }: ProjectSetupProps) {
  const { data: templates } = useTemplates();
  const createProject = useCreateProject();
  const kthuluInit = useKthuluInit();
  const { toast } = useToast();

  const initHooks: Record<string, any> = {
    kthulu: kthuluInit,
  };

  const [selected, setSelected] = useState<Template | null>(null);
  const [config, setConfig] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isValid, setIsValid] = useState(true);
  const [projectPath, setProjectPath] = useState('');
  const [pendingProject, setPendingProject] = useState<{
    project: any;
    template: Template;
  } | null>(null);
  const { syncSummary } = usePermaGraphWebSocket(
    pendingProject?.project.id || ''
  );

  const configSchema = (selected?.configSchema || null) as Record<
    string,
    any
  > | null;
  const initHook = selected?.metadata?.framework
    ? initHooks[selected.metadata.framework]
    : undefined;

  // Initialize config with default values when template is selected
  const handleTemplateSelect = (template: Template) => {
    setSelected(template);
    const schema = (template.configSchema || {}) as Record<string, any>;
    const initialConfig: Record<string, any> = {};

    // Set default values from schema properties
    Object.entries(schema.properties || {}).forEach(([key, prop]: any) => {
      if (prop.default !== undefined) {
        initialConfig[key] = prop.default;
      }
    });

    const result = validateConfig(schema, { ...initialConfig });
    setConfig(initialConfig);
    setErrors(result.errors);
    setIsValid(result.isValid);
    setProjectPath(initialConfig.projectPath ?? '');
  };

  const updateConfig = (name: string, value: any) => {
    setConfig((prev) => {
      if (name === 'projectPath') {
        setProjectPath(value ?? '');
      }
      const updated = { ...prev, [name]: value };
      const result = validateConfig(configSchema || {}, { ...updated });
      setErrors(result.errors);
      setIsValid(result.isValid);
      return updated;
    });
  };

  // Render different input types based on schema
  const renderConfigField = (name: string, schema: any) => {
    const value = config[name];

    switch (schema.type) {
      case 'string':
        if (schema.enum) {
          return (
            <Select
              value={value}
              onValueChange={(newValue) => updateConfig(name, newValue)}
            >
              <SelectTrigger>
                <SelectValue placeholder={schema.title || `Select ${name}`} />
              </SelectTrigger>
              <SelectContent>
                {schema.enum.map((option: string) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          );
        }
        return (
          <Input
            id={name}
            type="text"
            placeholder={schema.placeholder}
            value={value ?? ''}
            onChange={(e) => updateConfig(name, e.target.value)}
          />
        );
      case 'boolean':
        return (
          <div className="flex items-center space-x-2">
            <Checkbox
              id={name}
              checked={value ?? false}
              onCheckedChange={(checked) => updateConfig(name, checked)}
            />
            <Label htmlFor={name} className="text-sm font-normal">
              {schema.title || name}
            </Label>
          </div>
        );
      case 'number':
      case 'integer':
        return (
          <Input
            id={name}
            type="number"
            placeholder={schema.placeholder}
            value={value ?? ''}
            onChange={(e) => updateConfig(name, e.target.valueAsNumber || 0)}
          />
        );
      default:
        return (
          <Input
            id={name}
            type="text"
            placeholder={schema.placeholder}
            value={value ?? ''}
            onChange={(e) => updateConfig(name, e.target.value)}
          />
        );
    }
  };

  useEffect(() => {
    if (pendingProject && syncSummary) {
      toast({
        title: 'PROJECT_CREATED',
        description: pendingProject.project.name,
      });
      onComplete(pendingProject.project.id, pendingProject.template);
      setPendingProject(null);
    }
  }, [pendingProject, syncSummary, toast, onComplete]);

  const handleCreate = () => {
    if (!selected) return;
    if (!projectPath.trim()) {
      toast({
        title: 'Project Path Required',
        description: 'Provide the absolute path to your project root.',
        variant: 'destructive',
      });
      return;
    }

    createProject.mutate(
      {
        name: `ZHUL_SYS_${selected.name
          .replace(/\s+/g, '_')
          .toUpperCase()}_001`,
        description: `ZHUL_SYS architecture using ${selected.name}`,
        templateId: selected.id,
        projectPath: projectPath.trim(),
        config,
      },
      {
        onSuccess: (project) => {
          const waitForSync = () => {
            setPendingProject({ project, template: selected });
          };

          if (initHook) {
            initHook.mutate(
              { projectId: project.id, ...config },
              {
                onSuccess: waitForSync,
                onError: (error: any) => {
                  toast({
                    title: 'Initialization Failed',
                    description: error.message,
                    variant: 'destructive',
                  });
                },
              }
            );
          } else {
            waitForSync();
          }
        },
        onError: (error: any) => {
          toast({
            title: 'Project Creation Failed',
            description: error.message,
            variant: 'destructive',
          });
        },
      }
    );
  };

  return (
    <div className="flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Settings className="h-5 w-5" />
            <span>Project Setup</span>
          </CardTitle>
          <CardDescription>
            {selected
              ? `Configure ${selected.name} project options`
              : 'Choose a template to initialize your project'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {!selected ? (
            <div className="grid gap-4">
              <div className="text-sm text-muted-foreground mb-2">
                Available Templates:
              </div>
              {templates?.map((template) => (
                <Card
                  key={template.id}
                  className="cursor-pointer transition-colors hover:bg-muted/50"
                  onClick={() => handleTemplateSelect(template)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2">
                          <Code className="h-4 w-4" />
                          <h3 className="font-semibold">{template.name}</h3>
                          {template.metadata?.framework && (
                            <Badge variant="secondary" className="text-xs">
                              {template.metadata.framework}
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {template.description}
                        </p>
                        {template.metadata?.category && (
                          <Badge variant="outline" className="text-xs">
                            {template.metadata.category}
                          </Badge>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={createProject.isPending}
                      >
                        Select
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="space-y-6">
              {/* Template Info */}
              <div className="flex items-center justify-between p-4 bg-muted/30 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Code className="h-5 w-5" />
                  <div>
                    <h3 className="font-semibold">{selected.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {selected.description}
                    </p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelected(null)}
                >
                  Change Template
                </Button>
              </div>

              <div className="space-y-2">
                <Label htmlFor="projectPath" className="flex items-center space-x-1">
                  <span>Project root path</span>
                  <span className="text-red-500 text-xs">*</span>
                </Label>
                <Input
                  id="projectPath"
                  type="text"
                  placeholder="/workspace/my-application"
                  value={projectPath}
                  onChange={(event) => {
                    const value = event.target.value;
                    setProjectPath(value);
                    if (configSchema?.properties?.projectPath) {
                      updateConfig('projectPath', value);
                    }
                  }}
                  autoComplete="off"
                />
              </div>

              {/* Dynamic Configuration Form */}
              {configSchema &&
              Object.keys(configSchema.properties || {}).length > 0 ? (
                <div className="space-y-4">
                  <div className="flex items-center space-x-2">
                    <Settings className="h-4 w-4" />
                    <h4 className="font-medium">Configuration</h4>
                  </div>

                  {Object.entries(configSchema.properties || {}).map(
                    ([name, schema]: [string, any]) => (
                      <div key={name} className="space-y-2">
                        {schema.type !== 'boolean' && (
                          <Label
                            htmlFor={name}
                            className="flex items-center space-x-1"
                          >
                            <span>{schema.title || name}</span>
                            {configSchema.required?.includes(name) && (
                              <span className="text-red-500 text-xs">*</span>
                            )}
                          </Label>
                        )}

                        {renderConfigField(name, schema)}
                        {errors[name] && (
                          <p className="text-sm text-red-500">{errors[name]}</p>
                        )}

                        {schema.description && (
                          <p className="text-sm text-muted-foreground">
                            {schema.description}
                          </p>
                        )}
                      </div>
                    )
                  )}
                </div>
              ) : (
                <div className="text-center p-6 text-muted-foreground">
                  <Zap className="h-8 w-8 mx-auto mb-2" />
                  <p>No additional configuration required for this template.</p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex space-x-2 pt-4">
                <Button
                  variant="outline"
                  onClick={() => setSelected(null)}
                  className="flex-1"
                  disabled={
                    createProject.isPending ||
                    (initHook && initHook.isPending) ||
                    pendingProject !== null
                  }
                >
                  Back
                </Button>
                <Button
                  onClick={handleCreate}
                  disabled={
                    createProject.isPending ||
                    (initHook && initHook.isPending) ||
                    pendingProject !== null ||
                    !isValid ||
                    !projectPath.trim()
                  }
                  className="flex-1"
                >
                  {createProject.isPending ||
                  initHook?.isPending ||
                  pendingProject ? (
                    <>
                      <div className="animate-spin h-4 w-4 mr-2 border-2 border-white border-t-transparent rounded-full" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Zap className="h-4 w-4 mr-2" />
                      Create Project
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
