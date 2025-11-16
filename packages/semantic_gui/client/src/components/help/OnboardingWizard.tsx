import React, { useState, useEffect } from 'react';
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
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  CheckCircle,
  ArrowRight,
  ArrowLeft,
  Rocket,
  BookOpen,
  Settings,
  Code,
  Play,
  Users,
  Lightbulb,
  Target,
  Zap,
} from 'lucide-react';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  content: React.ReactNode;
  icon: React.ReactNode;
  optional?: boolean;
  completed?: boolean;
  action?: {
    type: 'button' | 'form' | 'checklist' | 'tutorial';
    data?: any;
  };
}

interface OnboardingWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
}

const OnboardingWizard: React.FC<OnboardingWizardProps> = ({
  isOpen,
  onClose,
  onComplete,
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [userPreferences, setUserPreferences] = useState({
    role: '',
    experience: '',
    interests: [] as string[],
    projectType: '',
    notifications: true,
  });

  const steps: OnboardingStep[] = [
    {
      id: 'welcome',
      title: 'Welcome to Semantic Architecture',
      description:
        'Your journey to intelligent software architecture begins here',
      icon: <Rocket className="w-8 h-8 text-blue-500" />,
      content: (
        <div className="space-y-4">
          <div className="text-center">
            <div className="w-24 h-24 mx-auto mb-4 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
              <Rocket className="w-12 h-12 text-white" />
            </div>
            <h2 className="text-2xl font-bold mb-2">
              Welcome to the Future of Architecture
            </h2>
            <p className="text-muted-foreground max-w-md mx-auto">
              This system combines semantic technologies, AI agents, and
              hexagonal architecture to help you build better software with
              intelligent assistance.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <BookOpen className="w-8 h-8 text-blue-500 mx-auto mb-2" />
              <h3 className="font-semibold">Semantic Modeling</h3>
              <p className="text-sm text-muted-foreground">
                Formal representation of your architecture using OWL ontologies
              </p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <Zap className="w-8 h-8 text-green-500 mx-auto mb-2" />
              <h3 className="font-semibold">AI Agents</h3>
              <p className="text-sm text-muted-foreground">
                Intelligent reasoning, explanation, and code generation
                assistance
              </p>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <Target className="w-8 h-8 text-purple-500 mx-auto mb-2" />
              <h3 className="font-semibold">Hexagonal Architecture</h3>
              <p className="text-sm text-muted-foreground">
                Clean architecture with dependency inversion and ports &
                adapters
              </p>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'profile',
      title: 'Tell Us About Yourself',
      description: 'Help us customize your experience',
      icon: <Users className="w-8 h-8 text-green-500" />,
      action: { type: 'form' },
      content: (
        <div className="space-y-6">
          <div>
            <Label htmlFor="role">What's your primary role?</Label>
            <select
              id="role"
              className="w-full mt-1 p-2 border rounded-md"
              value={userPreferences.role}
              onChange={(e) =>
                setUserPreferences((prev) => ({
                  ...prev,
                  role: e.target.value,
                }))
              }
            >
              <option value="">Select your role</option>
              <option value="architect">Software Architect</option>
              <option value="developer">Developer</option>
              <option value="lead">Tech Lead</option>
              <option value="student">Student</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div>
            <Label htmlFor="experience">
              Experience with hexagonal architecture?
            </Label>
            <select
              id="experience"
              className="w-full mt-1 p-2 border rounded-md"
              value={userPreferences.experience}
              onChange={(e) =>
                setUserPreferences((prev) => ({
                  ...prev,
                  experience: e.target.value,
                }))
              }
            >
              <option value="">Select experience level</option>
              <option value="beginner">Beginner - New to the concept</option>
              <option value="intermediate">
                Intermediate - Some experience
              </option>
              <option value="advanced">
                Advanced - Experienced practitioner
              </option>
            </select>
          </div>

          <div>
            <Label>What interests you most? (Select all that apply)</Label>
            <div className="grid grid-cols-2 gap-2 mt-2">
              {[
                'Semantic modeling',
                'AI-assisted development',
                'Architecture validation',
                'Code generation',
                'Domain-driven design',
                'Clean architecture',
              ].map((interest) => (
                <div key={interest} className="flex items-center space-x-2">
                  <Checkbox
                    id={interest}
                    checked={userPreferences.interests.includes(interest)}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setUserPreferences((prev) => ({
                          ...prev,
                          interests: [...prev.interests, interest],
                        }));
                      } else {
                        setUserPreferences((prev) => ({
                          ...prev,
                          interests: prev.interests.filter(
                            (i) => i !== interest
                          ),
                        }));
                      }
                    }}
                  />
                  <Label htmlFor={interest} className="text-sm">
                    {interest}
                  </Label>
                </div>
              ))}
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'project-setup',
      title: 'Set Up Your First Project',
      description: 'Choose how you want to get started',
      icon: <Code className="w-8 h-8 text-purple-500" />,
      content: (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="cursor-pointer hover:shadow-lg transition-shadow border-2 hover:border-blue-500">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Play className="w-5 h-5" />
                  Start with Tutorial
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Learn the basics with an interactive tutorial that guides you
                  through creating your first semantic architecture.
                </p>
                <Badge variant="outline">Recommended for beginners</Badge>
              </CardContent>
            </Card>

            <Card className="cursor-pointer hover:shadow-lg transition-shadow border-2 hover:border-green-500">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Rocket className="w-5 h-5" />
                  Import Existing Project
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Import an existing Kthulu project or create a new one from
                  scratch using our templates.
                </p>
                <Badge variant="outline">For experienced users</Badge>
              </CardContent>
            </Card>
          </div>

          <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
            <div className="flex items-start gap-3">
              <Lightbulb className="w-5 h-5 text-yellow-600 mt-0.5" />
              <div>
                <h4 className="font-semibold text-yellow-800">Pro Tip</h4>
                <p className="text-sm text-yellow-700">
                  Even if you're experienced, we recommend starting with the
                  tutorial to understand how semantic modeling works in this
                  system.
                </p>
              </div>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'agents-setup',
      title: 'Configure AI Agents',
      description: 'Set up intelligent assistants for your workflow',
      icon: <Zap className="w-8 h-8 text-yellow-500" />,
      action: { type: 'checklist' },
      content: (
        <div className="space-y-6">
          <div className="text-center mb-6">
            <h3 className="text-lg font-semibold mb-2">
              Meet Your AI Assistants
            </h3>
            <p className="text-muted-foreground">
              These agents work together to analyze, validate, and improve your
              architecture
            </p>
          </div>

          <div className="space-y-4">
            <AgentCard
              name="Reasoner Agent"
              description="Validates your architecture against semantic rules and principles"
              features={[
                'Dependency Inversion Principle validation',
                'Bounded context integrity checking',
                'SOLID principles enforcement',
              ]}
              enabled={true}
              onToggle={() => {}}
            />

            <AgentCard
              name="Explanation Agent"
              description="Provides human-readable explanations of validation results"
              features={[
                'Natural language explanations',
                'Contextual help and suggestions',
                'Learning-oriented feedback',
              ]}
              enabled={true}
              onToggle={() => {}}
            />

            <AgentCard
              name="Generation Assistant"
              description="Helps generate code and architectural improvements"
              features={[
                'Code generation suggestions',
                'Refactoring recommendations',
                'Best practice guidance',
              ]}
              enabled={false}
              optional={true}
              onToggle={() => {}}
            />
          </div>
        </div>
      ),
    },
    {
      id: 'quick-tour',
      title: 'Quick Interface Tour',
      description: 'Learn about the main features and navigation',
      icon: <BookOpen className="w-8 h-8 text-indigo-500" />,
      content: (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-4">
              <h3 className="font-semibold">Main Features</h3>
              <div className="space-y-3">
                <FeatureItem
                  icon="🎯"
                  title="Graph Editor"
                  description="Visual architecture modeling with React Flow"
                />
                <FeatureItem
                  icon="🤖"
                  title="Agent Dashboard"
                  description="Control and monitor your AI assistants"
                />
                <FeatureItem
                  icon="📊"
                  title="Validation Panel"
                  description="View architectural violations and suggestions"
                />
                <FeatureItem
                  icon="🔍"
                  title="SPARQL Queries"
                  description="Semantic search and analysis tools"
                />
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="font-semibold">Navigation Tips</h3>
              <div className="space-y-3">
                <TipItem tip="Use Ctrl+K to open the command palette" />
                <TipItem tip="Right-click nodes for context menus" />
                <TipItem tip="Press ? for keyboard shortcuts" />
                <TipItem tip="Use the help icon (?) for contextual help" />
              </div>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'completion',
      title: "You're All Set!",
      description: 'Ready to start building semantic architecture',
      icon: <CheckCircle className="w-8 h-8 text-green-500" />,
      content: (
        <div className="text-center space-y-6">
          <div className="w-24 h-24 mx-auto mb-4 bg-gradient-to-br from-green-500 to-blue-600 rounded-full flex items-center justify-center">
            <CheckCircle className="w-12 h-12 text-white" />
          </div>

          <div>
            <h2 className="text-2xl font-bold mb-2">Welcome Aboard! 🎉</h2>
            <p className="text-muted-foreground max-w-md mx-auto">
              You're now ready to start building with semantic-driven
              architecture. Your AI agents are configured and ready to assist
              you.
            </p>
          </div>

          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="font-semibold mb-2">What's Next?</h3>
            <div className="text-sm space-y-2">
              <p>• Start with the interactive tutorial to learn the basics</p>
              <p>• Import or create your first project</p>
              <p>• Explore the graph editor and semantic validation</p>
              <p>• Join our community for tips and best practices</p>
            </div>
          </div>

          <div className="flex justify-center gap-3">
            <Button variant="outline">View Documentation</Button>
            <Button>Start Tutorial</Button>
          </div>
        </div>
      ),
    },
  ];

  const currentStepData = steps[currentStep];
  const progress = ((currentStep + 1) / steps.length) * 100;

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCompletedSteps((prev) => new Set([...prev, currentStepData.id]));
      setCurrentStep(currentStep + 1);
    } else {
      onComplete();
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const skipOnboarding = () => {
    onClose();
  };

  const canProceed = () => {
    if (currentStepData.action?.type === 'form') {
      return userPreferences.role && userPreferences.experience;
    }
    return true;
  };

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              {currentStepData.icon}
              Getting Started
            </DialogTitle>
            <Badge variant="outline">
              Step {currentStep + 1} of {steps.length}
            </Badge>
          </div>
          <Progress value={progress} className="mt-2" />
        </DialogHeader>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl mx-auto">
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold mb-2">
                {currentStepData.title}
              </h1>
              <p className="text-muted-foreground">
                {currentStepData.description}
              </p>
            </div>

            {currentStepData.content}
          </div>
        </div>

        <div className="flex justify-between items-center p-6 border-t">
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={prevStep}
              disabled={currentStep === 0}
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              Previous
            </Button>
            <Button variant="ghost" onClick={skipOnboarding}>
              Skip Setup
            </Button>
          </div>

          <Button
            onClick={nextStep}
            disabled={!canProceed()}
            className="flex items-center gap-2"
          >
            {currentStep === steps.length - 1 ? 'Get Started' : 'Next'}
            {currentStep !== steps.length - 1 && (
              <ArrowRight className="w-4 h-4" />
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

const AgentCard: React.FC<{
  name: string;
  description: string;
  features: string[];
  enabled: boolean;
  optional?: boolean;
  onToggle: () => void;
}> = ({ name, description, features, enabled, optional, onToggle }) => {
  return (
    <Card
      className={`${enabled ? 'border-green-200 bg-green-50' : 'border-gray-200'}`}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{name}</CardTitle>
          <div className="flex items-center gap-2">
            {optional && <Badge variant="outline">Optional</Badge>}
            <Checkbox checked={enabled} onCheckedChange={onToggle} />
          </div>
        </div>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardHeader>
      <CardContent className="pt-0">
        <ul className="text-sm space-y-1">
          {features.map((feature, index) => (
            <li key={index} className="flex items-center gap-2">
              <CheckCircle className="w-3 h-3 text-green-500" />
              {feature}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
};

const FeatureItem: React.FC<{
  icon: string;
  title: string;
  description: string;
}> = ({ icon, title, description }) => {
  return (
    <div className="flex items-start gap-3">
      <span className="text-2xl">{icon}</span>
      <div>
        <h4 className="font-medium">{title}</h4>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
};

const TipItem: React.FC<{ tip: string }> = ({ tip }) => {
  return (
    <div className="flex items-start gap-2">
      <Lightbulb className="w-4 h-4 text-yellow-500 mt-0.5" />
      <p className="text-sm">{tip}</p>
    </div>
  );
};

export default OnboardingWizard;
