import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import {
  BookOpen,
  HelpCircle,
  PlayCircle,
  CheckCircle,
  ArrowRight,
  Lightbulb,
  Code,
  GitBranch,
  Layers,
} from 'lucide-react';

interface Tutorial {
  id: string;
  title: string;
  description: string;
  duration: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  category: 'semantic' | 'architecture' | 'owl' | 'kthulu';
  steps: TutorialStep[];
  completed: boolean;
}

interface TutorialStep {
  id: string;
  title: string;
  content: string;
  interactive?: boolean;
  code?: string;
  action?: string;
}

interface HelpTopic {
  id: string;
  title: string;
  content: string;
  category: string;
  tags: string[];
  examples?: string[];
}

const HelpSystem: React.FC = () => {
  const [activeTab, setActiveTab] = useState('tutorials');
  const [selectedTutorial, setSelectedTutorial] = useState<Tutorial | null>(
    null
  );
  const [currentStep, setCurrentStep] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [userProgress, setUserProgress] = useState<Record<string, boolean>>({});

  const tutorials: Tutorial[] = [
    {
      id: 'semantic-intro',
      title: 'Introduction to Semantic Architecture',
      description:
        'Learn the fundamentals of semantic architecture and how it applies to software design',
      duration: '15 min',
      difficulty: 'beginner',
      category: 'semantic',
      completed: false,
      steps: [
        {
          id: 'step1',
          title: 'What is Semantic Architecture?',
          content:
            'Semantic architecture uses formal ontologies to represent and reason about software architecture. It provides a machine-readable way to describe components, relationships, and constraints.',
          interactive: false,
        },
        {
          id: 'step2',
          title: 'Benefits of Semantic Modeling',
          content:
            'Semantic modeling enables automated validation, intelligent suggestions, and better understanding of complex systems through formal reasoning.',
          interactive: false,
        },
        {
          id: 'step3',
          title: 'Your First Semantic Graph',
          content:
            "Let's create a simple semantic graph representing a basic module structure.",
          interactive: true,
          action: 'Open the graph editor and create a new module node',
        },
      ],
    },
    {
      id: 'owl-basics',
      title: 'OWL Ontology Fundamentals',
      description:
        'Understanding OWL classes, properties, and reasoning capabilities',
      duration: '20 min',
      difficulty: 'intermediate',
      category: 'owl',
      completed: false,
      steps: [
        {
          id: 'step1',
          title: 'OWL Classes and Individuals',
          content:
            'OWL classes represent concepts (like Module, UseCase) while individuals are specific instances of those classes.',
          code: `# Example OWL Class Definition
kth:Module rdf:type owl:Class .
kth:UseCase rdf:type owl:Class .

# Example Individual
kth:AuthModule rdf:type kth:Module .`,
        },
        {
          id: 'step2',
          title: 'Object Properties and Relationships',
          content:
            'Object properties define relationships between individuals, like "definesUseCase" or "dependsOn".',
          code: `# Object Property Definition
kth:definesUseCase rdf:type owl:ObjectProperty ;
    rdfs:domain kth:Module ;
    rdfs:range kth:UseCase .

# Usage
kth:AuthModule kth:definesUseCase kth:LoginUseCase .`,
        },
      ],
    },
    {
      id: 'hexagonal-principles',
      title: 'Hexagonal Architecture Best Practices',
      description:
        'Learn how to apply hexagonal architecture principles in your projects',
      duration: '25 min',
      difficulty: 'intermediate',
      category: 'architecture',
      completed: false,
      steps: [
        {
          id: 'step1',
          title: 'Dependency Inversion Principle',
          content:
            'Domain components should never depend on infrastructure components. Use ports and adapters to invert dependencies.',
          interactive: true,
          action: 'Identify DIP violations in the current graph',
        },
        {
          id: 'step2',
          title: 'Bounded Contexts',
          content:
            'Each module should represent a bounded context with clear boundaries and minimal coupling.',
          interactive: true,
          action: 'Review module boundaries in your architecture',
        },
      ],
    },
    {
      id: 'kthulu-integration',
      title: 'Kthulu CLI Integration',
      description:
        'Learn how to use Kthulu CLI commands within the semantic environment',
      duration: '18 min',
      difficulty: 'beginner',
      category: 'kthulu',
      completed: false,
      steps: [
        {
          id: 'step1',
          title: 'Generating Architecture Graphs',
          content:
            'Use kthulu-cli plan --graph to export your architecture as a semantic graph.',
          code: 'kthulu-cli plan --graph --format=json > architecture.json',
          interactive: true,
          action: 'Try generating a graph from your current project',
        },
        {
          id: 'step2',
          title: 'Creating New Modules',
          content:
            'Use the integrated module wizard to create new modules that follow hexagonal principles.',
          interactive: true,
          action: 'Create a new module using the wizard',
        },
      ],
    },
  ];

  const helpTopics: HelpTopic[] = [
    {
      id: 'owl-classes',
      title: 'OWL Classes',
      content:
        'OWL classes represent concepts in your domain. In Kthulu architecture, we use classes like Module, UseCase, Port, and Adapter to represent different types of components.',
      category: 'OWL Concepts',
      tags: ['owl', 'classes', 'ontology'],
      examples: [
        'kth:Module - Represents a bounded context or module',
        'kth:UseCase - Represents a business use case',
        'kth:Port - Represents an interface or contract',
      ],
    },
    {
      id: 'object-properties',
      title: 'Object Properties',
      content:
        'Object properties define relationships between individuals in your ontology. They specify how different components relate to each other.',
      category: 'OWL Concepts',
      tags: ['owl', 'properties', 'relationships'],
      examples: [
        'kth:definesUseCase - Links a module to its use cases',
        'kth:implementsPort - Links an adapter to the port it implements',
        'kth:dependsOnModule - Defines module dependencies',
      ],
    },
    {
      id: 'dip-principle',
      title: 'Dependency Inversion Principle',
      content:
        'High-level modules should not depend on low-level modules. Both should depend on abstractions. This is enforced through semantic validation rules.',
      category: 'Architecture Principles',
      tags: ['dip', 'solid', 'architecture'],
      examples: [
        'Domain components should only call other domain components or ports',
        'Infrastructure adapters implement ports but are not called directly',
        'Use dependency injection to provide implementations',
      ],
    },
    {
      id: 'bounded-contexts',
      title: 'Bounded Contexts',
      content:
        'A bounded context is a central pattern in Domain-Driven Design. It defines the boundaries within which a particular model is defined and applicable.',
      category: 'Architecture Principles',
      tags: ['ddd', 'bounded-context', 'modules'],
      examples: [
        'Each module represents a bounded context',
        'Entities should not cross context boundaries directly',
        'Use domain events for cross-context communication',
      ],
    },
  ];

  const onboardingSteps = [
    {
      title: 'Welcome to Semantic Architecture',
      content:
        'This system helps you visualize, validate, and improve your software architecture using semantic technologies.',
      action: 'Get Started',
    },
    {
      title: 'Connect Your Kthulu Project',
      content:
        'Import your existing Kthulu project or create a new one to begin semantic analysis.',
      action: 'Import Project',
    },
    {
      title: 'Explore the Semantic Graph',
      content:
        'View your architecture as an interactive graph with semantic relationships and validation.',
      action: 'Open Graph',
    },
    {
      title: 'Enable Intelligent Agents',
      content:
        'Activate reasoning, explanation, and generation agents to get intelligent assistance.',
      action: 'Configure Agents',
    },
    {
      title: 'Start Building',
      content:
        'Use the integrated tools to create modules, validate architecture, and generate code.',
      action: 'Start Tutorial',
    },
  ];

  const filteredHelpTopics = helpTopics.filter(
    (topic) =>
      topic.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      topic.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      topic.tags.some((tag) =>
        tag.toLowerCase().includes(searchQuery.toLowerCase())
      )
  );

  const startTutorial = (tutorial: Tutorial) => {
    setSelectedTutorial(tutorial);
    setCurrentStep(0);
  };

  const nextStep = () => {
    if (selectedTutorial && currentStep < selectedTutorial.steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const completeTutorial = () => {
    if (selectedTutorial) {
      setUserProgress((prev) => ({
        ...prev,
        [selectedTutorial.id]: true,
      }));
      setSelectedTutorial(null);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Help & Documentation</h1>
        <p className="text-muted-foreground">
          Learn semantic architecture, OWL concepts, and hexagonal design
          principles
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="tutorials" className="flex items-center gap-2">
            <PlayCircle className="w-4 h-4" />
            Tutorials
          </TabsTrigger>
          <TabsTrigger value="help" className="flex items-center gap-2">
            <HelpCircle className="w-4 h-4" />
            Help Topics
          </TabsTrigger>
          <TabsTrigger
            value="best-practices"
            className="flex items-center gap-2"
          >
            <Lightbulb className="w-4 h-4" />
            Best Practices
          </TabsTrigger>
          <TabsTrigger value="onboarding" className="flex items-center gap-2">
            <BookOpen className="w-4 h-4" />
            Getting Started
          </TabsTrigger>
        </TabsList>

        <TabsContent value="tutorials" className="mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {tutorials.map((tutorial) => (
              <Card
                key={tutorial.id}
                className="cursor-pointer hover:shadow-lg transition-shadow"
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-lg">{tutorial.title}</CardTitle>
                    {userProgress[tutorial.id] && (
                      <CheckCircle className="w-5 h-5 text-green-500" />
                    )}
                  </div>
                  <div className="flex gap-2 mt-2">
                    <Badge
                      variant={
                        tutorial.difficulty === 'beginner'
                          ? 'default'
                          : tutorial.difficulty === 'intermediate'
                            ? 'secondary'
                            : 'destructive'
                      }
                    >
                      {tutorial.difficulty}
                    </Badge>
                    <Badge variant="outline">{tutorial.duration}</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-4">
                    {tutorial.description}
                  </p>
                  <Button
                    onClick={() => startTutorial(tutorial)}
                    className="w-full"
                    variant={userProgress[tutorial.id] ? 'outline' : 'default'}
                  >
                    {userProgress[tutorial.id] ? 'Review' : 'Start Tutorial'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="help" className="mt-6">
          <div className="mb-4">
            <input
              type="text"
              placeholder="Search help topics..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full p-2 border rounded-md"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredHelpTopics.map((topic) => (
              <Card key={topic.id}>
                <CardHeader>
                  <CardTitle className="text-lg">{topic.title}</CardTitle>
                  <Badge variant="outline">{topic.category}</Badge>
                </CardHeader>
                <CardContent>
                  <p className="text-sm mb-4">{topic.content}</p>
                  {topic.examples && (
                    <div>
                      <h4 className="font-semibold mb-2">Examples:</h4>
                      <ul className="text-sm space-y-1">
                        {topic.examples.map((example, index) => (
                          <li key={index} className="text-muted-foreground">
                            • {example}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="best-practices" className="mt-6">
          <BestPracticesGuide />
        </TabsContent>

        <TabsContent value="onboarding" className="mt-6">
          <OnboardingWizard steps={onboardingSteps} />
        </TabsContent>
      </Tabs>

      {/* Tutorial Dialog */}
      {selectedTutorial && (
        <Dialog
          open={!!selectedTutorial}
          onOpenChange={() => setSelectedTutorial(null)}
        >
          <DialogContent className="max-w-4xl max-h-[80vh]">
            <DialogHeader>
              <DialogTitle>{selectedTutorial.title}</DialogTitle>
              <div className="flex items-center gap-2 mt-2">
                <Progress
                  value={
                    ((currentStep + 1) / selectedTutorial.steps.length) * 100
                  }
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground">
                  {currentStep + 1} / {selectedTutorial.steps.length}
                </span>
              </div>
            </DialogHeader>
            <ScrollArea className="max-h-[60vh]">
              <TutorialStep
                step={selectedTutorial.steps[currentStep]}
                onNext={nextStep}
                onPrev={prevStep}
                onComplete={completeTutorial}
                isFirst={currentStep === 0}
                isLast={currentStep === selectedTutorial.steps.length - 1}
              />
            </ScrollArea>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

// Tutorial Step Component
const TutorialStep: React.FC<{
  step: TutorialStep;
  onNext: () => void;
  onPrev: () => void;
  onComplete: () => void;
  isFirst: boolean;
  isLast: boolean;
}> = ({ step, onNext, onPrev, onComplete, isFirst, isLast }) => {
  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-4">{step.title}</h3>
      <div className="prose max-w-none mb-6">
        <p>{step.content}</p>
        {step.code && (
          <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto">
            <code>{step.code}</code>
          </pre>
        )}
        {step.interactive && step.action && (
          <div className="bg-blue-50 p-4 rounded-md border-l-4 border-blue-400">
            <p className="font-semibold text-blue-800">Interactive Step:</p>
            <p className="text-blue-700">{step.action}</p>
          </div>
        )}
      </div>
      <div className="flex justify-between">
        <Button onClick={onPrev} disabled={isFirst} variant="outline">
          Previous
        </Button>
        <Button
          onClick={isLast ? onComplete : onNext}
          className="flex items-center gap-2"
        >
          {isLast ? 'Complete' : 'Next'}
          {!isLast && <ArrowRight className="w-4 h-4" />}
        </Button>
      </div>
    </div>
  );
};

// Best Practices Guide Component
const BestPracticesGuide: React.FC = () => {
  const practices = [
    {
      category: 'Hexagonal Architecture',
      icon: <Layers className="w-6 h-6" />,
      items: [
        {
          title: 'Keep Domain Logic Pure',
          description:
            'Domain components should contain only business logic, no infrastructure concerns.',
          example:
            'Use cases should not directly call databases or external APIs.',
        },
        {
          title: 'Use Ports for Abstractions',
          description:
            'Define clear interfaces (ports) for external dependencies.',
          example:
            'Create a UserRepository port instead of using database classes directly.',
        },
        {
          title: 'Implement Adapters for Infrastructure',
          description:
            'Adapters implement ports and handle infrastructure concerns.',
          example: 'PostgreSQLUserRepository implements UserRepository port.',
        },
      ],
    },
    {
      category: 'Domain-Driven Design',
      icon: <GitBranch className="w-6 h-6" />,
      items: [
        {
          title: 'Define Clear Bounded Contexts',
          description:
            'Each module should represent a distinct business domain.',
          example: 'Separate User Management from Order Processing contexts.',
        },
        {
          title: 'Use Domain Events',
          description: 'Communicate between contexts using domain events.',
          example:
            'UserRegistered event triggers welcome email in Communication context.',
        },
        {
          title: 'Maintain Aggregate Consistency',
          description: 'Ensure entities belong to only one aggregate root.',
          example:
            'Order items should only be modified through the Order aggregate.',
        },
      ],
    },
    {
      category: 'Semantic Modeling',
      icon: <Code className="w-6 h-6" />,
      items: [
        {
          title: 'Use Meaningful IRIs',
          description: 'Create descriptive identifiers for ontology elements.',
          example: 'http://kthulu.io/ontology#UserManagementModule',
        },
        {
          title: 'Define Clear Relationships',
          description: 'Use specific object properties to model relationships.',
          example: 'definesUseCase, implementsPort, dependsOnModule',
        },
        {
          title: 'Validate Regularly',
          description: 'Run semantic validation after architectural changes.',
          example: 'Enable automatic validation on code commits.',
        },
      ],
    },
  ];

  return (
    <div className="space-y-6">
      {practices.map((category) => (
        <Card key={category.category}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {category.icon}
              {category.category}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {category.items.map((item, index) => (
                <div key={index} className="border-l-4 border-blue-400 pl-4">
                  <h4 className="font-semibold">{item.title}</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    {item.description}
                  </p>
                  <p className="text-sm bg-gray-50 p-2 rounded italic">
                    Example: {item.example}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

// Onboarding Wizard Component
const OnboardingWizard: React.FC<{ steps: any[] }> = ({ steps }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [completed, setCompleted] = useState(false);

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      setCompleted(true);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  if (completed) {
    return (
      <Card className="text-center p-8">
        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">
          Welcome to Semantic Architecture!
        </h2>
        <p className="text-muted-foreground mb-4">
          You're ready to start building with semantic-driven development.
        </p>
        <Button onClick={() => setCompleted(false)}>Restart Onboarding</Button>
      </Card>
    );
  }

  const step = steps[currentStep];

  return (
    <Card className="max-w-2xl mx-auto">
      <CardHeader>
        <div className="flex items-center justify-between mb-4">
          <CardTitle>{step.title}</CardTitle>
          <Badge variant="outline">
            Step {currentStep + 1} of {steps.length}
          </Badge>
        </div>
        <Progress value={((currentStep + 1) / steps.length) * 100} />
      </CardHeader>
      <CardContent>
        <p className="text-lg mb-6">{step.content}</p>
        <div className="flex justify-between">
          <Button
            onClick={prevStep}
            disabled={currentStep === 0}
            variant="outline"
          >
            Previous
          </Button>
          <Button onClick={nextStep}>
            {currentStep === steps.length - 1 ? 'Complete' : step.action}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default HelpSystem;
