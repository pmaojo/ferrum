import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Cpu,
  Database,
  HardDrive,
  History,
  MemoryStick,
  Network,
  RefreshCw,
  Settings,
  Play,
  Square,
  Pause,
  RotateCcw,
  ExternalLink,
  Folder,
  Plus,
  Trash2,
  Edit,
  GitBranch,
  Code,
  Terminal,
  Monitor,
  Layers,
  Hexagon,
  Zap,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import {
  useDashboardOverview,
  useServices,
  useFrameworks,
  useDashboardProjects,
  useFrameworkSwitch,
  useServiceAction,
  useCreateProject,
} from '@/hooks/useDashboard';

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'stopped';
  url: string;
  port: number;
  framework?: string;
  description: string;
  lastCheck: string;
  responseTime?: number;
  version?: string;
  dependencies?: string[];
}

interface Framework {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'error';
  description: string;
  icon: React.ReactNode;
  services: string[];
  composeFile: string;
  features: {
    name: string;
    status: 'working' | 'partial' | 'planned' | 'broken';
    description: string;
  }[];
}

interface Project {
  id: string;
  name: string;
  framework: string;
  status: 'active' | 'inactive' | 'archived';
  lastModified: string;
  description: string;
  path: string;
  gitBranch?: string;
  nodeCount?: number;
  edgeCount?: number;
}

// Helper function to get framework icon
const getFrameworkIcon = (frameworkId: string) => {
  switch (frameworkId) {
    case 'ferrum':
      return <Zap className="h-5 w-5" />;
    case 'kthulu':
      return <Code className="h-5 w-5" />;
    case 'tuetano':
      return <Terminal className="h-5 w-5" />;
    default:
      return <Code className="h-5 w-5" />;
  }
};

export default function UnifiedDashboard() {
  const { toast } = useToast();
  const [selectedFramework, setSelectedFramework] = useState<string>('');
  
  // Use dashboard hooks
  const { data: overview, isLoading: overviewLoading, refetch: refetchOverview } = useDashboardOverview();
  const { data: services = [], isLoading: servicesLoading, refetch: refetchServices } = useServices();
  const { data: frameworks = [], isLoading: frameworksLoading } = useFrameworks();
  const { data: projects = [], isLoading: projectsLoading } = useDashboardProjects(selectedFramework || undefined);
  
  // Mutations
  const frameworkSwitch = useFrameworkSwitch();
  const serviceAction = useServiceAction();
  const createProject = useCreateProject();
  
  const loading = overviewLoading || servicesLoading || frameworksLoading;
  const refreshing = frameworkSwitch.isPending || serviceAction.isPending;

  // Set initial selected framework from overview data
  useEffect(() => {
    if (overview?.activeFramework && !selectedFramework) {
      setSelectedFramework(overview.activeFramework);
    }
  }, [overview, selectedFramework]);

  const fetchServiceStatus = async () => {
    try {
      await Promise.all([
        refetchOverview(),
        refetchServices(),
      ]);
    } catch (error) {
      console.error('Error fetching service status:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch service status',
        variant: 'destructive',
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'working':
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'degraded':
      case 'partial':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'unhealthy':
      case 'broken':
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'stopped':
      case 'inactive':
        return <Square className="h-4 w-4 text-gray-500" />;
      case 'planned':
        return <Clock className="h-4 w-4 text-blue-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'working':
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'degraded':
      case 'partial':
        return 'bg-yellow-100 text-yellow-800';
      case 'unhealthy':
      case 'broken':
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'stopped':
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'planned':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleFrameworkSwitch = async (frameworkId: string) => {
    setSelectedFramework(frameworkId);
    
    if (frameworkId) {
      frameworkSwitch.mutate(frameworkId);
    }
  };

  const handleServiceAction = async (serviceName: string, action: 'start' | 'stop' | 'restart') => {
    serviceAction.mutate({ serviceName, action });
  };

  const createNewProject = async (framework: string) => {
    const projectName = `${framework}-project-${Date.now()}`;
    createProject.mutate({
      name: projectName,
      framework,
      description: `New ${framework} project`,
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading dashboard...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Ferrum Studio</h1>
          <p className="text-muted-foreground">
            AI-first scaffolding system for full-stack Rust + React + TypeScript applications
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Select value={selectedFramework} onValueChange={handleFrameworkSwitch}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Select Framework" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Frameworks</SelectItem>
              {frameworks.map((framework) => (
                <SelectItem key={framework.id} value={framework.id}>
                  <div className="flex items-center gap-2">
                    {getFrameworkIcon(framework.id)}
                    {framework.name}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            onClick={fetchServiceStatus}
            disabled={refreshing}
            variant="outline"
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="services">Services</TabsTrigger>
          <TabsTrigger value="frameworks">Frameworks</TabsTrigger>
          <TabsTrigger value="projects">Projects</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {/* Framework Status Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {frameworks.map((framework) => (
              <Card key={framework.id} className="relative">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center justify-between text-sm font-medium">
                    <div className="flex items-center gap-2">
                      {getFrameworkIcon(framework.id)}
                      {framework.name}
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(framework.status)}
                      <Badge className={getStatusColor(framework.status)}>
                        {framework.status}
                      </Badge>
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-3">
                    {framework.description}
                  </p>
                  <div className="space-y-2">
                    <div className="text-xs font-medium">Services:</div>
                    <div className="flex flex-wrap gap-1">
                      {framework.services.map((serviceName) => {
                        const service = services.find(s => s.name.toLowerCase().includes(serviceName.toLowerCase()));
                        return (
                          <Badge
                            key={serviceName}
                            variant="outline"
                            className={`text-xs ${service ? getStatusColor(service.status) : 'bg-gray-100 text-gray-800'}`}
                          >
                            {serviceName}
                          </Badge>
                        );
                      })}
                    </div>
                  </div>
                  <div className="mt-3 flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleFrameworkSwitch(framework.id)}
                      disabled={framework.status === 'active'}
                    >
                      <Play className="h-3 w-3 mr-1" />
                      Activate
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => createNewProject(framework.id)}
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      New Project
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Service Status Overview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Service Status Overview
              </CardTitle>
              <CardDescription>
                Real-time status of all development services
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {services
                  .filter(service => !selectedFramework || !service.framework || service.framework === selectedFramework)
                  .map((service) => (
                  <div key={service.name} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(service.status)}
                      <div>
                        <div className="font-medium text-sm">{service.name}</div>
                        <div className="text-xs text-muted-foreground">
                          Port {service.port}
                          {service.responseTime && ` • ${service.responseTime}ms`}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => window.open(service.url, '_blank')}
                        disabled={service.status === 'stopped'}
                      >
                        <ExternalLink className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="services" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Service Management</CardTitle>
              <CardDescription>
                Monitor and control development services
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {services
                  .filter(service => !selectedFramework || !service.framework || service.framework === selectedFramework)
                  .map((service) => (
                  <div key={service.name} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-4">
                      {getStatusIcon(service.status)}
                      <div>
                        <div className="font-medium">{service.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {service.description}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {service.url} • Port {service.port}
                          {service.responseTime && ` • Response: ${service.responseTime}ms`}
                          {service.version && ` • v${service.version}`}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={getStatusColor(service.status)}>
                        {service.status}
                      </Badge>
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleServiceAction(service.name, 'start')}
                          disabled={service.status === 'healthy'}
                        >
                          <Play className="h-3 w-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleServiceAction(service.name, 'stop')}
                          disabled={service.status === 'stopped'}
                        >
                          <Square className="h-3 w-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleServiceAction(service.name, 'restart')}
                        >
                          <RotateCcw className="h-3 w-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => window.open(service.url, '_blank')}
                          disabled={service.status === 'stopped'}
                        >
                          <ExternalLink className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="frameworks" className="space-y-4">
          {frameworks.map((framework) => (
            <Card key={framework.id}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getFrameworkIcon(framework.id)}
                    {framework.name}
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(framework.status)}
                    <Badge className={getStatusColor(framework.status)}>
                      {framework.status}
                    </Badge>
                  </div>
                </CardTitle>
                <CardDescription>{framework.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium mb-2">Features</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {framework.features.map((feature) => (
                        <div key={feature.name} className="flex items-center justify-between p-2 border rounded">
                          <div>
                            <div className="font-medium text-sm">{feature.name}</div>
                            <div className="text-xs text-muted-foreground">{feature.description}</div>
                          </div>
                          <div className="flex items-center gap-1">
                            {getStatusIcon(feature.status)}
                            <Badge variant="outline" className={getStatusColor(feature.status)}>
                              {feature.status}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <Button
                      onClick={() => handleFrameworkSwitch(framework.id)}
                      disabled={framework.status === 'active'}
                    >
                      <Play className="h-4 w-4 mr-2" />
                      Activate Framework
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => createNewProject(framework.id)}
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      New Project
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => window.open(`/docs/${framework.id}`, '_blank')}
                    >
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Documentation
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="projects" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Folder className="h-5 w-5" />
                  Project Management
                </div>
                <Button onClick={() => createNewProject(selectedFramework || 'ferrum')}>
                  <Plus className="h-4 w-4 mr-2" />
                  New Project
                </Button>
              </CardTitle>
              <CardDescription>
                Manage your development projects across all frameworks
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {projects
                  .filter(project => !selectedFramework || project.framework === selectedFramework)
                  .map((project) => (
                  <div key={project.id} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        {getFrameworkIcon(project.framework)}
                        {getStatusIcon(project.status)}
                      </div>
                      <div>
                        <div className="font-medium">{project.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {project.description}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Framework: {project.framework} • Modified: {new Date(project.lastModified).toLocaleDateString()}
                          {project.nodeCount && ` • ${project.nodeCount} nodes`}
                          {project.edgeCount && ` • ${project.edgeCount} edges`}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={getStatusColor(project.status)}>
                        {project.status}
                      </Badge>
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => window.location.href = `/?project=${project.id}`}
                        >
                          <Edit className="h-3 w-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => window.open(project.path, '_blank')}
                        >
                          <ExternalLink className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
                
                {projects.filter(project => !selectedFramework || project.framework === selectedFramework).length === 0 && (
                  <div className="text-center py-8">
                    <Folder className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium">No Projects Found</h3>
                    <p className="text-muted-foreground mb-4">
                      {selectedFramework 
                        ? `No ${selectedFramework} projects found. Create your first project to get started.`
                        : 'No projects found. Create your first project to get started.'
                      }
                    </p>
                    <Button onClick={() => createNewProject(selectedFramework || 'ferrum')}>
                      <Plus className="h-4 w-4 mr-2" />
                      Create Project
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}