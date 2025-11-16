import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  ArrowRight,
  ArrowLeft,
  CheckCircle,
  PlayCircle,
  Target,
  MousePointer,
  Keyboard,
  Eye,
  X,
} from 'lucide-react';

interface TutorialStep {
  id: string;
  title: string;
  content: string;
  type: 'info' | 'action' | 'highlight' | 'input' | 'validation';
  target?: string; // CSS selector for element to highlight
  position?: 'top' | 'bottom' | 'left' | 'right';
  action?: {
    type: 'click' | 'input' | 'navigate' | 'wait';
    description: string;
    validation?: () => boolean;
  };
  code?: string;
  tips?: string[];
}

interface Tutorial {
  id: string;
  title: string;
  description: string;
  category: 'getting-started' | 'semantic' | 'architecture' | 'advanced';
  estimatedTime: string;
  prerequisites?: string[];
  steps: TutorialStep[];
}

interface InteractiveTutorialProps {
  tutorial: Tutorial;
  isOpen: boolean;
  onClose: () => void;
  onComplete: (tutorialId: string) => void;
}

const InteractiveTutorial: React.FC<InteractiveTutorialProps> = ({
  tutorial,
  isOpen,
  onClose,
  onComplete,
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);
  const [highlightedElement, setHighlightedElement] =
    useState<HTMLElement | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const currentStepData = tutorial.steps[currentStep];
  const progress = ((currentStep + 1) / tutorial.steps.length) * 100;

  useEffect(() => {
    if (isOpen && currentStepData?.target) {
      highlightElement(currentStepData.target);
    } else {
      clearHighlight();
    }

    return () => clearHighlight();
  }, [isOpen, currentStep, currentStepData]);

  const highlightElement = (selector: string) => {
    try {
      const element = document.querySelector(selector) as HTMLElement;
      if (element) {
        setHighlightedElement(element);

        // Add highlight overlay
        const rect = element.getBoundingClientRect();
        if (overlayRef.current) {
          overlayRef.current.style.display = 'block';
          overlayRef.current.style.top = `${rect.top + window.scrollY}px`;
          overlayRef.current.style.left = `${rect.left + window.scrollX}px`;
          overlayRef.current.style.width = `${rect.width}px`;
          overlayRef.current.style.height = `${rect.height}px`;
        }

        // Scroll element into view
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    } catch (error) {
      console.warn('Could not highlight element:', selector, error);
    }
  };

  const clearHighlight = () => {
    setHighlightedElement(null);
    if (overlayRef.current) {
      overlayRef.current.style.display = 'none';
    }
  };

  const nextStep = () => {
    if (currentStep < tutorial.steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      completeTutorial();
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const completeTutorial = () => {
    setIsCompleted(true);
    clearHighlight();
    onComplete(tutorial.id);
  };

  const skipTutorial = () => {
    clearHighlight();
    onClose();
  };

  const restartTutorial = () => {
    setCurrentStep(0);
    setIsCompleted(false);
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Highlight Overlay */}
      <div
        ref={overlayRef}
        className="fixed z-[9999] pointer-events-none border-4 border-blue-500 bg-blue-500/10 rounded-lg shadow-lg"
        style={{ display: 'none' }}
      />

      {/* Tutorial Dialog */}
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-2xl max-h-[80vh] z-[10000]">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle className="flex items-center gap-2">
                <PlayCircle className="w-5 h-5" />
                {tutorial.title}
              </DialogTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline">{tutorial.category}</Badge>
                <Button variant="ghost" size="sm" onClick={skipTutorial}>
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>
            <div className="flex items-center gap-4 mt-2">
              <Progress value={progress} className="flex-1" />
              <span className="text-sm text-muted-foreground">
                {currentStep + 1} / {tutorial.steps.length}
              </span>
            </div>
          </DialogHeader>

          {isCompleted ? (
            <TutorialComplete
              tutorial={tutorial}
              onRestart={restartTutorial}
              onClose={onClose}
            />
          ) : (
            <TutorialStepContent
              step={currentStepData}
              stepNumber={currentStep + 1}
              totalSteps={tutorial.steps.length}
              onNext={nextStep}
              onPrev={prevStep}
              onSkip={skipTutorial}
              isFirst={currentStep === 0}
              isLast={currentStep === tutorial.steps.length - 1}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

const TutorialStepContent: React.FC<{
  step: TutorialStep;
  stepNumber: number;
  totalSteps: number;
  onNext: () => void;
  onPrev: () => void;
  onSkip: () => void;
  isFirst: boolean;
  isLast: boolean;
}> = ({
  step,
  stepNumber,
  totalSteps,
  onNext,
  onPrev,
  onSkip,
  isFirst,
  isLast,
}) => {
  const [actionCompleted, setActionCompleted] = useState(false);

  useEffect(() => {
    if (step.action?.validation) {
      const checkValidation = () => {
        if (step.action?.validation?.()) {
          setActionCompleted(true);
        }
      };

      const interval = setInterval(checkValidation, 1000);
      return () => clearInterval(interval);
    }
  }, [step]);

  const getStepIcon = () => {
    switch (step.type) {
      case 'action':
        return <MousePointer className="w-5 h-5 text-blue-500" />;
      case 'input':
        return <Keyboard className="w-5 h-5 text-green-500" />;
      case 'highlight':
        return <Eye className="w-5 h-5 text-yellow-500" />;
      case 'validation':
        return <Target className="w-5 h-5 text-purple-500" />;
      default:
        return <CheckCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  return (
    <div className="space-y-6 p-4">
      <div className="flex items-start gap-3">
        {getStepIcon()}
        <div className="flex-1">
          <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
          <div className="prose max-w-none text-sm">
            <p>{step.content}</p>
          </div>
        </div>
      </div>

      {step.action && (
        <Card className="bg-blue-50 border-blue-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Target className="w-4 h-4" />
              Action Required
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="text-sm mb-3">{step.action.description}</p>
            {actionCompleted && (
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="w-4 h-4" />
                <span className="text-sm font-medium">Action completed!</span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {step.code && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Code Example</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="bg-gray-100 p-3 rounded-md text-sm overflow-x-auto">
              <code>{step.code}</code>
            </pre>
          </CardContent>
        </Card>
      )}

      {step.tips && step.tips.length > 0 && (
        <Card className="bg-yellow-50 border-yellow-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              💡 Tips
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <ul className="text-sm space-y-1">
              {step.tips.map((tip, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-yellow-600">•</span>
                  <span>{tip}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-between items-center pt-4 border-t">
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onPrev}
            disabled={isFirst}
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Previous
          </Button>
          <Button variant="ghost" size="sm" onClick={onSkip}>
            Skip Tutorial
          </Button>
        </div>

        <Button
          onClick={onNext}
          disabled={step.action?.validation && !actionCompleted}
          className="flex items-center gap-2"
        >
          {isLast ? 'Complete' : 'Next'}
          {!isLast && <ArrowRight className="w-4 h-4" />}
        </Button>
      </div>
    </div>
  );
};

const TutorialComplete: React.FC<{
  tutorial: Tutorial;
  onRestart: () => void;
  onClose: () => void;
}> = ({ tutorial, onRestart, onClose }) => {
  return (
    <div className="text-center p-8 space-y-6">
      <div className="flex justify-center">
        <CheckCircle className="w-16 h-16 text-green-500" />
      </div>

      <div>
        <h2 className="text-2xl font-bold mb-2">Tutorial Complete!</h2>
        <p className="text-muted-foreground">
          You've successfully completed "{tutorial.title}". You're now ready to
          apply these concepts in your projects.
        </p>
      </div>

      <div className="flex justify-center gap-3">
        <Button variant="outline" onClick={onRestart}>
          Restart Tutorial
        </Button>
        <Button onClick={onClose}>Continue Building</Button>
      </div>
    </div>
  );
};

// Tutorial definitions
export const tutorialDefinitions: Tutorial[] = [
  {
    id: 'first-semantic-graph',
    title: 'Create Your First Semantic Graph',
    description: 'Learn to create and visualize a semantic architecture graph',
    category: 'getting-started',
    estimatedTime: '10 minutes',
    steps: [
      {
        id: 'welcome',
        title: 'Welcome to Semantic Architecture',
        content:
          "In this tutorial, you'll learn how to create your first semantic architecture graph. We'll start with a simple module and build up to a complete architecture.",
        type: 'info',
      },
      {
        id: 'open-graph-editor',
        title: 'Open the Graph Editor',
        content:
          "First, let's open the graph editor where you can visualize and edit your architecture.",
        type: 'action',
        target: '[data-testid="graph-editor-button"]',
        action: {
          type: 'click',
          description: 'Click on the "Graph Editor" button in the navigation',
          validation: () =>
            document.querySelector('[data-testid="graph-editor"]') !== null,
        },
      },
      {
        id: 'create-module',
        title: 'Create Your First Module',
        content:
          "Now let's create a module node. Modules represent bounded contexts in your architecture.",
        type: 'action',
        target: '[data-testid="add-node-button"]',
        action: {
          type: 'click',
          description: 'Click the "Add Node" button and select "Module"',
          validation: () =>
            document.querySelectorAll('[data-node-type="module"]').length > 0,
        },
        tips: [
          'Modules should represent distinct business domains',
          'Keep modules loosely coupled and highly cohesive',
        ],
      },
      {
        id: 'add-use-case',
        title: 'Add a Use Case',
        content:
          'Every module should define at least one use case. Use cases represent business operations.',
        type: 'action',
        target: '[data-testid="add-node-button"]',
        action: {
          type: 'click',
          description: 'Add a UseCase node and connect it to your module',
          validation: () =>
            document.querySelectorAll('[data-node-type="usecase"]').length > 0,
        },
      },
      {
        id: 'validate-architecture',
        title: 'Validate Your Architecture',
        content:
          "Let's run semantic validation to ensure your architecture follows best practices.",
        type: 'action',
        target: '[data-testid="validate-button"]',
        action: {
          type: 'click',
          description: 'Click the "Validate" button to run semantic validation',
        },
      },
    ],
  },
  {
    id: 'owl-ontology-basics',
    title: 'Understanding OWL Ontologies',
    description:
      'Learn the fundamentals of OWL ontologies and how they model your architecture',
    category: 'semantic',
    estimatedTime: '15 minutes',
    steps: [
      {
        id: 'owl-intro',
        title: 'What is OWL?',
        content:
          'OWL (Web Ontology Language) is a semantic web language designed to represent rich and complex knowledge about things, groups of things, and relations between things.',
        type: 'info',
        code: `# Example OWL Class
kth:Module rdf:type owl:Class .
kth:UseCase rdf:type owl:Class .

# Example Individual
kth:UserModule rdf:type kth:Module .`,
      },
      {
        id: 'classes-individuals',
        title: 'Classes vs Individuals',
        content:
          'Classes represent concepts (like Module, UseCase) while individuals are specific instances of those classes (like UserModule, LoginUseCase).',
        type: 'info',
        tips: [
          'Classes are like blueprints, individuals are like actual buildings',
          'You can have many individuals of the same class',
          'Classes can have subclasses (inheritance)',
        ],
      },
      {
        id: 'object-properties',
        title: 'Object Properties Define Relationships',
        content:
          'Object properties define how individuals relate to each other. They\'re the "verbs" of your ontology.',
        type: 'info',
        code: `# Object Property Definition
kth:definesUseCase rdf:type owl:ObjectProperty ;
    rdfs:domain kth:Module ;
    rdfs:range kth:UseCase .

# Usage
kth:UserModule kth:definesUseCase kth:RegisterUser .`,
      },
    ],
  },
  {
    id: 'hexagonal-architecture',
    title: 'Hexagonal Architecture Principles',
    description:
      'Master the principles of hexagonal architecture and ports & adapters',
    category: 'architecture',
    estimatedTime: '20 minutes',
    steps: [
      {
        id: 'hexagonal-intro',
        title: 'Introduction to Hexagonal Architecture',
        content:
          'Hexagonal architecture, also known as Ports and Adapters, isolates the core business logic from external concerns.',
        type: 'info',
        tips: [
          'The "hexagon" shape is just a metaphor - you can have any number of sides',
          'The key is the separation between inside (domain) and outside (infrastructure)',
          'Ports are interfaces, adapters are implementations',
        ],
      },
      {
        id: 'dependency-inversion',
        title: 'Dependency Inversion Principle',
        content:
          'High-level modules should not depend on low-level modules. Both should depend on abstractions.',
        type: 'info',
        code: `// ❌ Bad: UseCase depends on concrete implementation
class RegisterUser {
    constructor(private db: PostgreSQLUserRepository) {}
}

// ✅ Good: UseCase depends on abstraction
class RegisterUser {
    constructor(private userRepo: UserRepository) {}
}`,
      },
      {
        id: 'identify-violations',
        title: 'Identify DIP Violations',
        content:
          "Let's look at your current architecture and identify any dependency inversion violations.",
        type: 'action',
        target: '[data-testid="violations-panel"]',
        action: {
          type: 'click',
          description:
            'Open the violations panel to see any architectural issues',
        },
      },
    ],
  },
];

export default InteractiveTutorial;
