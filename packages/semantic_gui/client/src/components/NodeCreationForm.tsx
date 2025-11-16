import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Brain,
  ExternalLink,
  Code,
  FileText,
  Lightbulb,
  Target,
  Zap,
  Plus,
  Link,
  X,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useGraphData } from '@/hooks/use-graph';
import { useTemplate } from '@/context/TemplateContext';

const nodeFormSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  type: z.string().min(1, 'Type is required'),
  description: z.string().optional(),
  filePath: z.string().optional(),
});

type NodeFormData = z.infer<typeof nodeFormSchema>;

interface NodeCreationFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (
    data: NodeFormData & { position: { x: number; y: number } }
  ) => void;
  position: { x: number; y: number };
}

// Default fallback node types for when no template is loaded
const fallbackNodeTypes = [
  {
    value: 'component',
    label: 'Component',
    description: 'Generic architectural component',
    template: `export class {name}Component {
  // Implementation here
}`,
    bestPractices: [
      'Single responsibility principle',
      'Clear naming conventions',
      'Proper documentation',
    ],
  },
  {
    value: 'service',
    label: 'Service',
    description: 'Business service layer',
    template: `export class {name}Service {
  // Service implementation
}`,
    bestPractices: [
      'Dependency injection',
      'Error handling',
      'Interface segregation',
    ],
  },
];

export function NodeCreationForm({
  isOpen,
  onClose,
  onSubmit,
  position,
}: NodeCreationFormProps) {
  const {
    currentTemplate,
    nodeTypes: templateNodeTypes,
    isLoading,
  } = useTemplate();
  const [activeTab, setActiveTab] = useState('basic');
  const [isGeneratingAI, setIsGeneratingAI] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<any>(null);
  const { toast } = useToast();

  // Use template node types or fallback to generic types
  const nodeTypes =
    templateNodeTypes.length > 0 ? templateNodeTypes : fallbackNodeTypes;

  const form = useForm<NodeFormData>({
    resolver: zodResolver(nodeFormSchema),
    defaultValues: {
      name: '',
      type: '',
      description: '',
      filePath: '',
    },
  });

  const selectedType = form.watch('type');
  const selectedTypeInfo = nodeTypes.find((t) => t.value === selectedType);

  const handleSubmit = async (data: NodeFormData) => {
    try {
      await onSubmit({
        ...data,
        position,
      });
      form.reset();
      onClose();
      setActiveTab('basic'); // Reset to basic tab
      setAiSuggestions(null); // Clear AI suggestions
    } catch (error) {
      console.error('Form submission error:', error);
      // Don't close form on error so user can retry
    }
  };

  const generateAISuggestions = async () => {
    const nodeName = form.getValues('name');
    const nodeType = form.getValues('type');

    if (!nodeName || !nodeType) {
      toast({
        title: 'Missing Information',
        description: 'Please provide node name and type first',
        variant: 'destructive',
      });
      return;
    }

    setIsGeneratingAI(true);

    try {
      // Simulate AI call - replace with actual AI service
      await new Promise((resolve) => setTimeout(resolve, 1500));

      const suggestions = {
        description: `${
          nodeType === 'controller'
            ? 'Handles HTTP requests for'
            : nodeType === 'service'
              ? 'Business logic for'
              : nodeType === 'repository'
                ? 'Data access for'
                : nodeType === 'entity'
                  ? 'Domain model representing'
                  : 'Component for'
        } ${nodeName.toLowerCase()} operations`,
        filePath: `src/${nodeType}s/${nodeName.toLowerCase()}.${nodeType}.ts`,
        relatedComponents: [
          nodeType === 'controller' ? `${nodeName}Service` : null,
          nodeType === 'service' ? `${nodeName}Repository` : null,
          nodeType === 'repository' ? `${nodeName}Entity` : null,
        ].filter(Boolean),
        codeTemplate:
          selectedTypeInfo?.template?.replace(/{name}/g, nodeName) || '',
        testSuggestions: [
          `${nodeName}.${nodeType}.spec.ts`,
          `${nodeName}.integration.spec.ts`,
        ],
      };

      setAiSuggestions(suggestions);

      // Auto-fill form
      form.setValue('description', suggestions.description);
      form.setValue('filePath', suggestions.filePath);

      toast({
        title: '🧠 AI Suggestions Generated',
        description: 'Form auto-filled with intelligent suggestions',
      });
    } catch (error) {
      toast({
        title: 'AI Error',
        description: 'Failed to generate suggestions',
        variant: 'destructive',
      });
    } finally {
      setIsGeneratingAI(false);
    }
  };

  const openDocumentation = () => {
    if (selectedTypeInfo?.documentation) {
      window.open(selectedTypeInfo.documentation, '_blank');
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-black border-[#00ff00] text-[#00ff00] max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-mono text-[#00ff00] text-lg flex items-center space-x-2">
            <Code className="h-5 w-5" />
            <span>CREATE_NODE.EXE</span>
            {currentTemplate && (
              <Badge
                variant="outline"
                className="text-xs border-[#00ff00] text-[#00ff00]"
              >
                {currentTemplate.name}
              </Badge>
            )}
            {isLoading && (
              <Badge
                variant="outline"
                className="text-xs border-yellow-500 text-yellow-500"
              >
                LOADING...
              </Badge>
            )}
            <Badge
              variant="outline"
              className="text-xs border-[#00ff00] text-[#00ff00]"
            >
              v2.0_ENHANCED
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 bg-black border border-[#00ff00]/30">
            <TabsTrigger value="basic" className="text-[#00ff00] font-mono">
              BASIC
            </TabsTrigger>
            <TabsTrigger value="ai" className="text-[#00ff00] font-mono">
              AI_ASSIST
            </TabsTrigger>
            <TabsTrigger value="docs" className="text-[#00ff00] font-mono">
              DOCS
            </TabsTrigger>
          </TabsList>

          <TabsContent value="basic" className="space-y-4">
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(handleSubmit)}
                className="space-y-4"
              >
                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-[#00ff00] font-mono text-sm">
                          NAME:
                        </FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            className="bg-black border-[#00ff00] text-[#00ff00] font-mono placeholder:text-[#00ff00]/50"
                            placeholder="Enter node name..."
                          />
                        </FormControl>
                        <FormMessage className="text-red-400 font-mono text-xs" />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-[#00ff00] font-mono text-sm">
                          TYPE:
                        </FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          defaultValue={field.value}
                        >
                          <FormControl>
                            <SelectTrigger className="bg-black border-[#00ff00] text-[#00ff00] font-mono">
                              <SelectValue placeholder="Select type..." />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent className="bg-black border-[#00ff00] text-[#00ff00]">
                            {nodeTypes.map((type) => (
                              <SelectItem
                                key={type.value}
                                value={type.value}
                                className="font-mono hover:bg-[#00ff00]/10"
                              >
                                {type.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage className="text-red-400 font-mono text-xs" />
                      </FormItem>
                    )}
                  />
                </div>

                {selectedTypeInfo && (
                  <div className="flex items-center justify-between p-3 border border-[#00ff00]/30 rounded">
                    <div>
                      <div className="text-[#00ff00]/70 font-mono text-xs">
                        INFO: {selectedTypeInfo.description}
                      </div>
                      <div className="flex gap-2 mt-2">
                        {selectedTypeInfo.bestPractices
                          ?.slice(0, 2)
                          .map((practice, i) => (
                            <Badge
                              key={i}
                              variant="outline"
                              className="text-xs border-[#00ff00]/50 text-[#00ff00]/70"
                            >
                              {practice}
                            </Badge>
                          ))}
                      </div>
                    </div>
                    <Button
                      type="button"
                      onClick={openDocumentation}
                      size="sm"
                      className="bg-transparent border border-[#00ff00] text-[#00ff00] hover:bg-[#00ff00]/10"
                    >
                      <ExternalLink className="h-4 w-4 mr-1" />
                      DOCS
                    </Button>
                  </div>
                )}

                <FormField
                  control={form.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-[#00ff00] font-mono text-sm">
                        DESCRIPTION:
                      </FormLabel>
                      <FormControl>
                        <Textarea
                          {...field}
                          className="bg-black border-[#00ff00] text-[#00ff00] font-mono placeholder:text-[#00ff00]/50 min-h-16"
                          placeholder="Describe component functionality..."
                        />
                      </FormControl>
                      <FormMessage className="text-red-400 font-mono text-xs" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="filePath"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-[#00ff00] font-mono text-sm">
                        FILE_PATH:
                      </FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          className="bg-black border-[#00ff00] text-[#00ff00] font-mono placeholder:text-[#00ffকিন্ত
0ff00]/50"
                          placeholder="src/components/example.ts"
                        />
                      </FormControl>
                      <FormMessage className="text-red-400 font-mono text-xs" />
                    </FormItem>
                  )}
                />

                <div className="flex gap-2 pt-4">
                  <Button
                    type="button"
                    onClick={onClose}
                    className="flex-1 bg-transparent border border-[#00ff00] text-[#00ff00] hover:bg-[#00ff00]/10 font-mono"
                  >
                    CANCEL
                  </Button>
                  <Button
                    type="submit"
                    className="flex-1 bg-[#00ff00] text-black hover:bg-[#00ff00]/80 font-mono"
                  >
                    CREATE_NODE
                  </Button>
                </div>
              </form>
            </Form>
          </TabsContent>

          <TabsContent value="ai" className="space-y-4">
            <div className="text-center p-6 border border-[#00ff00]/30 rounded">
              <Brain className="h-12 w-12 text-[#00ff00] mx-auto mb-4" />
              <h3 className="text-[#00ff00] font-mono font-bold mb-2">
                AI_ASSISTANT_READY
              </h3>
              <p className="text-[#00ff00]/70 font-mono text-sm mb-4">
                Enter node name and type, then let AI generate intelligent
                suggestions
              </p>

              <Button
                onClick={generateAISuggestions}
                disabled={
                  isGeneratingAI || !form.watch('name') || !form.watch('type')
                }
                className="bg-[#00ff00] text-black hover:bg-[#00ff00]/80 font-mono"
              >
                {isGeneratingAI ? (
                  <>
                    <div className="animate-spin h-4 w-4 mr-2 border-2 border-black border-t-transparent rounded-full" />
                    ANALYZING...
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4 mr-2" />
                    GENERATE_SUGGESTIONS
                  </>
                )}
              </Button>
            </div>

            {aiSuggestions && (
              <div className="space-y-4">
                <div className="p-4 border border-[#00ff00]/30 rounded">
                  <h4 className="text-[#00ff00] font-mono font-bold text-sm mb-2">
                    <Target className="h-4 w-4 inline mr-2" />
                    AI_SUGGESTIONS
                  </h4>

                  <div className="space-y-3">
                    <div>
                      <div className="text-[#00ff00]/70 font-mono text-xs">
                        DESCRIPTION:
                      </div>
                      <div className="text-[#00ff00] font-mono text-sm">
                        {aiSuggestions.description}
                      </div>
                    </div>

                    <div>
                      <div className="text-[#00ff00]/70 font-mono text-xs">
                        FILE_PATH:
                      </div>
                      <div className="text-[#00ff00] font-mono text-sm">
                        {aiSuggestions.filePath}
                      </div>
                    </div>

                    <div>
                      <div className="text-[#00ff00]/70 font-mono text-xs">
                        RELATED_COMPONENTS:
                      </div>
                      <div className="flex gap-2 mt-1">
                        {aiSuggestions.relatedComponents?.map(
                          (comp: string, i: number) => (
                            <Badge
                              key={i}
                              variant="outline"
                              className="text-xs border-[#00ff00]/50 text-[#00ff00]/70"
                            >
                              {comp}
                            </Badge>
                          )
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-[#00ff00]/70 font-mono text-xs">
                        TEST_FILES:
                      </div>
                      <div className="flex gap-2 mt-1">
                        {aiSuggestions.testSuggestions?.map(
                          (test: string, i: number) => (
                            <Badge
                              key={i}
                              variant="outline"
                              className="text-xs border-[#00ff00]/50 text-[#00ff00]/70"
                            >
                              {test}
                            </Badge>
                          )
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {aiSuggestions.codeTemplate && (
                  <div className="p-4 border border-[#00ff00]/30 rounded">
                    <h4 className="text-[#00ff00] font-mono font-bold text-sm mb-2">
                      <Code className="h-4 w-4 inline mr-2" />
                      CODE_TEMPLATE
                    </h4>
                    <pre className="text-[#00ff00]/80 font-mono text-xs bg-black/50 p-3 rounded overflow-x-auto">
                      {aiSuggestions.codeTemplate}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </TabsContent>

          <TabsContent value="docs" className="space-y-4">
            {selectedTypeInfo ? (
              <div className="space-y-4">
                <div className="p-4 border border-[#00ff00]/30 rounded">
                  <h3 className="text-[#00ff00] font-mono font-bold flex items-center mb-3">
                    <FileText className="h-5 w-5 mr-2" />
                    {selectedTypeInfo.label.toUpperCase()}_DOCUMENTATION
                  </h3>

                  <p className="text-[#00ff00]/80 font-mono text-sm mb-4">
                    {selectedTypeInfo.description}
                  </p>

                  <div className="mb-4">
                    <h4 className="text-[#00ff00] font-mono font-bold text-sm mb-2">
                      <Lightbulb className="h-4 w-4 inline mr-2" />
                      BEST_PRACTICES:
                    </h4>
                    <ul className="space-y-1">
                      {selectedTypeInfo.bestPractices?.map((practice, i) => (
                        <li
                          key={i}
                          className="text-[#00ff00]/70 font-mono text-sm"
                        >
                          {'>'} {practice}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <Button
                    onClick={openDocumentation}
                    className="bg-[#00ff00] text-black hover:bg-[#00ff00]/80 font-mono w-full"
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    OPEN_OFFICIAL_DOCS
                  </Button>
                </div>

                {selectedTypeInfo.template && (
                  <div className="p-4 border border-[#00ff00]/30 rounded">
                    <h4 className="text-[#00ff00] font-mono font-bold text-sm mb-2">
                      <Code className="h-4 w-4 inline mr-2" />
                      CODE_TEMPLATE:
                    </h4>
                    <pre className="text-[#00ff00]/80 font-mono text-xs bg-black/50 p-3 rounded overflow-x-auto">
                      {selectedTypeInfo.template}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center p-6 border border-[#00ff00]/30 rounded">
                <FileText className="h-12 w-12 text-[#00ff00]/50 mx-auto mb-4" />
                <p className="text-[#00ff00]/70 font-mono text-sm">
                  Select a node type to view documentation and examples
                </p>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
