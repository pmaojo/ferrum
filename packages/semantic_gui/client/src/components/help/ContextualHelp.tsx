import React, { useState, useContext, createContext, ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  HelpCircle,
  BookOpen,
  Lightbulb,
  Code,
  ExternalLink,
  X,
} from 'lucide-react';

interface HelpContent {
  id: string;
  title: string;
  description: string;
  content: string;
  category: 'owl' | 'architecture' | 'semantic' | 'kthulu' | 'ui';
  examples?: string[];
  relatedTopics?: string[];
  externalLinks?: { title: string; url: string }[];
}

interface ContextualHelpContextType {
  showHelp: (contentId: string) => void;
  hideHelp: () => void;
  isHelpVisible: boolean;
  currentHelpId: string | null;
}

const ContextualHelpContext = createContext<ContextualHelpContextType | null>(
  null
);

export const useContextualHelp = () => {
  const context = useContext(ContextualHelpContext);
  if (!context) {
    throw new Error(
      'useContextualHelp must be used within a ContextualHelpProvider'
    );
  }
  return context;
};

// Help content database
const helpContent: Record<string, HelpContent> = {
  'owl-classes': {
    id: 'owl-classes',
    title: 'OWL Classes',
    description: 'Understanding OWL classes in semantic architecture',
    content: `OWL classes represent concepts in your domain model. In Kthulu architecture, we use specific classes to represent different types of architectural components:

• **Module**: Represents a bounded context or module in your application
• **UseCase**: Represents a business use case or application service
• **Port**: Represents an interface or contract (dependency inversion)
• **Adapter**: Represents an implementation of a port (infrastructure layer)
• **DomainEntity**: Represents a domain entity with business logic
• **DomainEvent**: Represents a domain event for communication

These classes form the foundation of your semantic architecture model.`,
    category: 'owl',
    examples: [
      'kth:Module rdf:type owl:Class .',
      'kth:AuthModule rdf:type kth:Module .',
      'kth:LoginUseCase rdf:type kth:UseCase .',
    ],
    relatedTopics: ['object-properties', 'individuals', 'reasoning'],
    externalLinks: [
      {
        title: 'OWL 2 Web Ontology Language',
        url: 'https://www.w3.org/TR/owl2-overview/',
      },
    ],
  },
  'object-properties': {
    id: 'object-properties',
    title: 'Object Properties',
    description: 'Defining relationships between architectural components',
    content: `Object properties define relationships between individuals in your ontology. They specify how different architectural components relate to each other:

• **definesUseCase**: Links a module to its use cases
• **hasPort**: Links a module to its defined ports
• **implementsPort**: Links an adapter to the port it implements
• **usesPort**: Links a use case to ports it depends on
• **dependsOnModule**: Defines dependencies between modules
• **emitsEvent**: Links use cases to domain events they emit
• **handlesEvent**: Links adapters to domain events they handle

These relationships enable semantic reasoning about your architecture.`,
    category: 'owl',
    examples: [
      'kth:definesUseCase rdf:type owl:ObjectProperty .',
      'kth:AuthModule kth:definesUseCase kth:LoginUseCase .',
      'kth:DatabaseAdapter kth:implementsPort kth:UserRepository .',
    ],
    relatedTopics: ['owl-classes', 'reasoning', 'validation-rules'],
  },
  'dependency-inversion': {
    id: 'dependency-inversion',
    title: 'Dependency Inversion Principle',
    description: 'Understanding and applying DIP in hexagonal architecture',
    content: `The Dependency Inversion Principle (DIP) is a fundamental principle of hexagonal architecture:

**High-level modules should not depend on low-level modules. Both should depend on abstractions.**

In our semantic model:
• Domain components (UseCase, DomainEntity) should only depend on ports (abstractions)
• Infrastructure components (Adapters) implement ports but are not called directly
• This creates a clean separation between business logic and infrastructure concerns

The system automatically validates DIP compliance using semantic rules.`,
    category: 'architecture',
    examples: [
      '✅ UseCase → Port (Good: depends on abstraction)',
      '❌ UseCase → Adapter (Bad: depends on implementation)',
      '✅ Adapter implements Port (Good: provides implementation)',
    ],
    relatedTopics: [
      'hexagonal-architecture',
      'ports-adapters',
      'validation-rules',
    ],
  },
  'bounded-contexts': {
    id: 'bounded-contexts',
    title: 'Bounded Contexts',
    description:
      'Domain-Driven Design bounded contexts in modular architecture',
    content: `A bounded context is a central pattern in Domain-Driven Design that defines clear boundaries within which a particular domain model is defined and applicable:

• Each module represents a bounded context
• Entities and value objects are scoped to their context
• Cross-context communication happens through domain events
• Contexts should have minimal coupling and high cohesion

The semantic model enforces bounded context integrity by validating that entities don't cross context boundaries inappropriately.`,
    category: 'architecture',
    examples: [
      'User Management Context: User, UserRepository, RegisterUser',
      'Order Processing Context: Order, OrderRepository, ProcessOrder',
      'Communication via events: UserRegistered → SendWelcomeEmail',
    ],
    relatedTopics: ['domain-events', 'modules', 'ddd-principles'],
  },
  'semantic-reasoning': {
    id: 'semantic-reasoning',
    title: 'Semantic Reasoning',
    description: 'How automated reasoning validates your architecture',
    content: `Semantic reasoning uses formal logic to automatically validate your architecture against defined rules:

**Types of Reasoning:**
• **Classification**: Automatically categorizes components based on their properties
• **Consistency Checking**: Detects logical contradictions in your model
• **Rule Validation**: Checks compliance with architectural principles

**Reasoners Used:**
• **ELK**: Fast reasoning for basic classification and subsumption
• **HermiT/Pellet**: Complete reasoning for complex constraints and explanations

The system runs reasoning automatically when your architecture changes, providing immediate feedback on violations.`,
    category: 'semantic',
    examples: [
      'Detects when domain components call infrastructure directly',
      'Validates that entities belong to only one aggregate',
      'Ensures modules maintain proper boundaries',
    ],
    relatedTopics: ['validation-rules', 'owl-classes', 'agents'],
  },
  'kthulu-cli': {
    id: 'kthulu-cli',
    title: 'Kthulu CLI Integration',
    description: 'Using Kthulu CLI commands within the semantic environment',
    content: `The Kthulu CLI is integrated into the semantic architecture system, allowing you to generate and analyze code while maintaining semantic consistency:

**Key Commands:**
• **kthulu-cli plan --graph**: Exports your architecture as a semantic graph
• **kthulu-cli make:module**: Creates new modules following hexagonal principles
• **kthulu-cli validate**: Validates code against architectural rules

**Integration Features:**
• Real-time synchronization between code and semantic model
• Automatic validation after code generation
• Intelligent suggestions based on semantic analysis`,
    category: 'kthulu',
    examples: [
      'kthulu-cli plan --graph --format=json > architecture.json',
      'kthulu-cli make:module user-management',
      'kthulu-cli validate --semantic',
    ],
    relatedTopics: ['code-generation', 'synchronization', 'validation'],
  },
  agents: {
    id: 'agents',
    title: 'Intelligent Agents',
    description:
      'AI agents that assist with architecture analysis and improvement',
    content: `The system includes several intelligent agents that provide automated assistance:

**Reasoner Agent:**
• Continuously validates your architecture using OWL reasoning
• Detects violations of architectural principles
• Provides detailed validation reports

**Explanation Agent:**
• Converts formal validation results into human-readable explanations
• Provides context and suggestions for fixing violations
• Uses natural language processing to make complex concepts accessible

**Generation Assistant:**
• Suggests architectural improvements based on analysis
• Helps generate new components following best practices
• Integrates with Kthulu CLI for code generation`,
    category: 'semantic',
    examples: [
      'Reasoner detects DIP violation → Explanation agent explains why → Generation assistant suggests creating a port',
      'Automatic detection of missing bounded context boundaries',
      'Intelligent refactoring suggestions based on semantic analysis',
    ],
    relatedTopics: [
      'semantic-reasoning',
      'validation-rules',
      'code-generation',
    ],
  },
  'permagraph-sync': {
    id: 'permagraph-sync',
    title: 'Sincronizar con PermaGraph',
    description:
      'Cómo importar una ontología cuando el motor semántico está vacío',
    content: `Cuando no se ha cargado ninguna ontología verás el mensaje **"No hay ontología"**.
Utiliza el botón **"Sincronizar con PermaGraph"** para traer los datos desde tu proyecto Kthulu.`,
    category: 'semantic',
    relatedTopics: ['kthulu-cli', 'semantic-reasoning'],
  },
  'empty-graph': {
    id: 'empty-graph',
    title: 'Empty Graph Placeholder',
    description: 'Qué significa el mensaje cuando no hay nodos en el grafo',
    content: `Si \`useGraphData\` no devuelve nodos, la visualización muestra un placeholder en lugar de un lienzo vacío.
Sincroniza con PermaGraph o crea nuevos nodos para poblar el grafo.`,
    category: 'ui',
    relatedTopics: ['permagraph-sync'],
  },
};

// Contextual Help Provider
export const ContextualHelpProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [isHelpVisible, setIsHelpVisible] = useState(false);
  const [currentHelpId, setCurrentHelpId] = useState<string | null>(null);

  const showHelp = (contentId: string) => {
    setCurrentHelpId(contentId);
    setIsHelpVisible(true);
  };

  const hideHelp = () => {
    setIsHelpVisible(false);
    setCurrentHelpId(null);
  };

  return (
    <ContextualHelpContext.Provider
      value={{ showHelp, hideHelp, isHelpVisible, currentHelpId }}
    >
      {children}
      {isHelpVisible && currentHelpId && (
        <ContextualHelpModal
          content={helpContent[currentHelpId]}
          onClose={hideHelp}
        />
      )}
    </ContextualHelpContext.Provider>
  );
};

// Help Icon Component
export const HelpIcon: React.FC<{
  contentId: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'icon' | 'button';
}> = ({ contentId, size = 'md', variant = 'icon' }) => {
  const { showHelp } = useContextualHelp();
  const content = helpContent[contentId];

  if (!content) return null;

  const iconSize =
    size === 'sm' ? 'w-3 h-3' : size === 'md' ? 'w-4 h-4' : 'w-5 h-5';

  if (variant === 'button') {
    return (
      <Button
        variant="ghost"
        size="sm"
        onClick={() => showHelp(contentId)}
        className="h-auto p-1"
      >
        <HelpCircle className={iconSize} />
      </Button>
    );
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          onClick={() => showHelp(contentId)}
          className="inline-flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
        >
          <HelpCircle className={iconSize} />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="space-y-2">
          <h4 className="font-semibold">{content.title}</h4>
          <p className="text-sm text-muted-foreground">{content.description}</p>
          <Button
            size="sm"
            onClick={() => showHelp(contentId)}
            className="w-full"
          >
            Learn More
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
};

// Contextual Help Modal
const ContextualHelpModal: React.FC<{
  content: HelpContent;
  onClose: () => void;
}> = ({ content, onClose }) => {
  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5" />
              {content.title}
            </DialogTitle>
            <Badge variant="outline">{content.category}</Badge>
          </div>
        </DialogHeader>

        <ScrollArea className="max-h-[60vh]">
          <div className="space-y-6 p-1">
            <div className="prose max-w-none">
              <div className="whitespace-pre-line">{content.content}</div>
            </div>

            {content.examples && content.examples.length > 0 && (
              <div>
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <Code className="w-4 h-4" />
                  Examples
                </h4>
                <div className="space-y-2">
                  {content.examples.map((example, index) => (
                    <pre
                      key={index}
                      className="bg-gray-100 p-3 rounded-md text-sm overflow-x-auto"
                    >
                      <code>{example}</code>
                    </pre>
                  ))}
                </div>
              </div>
            )}

            {content.relatedTopics && content.relatedTopics.length > 0 && (
              <div>
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <Lightbulb className="w-4 h-4" />
                  Related Topics
                </h4>
                <div className="flex flex-wrap gap-2">
                  {content.relatedTopics.map((topicId) => {
                    const relatedContent = helpContent[topicId];
                    return relatedContent ? (
                      <Button
                        key={topicId}
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          // Switch to related topic
                          onClose();
                          setTimeout(() => {
                            const { showHelp } = useContextualHelp();
                            showHelp(topicId);
                          }, 100);
                        }}
                      >
                        {relatedContent.title}
                      </Button>
                    ) : null;
                  })}
                </div>
              </div>
            )}

            {content.externalLinks && content.externalLinks.length > 0 && (
              <div>
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <ExternalLink className="w-4 h-4" />
                  External Resources
                </h4>
                <div className="space-y-2">
                  {content.externalLinks.map((link, index) => (
                    <a
                      key={index}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-blue-600 hover:text-blue-800 text-sm"
                    >
                      <ExternalLink className="w-3 h-3" />
                      {link.title}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};

// Quick Help Tooltip Component
export const QuickHelp: React.FC<{
  title: string;
  content: string;
  children: ReactNode;
}> = ({ title, content, children }) => {
  return (
    <Popover>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="space-y-2">
          <h4 className="font-semibold">{title}</h4>
          <p className="text-sm text-muted-foreground">{content}</p>
        </div>
      </PopoverContent>
    </Popover>
  );
};

export default ContextualHelpProvider;
