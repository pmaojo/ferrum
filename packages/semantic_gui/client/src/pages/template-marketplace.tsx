import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useCreateProject } from '@/hooks/use-graph';
import {
  useTemplateCategories,
  useTemplateSearch,
} from '@/hooks/useTemplateLibrary';
import { useToast } from '@/hooks/use-toast';
import {
  Search,
  Plus,
  Code,
  Zap,
  Shield,
  Database,
  Globe,
  ArrowLeft,
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Link, useLocation } from 'wouter';
import type { Template } from '@shared/schema';

export default function TemplateMarketplace() {
  const createProjectMutation = useCreateProject();
  const { toast } = useToast();
  const [, setLocation] = useLocation();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [projectPath, setProjectPath] = useState('');

  const { data: categories } = useTemplateCategories();
  const { data: searchResults } = useTemplateSearch(searchTerm);

  const allTemplates = categories ? Object.values(categories).flat() : [];
  const categoryTemplates =
    selectedCategory === 'All'
      ? allTemplates
      : categories?.[selectedCategory] || [];
  const filteredTemplates = searchTerm
    ? searchResults || []
    : categoryTemplates;

  const handleCreateProject = async (template: Template) => {
    try {
      if (!projectPath.trim()) {
        toast({
          title: 'PROJECT_PATH_REQUIRED',
          description: 'Enter the root directory for the new project.',
          variant: 'destructive',
        });
        return;
      }
      const projectName = `${template.name.toUpperCase().replace(/\s+/g, '_')}_PROJECT_${Date.now()}`;

      const newProject = await createProjectMutation.mutateAsync({
        name: projectName,
        description: `Project based on ${template.name} architecture template`,
        templateId: template.id,
        projectPath: projectPath.trim(),
      });

      toast({
        title: 'PROJECT_CREATED',
        description: `New project created with ${template.name} template`,
      });

      // Redirect to home page to load the new project
      setLocation('/');
    } catch (error) {
      toast({
        title: 'CREATION_FAILED',
        description: 'Failed to create project',
        variant: 'destructive',
      });
    }
  };

  const getTemplateIcon = (templateName: string) => {
    if (templateName.toLowerCase().includes('nestjs'))
      return <Code className="h-6 w-6" />;
    if (templateName.toLowerCase().includes('microservice'))
      return <Globe className="h-6 w-6" />;
    if (templateName.toLowerCase().includes('security'))
      return <Shield className="h-6 w-6" />;
    if (templateName.toLowerCase().includes('database'))
      return <Database className="h-6 w-6" />;
    return <Zap className="h-6 w-6" />;
  };

  const getComplexityColor = (nodeCount: number) => {
    if (nodeCount <= 3) return 'bg-green-500';
    if (nodeCount <= 6) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getComplexityLabel = (nodeCount: number) => {
    if (nodeCount <= 3) return 'SIMPLE';
    if (nodeCount <= 6) return 'MEDIUM';
    return 'COMPLEX';
  };

  return (
    <div className="min-h-screen bg-black text-[#00FF41] font-mono p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            <Link href="/">
              <Button
                variant="outline"
                className="border-[#FF00FF] text-[#FF00FF] hover:bg-[#FF00FF]/10"
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                BACK_TO_HOME
              </Button>
            </Link>
            <h1 className="text-4xl font-black text-[#00FFFF] tracking-wider terminal-flicker">
              TEMPLATE_MARKETPLACE
            </h1>
          </div>
        </div>

        <p className="text-lg text-[#00FF41]/80 mb-6">
          Choose from pre-configured architecture templates to accelerate your
          development
        </p>

        {/* Search and Category Filters */}
        <div className="flex flex-wrap gap-4 items-center">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[#00FF41]/50" />
            <Input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search templates..."
              className="pl-10 bg-black border-2 border-[#00FF41] text-[#00FF41] placeholder:text-[#00FF41]/50"
            />
          </div>
          <Input
            value={projectPath}
            onChange={(event) => setProjectPath(event.target.value)}
            placeholder="/workspace/my-application"
            className="max-w-md bg-black border-2 border-[#FF00FF] text-[#FF00FF] placeholder:text-[#FF00FF]/50"
          />
          <Select value={selectedCategory} onValueChange={setSelectedCategory}>
            <SelectTrigger className="w-[180px] bg-black border-2 border-[#00FF41] text-[#00FF41]">
              <SelectValue placeholder="All Categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="All">All</SelectItem>
              {categories &&
                Object.keys(categories).map((category) => (
                  <SelectItem key={category} value={category}>
                    {category}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredTemplates.map((template) => (
          <Card
            key={template.id}
            className="bg-black border-2 border-[#00FF41] hover:border-[#00FFFF] transition-all duration-300 hacker-glow hover:shadow-[#00FFFF]/20"
          >
            <CardHeader className="pb-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-3">
                  <div className="text-[#00FFFF]">
                    {getTemplateIcon(template.name)}
                  </div>
                  <div>
                    <CardTitle className="text-[#00FF41] font-black tracking-wider">
                      {template.name.toUpperCase()}
                    </CardTitle>
                    <CardDescription className="text-[#00FF41]/70 text-sm mt-1">
                      {template.description || 'Advanced architecture template'}
                    </CardDescription>
                  </div>
                </div>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              {/* Template Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-2 border border-[#00FF41]/30 rounded">
                  <div className="text-[#00FFFF] font-black text-lg">
                    {template.nodeTypes?.length || 0}
                  </div>
                  <div className="text-xs text-[#00FF41]/70">NODE_TYPES</div>
                </div>
                <div className="text-center p-2 border border-[#00FF41]/30 rounded">
                  <div className="text-[#FFFF00] font-black text-lg">
                    {template.validationRules?.length || 0}
                  </div>
                  <div className="text-xs text-[#00FF41]/70">RULES</div>
                </div>
              </div>

              {/* Complexity Badge */}
              <div className="flex items-center justify-between">
                <Badge
                  className={`${getComplexityColor(template.nodeTypes?.length || 0)} text-black font-black px-2 py-1`}
                >
                  {getComplexityLabel(template.nodeTypes?.length || 0)}
                </Badge>
                <div className="text-xs text-[#00FF41]/60">
                  ID: {template.id}
                </div>
              </div>

              {/* Node Types Preview */}
              {template.nodeTypes && template.nodeTypes.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs text-[#00FFFF] font-bold">
                    INCLUDED_TYPES:
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {template.nodeTypes.slice(0, 4).map((nodeType, index) => (
                      <Badge
                        key={index}
                        variant="outline"
                        className="text-xs border-[#00FF41] text-[#00FF41] px-1 py-0"
                      >
                        {nodeType.type.toUpperCase()}
                      </Badge>
                    ))}
                    {template.nodeTypes.length > 4 && (
                      <Badge
                        variant="outline"
                        className="text-xs border-[#00FF41]/50 text-[#00FF41]/50 px-1 py-0"
                      >
                        +{template.nodeTypes.length - 4}
                      </Badge>
                    )}
                  </div>
                </div>
              )}

              {/* Create Project Button */}
              <Button
                onClick={() => handleCreateProject(template)}
                disabled={createProjectMutation.isPending}
                className="w-full bg-[#00FF41] text-black hover:bg-[#00FF41]/80 font-black tracking-wider"
              >
                <Plus className="h-4 w-4 mr-2" />
                {createProjectMutation.isPending
                  ? 'CREATING...'
                  : 'CREATE_PROJECT'}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {filteredTemplates.length === 0 && (
        <div className="text-center py-12">
          <Code className="h-16 w-16 mx-auto text-[#00FF41]/50 mb-4" />
          <h3 className="text-xl font-black text-[#00FF41] mb-2">
            NO_TEMPLATES_FOUND
          </h3>
          <p className="text-[#00FF41]/70">
            {searchTerm
              ? 'Try adjusting your search terms'
              : 'No templates available'}
          </p>
        </div>
      )}

      {/* Footer Info */}
      <div className="mt-12 text-center text-[#00FF41]/50 text-sm">
        <p>Templates provide pre-configured node types and validation rules</p>
        <p>
          Each template enforces specific architectural patterns and best
          practices
        </p>
      </div>
    </div>
  );
}
