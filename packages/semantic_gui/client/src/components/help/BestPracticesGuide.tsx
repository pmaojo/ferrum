import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  ChevronDown,
  ChevronRight,
  CheckCircle,
  XCircle,
  Lightbulb,
  Code,
  GitBranch,
  Layers,
  Database,
  Shield,
  Zap,
  BookOpen,
  AlertTriangle,
  Target,
} from 'lucide-react';

interface BestPractice {
  id: string;
  title: string;
  description: string;
  category:
    | 'hexagonal'
    | 'ddd'
    | 'semantic'
    | 'solid'
    | 'testing'
    | 'performance';
  level: 'essential' | 'recommended' | 'advanced';
  examples: {
    good?: string[];
    bad?: string[];
    code?: string;
  };
  tips: string[];
  relatedPrinciples?: string[];
  commonMistakes?: string[];
}

const BestPracticesGuide: React.FC = () => {
  const [activeCategory, setActiveCategory] = useState('hexagonal');
  const [expandedPractices, setExpandedPractices] = useState<Set<string>>(
    new Set()
  );

  const togglePractice = (practiceId: string) => {
    setExpandedPractices((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(practiceId)) {
        newSet.delete(practiceId);
      } else {
        newSet.add(practiceId);
      }
      return newSet;
    });
  };

  const bestPractices: BestPractice[] = [
    {
      id: 'dependency-inversion',
      title: 'Apply Dependency Inversion Principle',
      description:
        'High-level modules should not depend on low-level modules. Both should depend on abstractions.',
      category: 'hexagonal',
      level: 'essential',
      examples: {
        bad: [
          'Use cases directly importing database adapters',
          'Domain entities depending on infrastructure classes',
          'Business logic mixed with HTTP handling',
        ],
        good: [
          'Use cases depending only on port interfaces',
          'Adapters implementing ports without domain knowledge',
          'Clean separation between domain and infrastructure',
        ],
        code: `// ❌ Bad: Direct dependency on infrastructure
class RegisterUserUseCase {
    constructor(private db: PostgreSQLUserRepository) {}
    
    async execute(userData: UserData) {
        // Business logic mixed with infrastructure concerns
        const user = await this.db.save(userData);
        return user;
    }
}

// ✅ Good: Dependency on abstraction
class RegisterUserUseCase {
    constructor(private userRepo: UserRepository) {}
    
    async execute(userData: UserData) {
        // Pure business logic
        const user = new User(userData);
        await this.userRepo.save(user);
        return user;
    }
}`,
      },
      tips: [
        'Define ports (interfaces) for all external dependencies',
        'Keep domain logic free from infrastructure concerns',
        'Use dependency injection to provide implementations',
        'Test with mock implementations of ports',
      ],
      relatedPrinciples: ['Single Responsibility', 'Open/Closed Principle'],
      commonMistakes: [
        'Importing concrete classes in use cases',
        'Mixing business rules with data access logic',
        'Creating circular dependencies between layers',
      ],
    },
    {
      id: 'bounded-contexts',
      title: 'Define Clear Bounded Contexts',
      description:
        'Each module should represent a distinct business domain with clear boundaries.',
      category: 'ddd',
      level: 'essential',
      examples: {
        good: [
          'User Management: User, UserRepository, RegisterUser',
          'Order Processing: Order, OrderRepository, ProcessOrder',
          'Inventory: Product, Stock, UpdateInventory',
        ],
        bad: [
          'Mixing user and order entities in the same module',
          'Sharing domain objects across contexts',
          'Cross-context direct database access',
        ],
        code: `// ✅ Good: Clear bounded context
module UserManagement {
    // Domain entities scoped to this context
    class User { ... }
    class UserProfile { ... }
    
    // Use cases specific to user management
    class RegisterUser { ... }
    class UpdateProfile { ... }
    
    // Ports for external dependencies
    interface UserRepository { ... }
    interface EmailService { ... }
}

// ✅ Good: Separate bounded context
module OrderProcessing {
    // Different User concept for orders
    class OrderCustomer { ... }
    class Order { ... }
    
    // Order-specific operations
    class ProcessOrder { ... }
    class CancelOrder { ... }
}`,
      },
      tips: [
        'Each context should have its own model of shared concepts',
        'Use domain events for cross-context communication',
        'Avoid sharing entities between contexts',
        'Keep contexts loosely coupled and highly cohesive',
      ],
      relatedPrinciples: ['Single Responsibility', 'Domain Events'],
      commonMistakes: [
        'Creating god objects that span multiple contexts',
        'Direct method calls between contexts',
        'Sharing database tables across contexts',
      ],
    },
    {
      id: 'ports-adapters',
      title: 'Implement Ports and Adapters Pattern',
      description:
        'Use ports (interfaces) to define contracts and adapters to implement them.',
      category: 'hexagonal',
      level: 'essential',
      examples: {
        code: `// Port (Interface) - defines the contract
interface UserRepository {
    save(user: User): Promise<User>;
    findById(id: string): Promise<User | null>;
    findByEmail(email: string): Promise<User | null>;
}

// Adapter - implements the port
class PostgreSQLUserRepository implements UserRepository {
    constructor(private db: Database) {}
    
    async save(user: User): Promise<User> {
        // PostgreSQL-specific implementation
        const result = await this.db.query(
            'INSERT INTO users (id, email, name) VALUES ($1, $2, $3)',
            [user.id, user.email, user.name]
        );
        return user;
    }
    
    async findById(id: string): Promise<User | null> {
        // Implementation details hidden from domain
        const result = await this.db.query(
            'SELECT * FROM users WHERE id = $1',
            [id]
        );
        return result.rows[0] ? new User(result.rows[0]) : null;
    }
}

// Alternative adapter for testing
class InMemoryUserRepository implements UserRepository {
    private users: Map<string, User> = new Map();
    
    async save(user: User): Promise<User> {
        this.users.set(user.id, user);
        return user;
    }
    
    async findById(id: string): Promise<User | null> {
        return this.users.get(id) || null;
    }
}`,
      },
      tips: [
        'Keep ports simple and focused on business needs',
        'Adapters should handle all infrastructure complexity',
        'Create multiple adapters for different implementations',
        'Use adapters for testing with in-memory implementations',
      ],
      relatedPrinciples: ['Dependency Inversion', 'Interface Segregation'],
      commonMistakes: [
        'Making ports too complex or infrastructure-aware',
        'Leaking adapter implementation details into domain',
        'Creating adapters that know about business rules',
      ],
    },
    {
      id: 'domain-events',
      title: 'Use Domain Events for Decoupling',
      description:
        'Communicate between bounded contexts using domain events instead of direct calls.',
      category: 'ddd',
      level: 'recommended',
      examples: {
        code: `// Domain Event
class UserRegistered {
    constructor(
        public readonly userId: string,
        public readonly email: string,
        public readonly occurredAt: Date = new Date()
    ) {}
}

// Publishing events from use case
class RegisterUserUseCase {
    constructor(
        private userRepo: UserRepository,
        private eventBus: EventBus
    ) {}
    
    async execute(userData: UserData): Promise<User> {
        const user = new User(userData);
        await this.userRepo.save(user);
        
        // Publish domain event
        await this.eventBus.publish(
            new UserRegistered(user.id, user.email)
        );
        
        return user;
    }
}

// Event handler in different context
class SendWelcomeEmailHandler {
    constructor(private emailService: EmailService) {}
    
    async handle(event: UserRegistered): Promise<void> {
        await this.emailService.sendWelcomeEmail(
            event.email,
            event.userId
        );
    }
}`,
      },
      tips: [
        'Events should represent business facts, not technical operations',
        'Use past tense for event names (UserRegistered, not RegisterUser)',
        'Keep events immutable and serializable',
        'Handle events asynchronously when possible',
      ],
      relatedPrinciples: ['Bounded Contexts', 'Loose Coupling'],
      commonMistakes: [
        'Making events too granular or too coarse',
        'Including mutable objects in events',
        'Creating tight coupling through event data',
      ],
    },
    {
      id: 'semantic-modeling',
      title: 'Create Meaningful Semantic Models',
      description:
        'Use descriptive IRIs and clear relationships in your ontology.',
      category: 'semantic',
      level: 'recommended',
      examples: {
        code: `# ✅ Good: Descriptive IRIs and clear relationships
@prefix kth: <http://kthulu.io/ontology#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

# Clear class definitions
kth:UserManagementModule rdf:type kth:Module ;
    rdfs:label "User Management Module" ;
    rdfs:comment "Handles user registration, authentication, and profile management" .

kth:RegisterUserUseCase rdf:type kth:UseCase ;
    rdfs:label "Register User Use Case" ;
    kth:belongsToModule kth:UserManagementModule ;
    kth:usesPort kth:UserRepositoryPort .

# Specific relationship properties
kth:UserRepositoryPort rdf:type kth:Port ;
    rdfs:label "User Repository Port" ;
    kth:definedByModule kth:UserManagementModule .

kth:PostgreSQLUserAdapter rdf:type kth:Adapter ;
    rdfs:label "PostgreSQL User Adapter" ;
    kth:implementsPort kth:UserRepositoryPort .`,
      },
      tips: [
        'Use meaningful names for classes and properties',
        'Include rdfs:label and rdfs:comment for documentation',
        'Create specific relationship properties instead of generic ones',
        'Use consistent naming conventions across your ontology',
      ],
      relatedPrinciples: ['Clear Communication', 'Documentation'],
      commonMistakes: [
        'Using generic or cryptic names',
        'Missing documentation in the ontology',
        'Inconsistent naming patterns',
      ],
    },
    {
      id: 'validation-rules',
      title: 'Define Comprehensive Validation Rules',
      description:
        'Create semantic rules that enforce architectural principles automatically.',
      category: 'semantic',
      level: 'advanced',
      examples: {
        code: `# SHACL shapes for validation
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix kth: <http://kthulu.io/ontology#> .

# DIP Validation: Domain components cannot call infrastructure
kth:DIPValidationShape rdf:type sh:NodeShape ;
    sh:targetClass kth:DomainComponent ;
    sh:property [
        sh:path kth:calls ;
        sh:class kth:InfrastructureComponent ;
        sh:maxCount 0 ;
        sh:message "Domain components cannot directly call infrastructure components (DIP violation)" ;
        sh:severity sh:Violation ;
    ] .

# Module completeness: Every module must have at least one use case
kth:ModuleCompletenessShape rdf:type sh:NodeShape ;
    sh:targetClass kth:Module ;
    sh:property [
        sh:path kth:definesUseCase ;
        sh:minCount 1 ;
        sh:message "Every module must define at least one use case" ;
        sh:severity sh:Warning ;
    ] .

# Aggregate integrity: Entity belongs to at most one aggregate
kth:AggregateIntegrityShape rdf:type sh:NodeShape ;
    sh:targetClass kth:DomainEntity ;
    sh:property [
        sh:path kth:partOfAggregate ;
        sh:maxCount 1 ;
        sh:message "Domain entity can belong to at most one aggregate" ;
        sh:severity sh:Violation ;
    ] .`,
      },
      tips: [
        'Start with essential architectural principles',
        'Use appropriate severity levels (Violation, Warning, Info)',
        'Provide clear, actionable error messages',
        'Test validation rules with both valid and invalid examples',
      ],
      relatedPrinciples: ['Automated Testing', 'Continuous Validation'],
      commonMistakes: [
        'Creating rules that are too strict or too lenient',
        'Writing unclear or unhelpful error messages',
        'Not testing validation rules thoroughly',
      ],
    },
    {
      id: 'testing-strategy',
      title: 'Implement Comprehensive Testing',
      description:
        'Test each layer independently using appropriate testing strategies.',
      category: 'testing',
      level: 'essential',
      examples: {
        code: `// Unit test for use case (domain logic)
describe('RegisterUserUseCase', () => {
    let useCase: RegisterUserUseCase;
    let mockUserRepo: jest.Mocked<UserRepository>;
    let mockEventBus: jest.Mocked<EventBus>;
    
    beforeEach(() => {
        mockUserRepo = {
            save: jest.fn(),
            findByEmail: jest.fn()
        };
        mockEventBus = {
            publish: jest.fn()
        };
        useCase = new RegisterUserUseCase(mockUserRepo, mockEventBus);
    });
    
    it('should register a new user successfully', async () => {
        // Arrange
        const userData = { email: 'test@example.com', name: 'Test User' };
        mockUserRepo.findByEmail.mockResolvedValue(null);
        mockUserRepo.save.mockResolvedValue(new User(userData));
        
        // Act
        const result = await useCase.execute(userData);
        
        // Assert
        expect(result).toBeInstanceOf(User);
        expect(mockUserRepo.save).toHaveBeenCalledWith(expect.any(User));
        expect(mockEventBus.publish).toHaveBeenCalledWith(
            expect.any(UserRegistered)
        );
    });
});

// Integration test for adapter
describe('PostgreSQLUserRepository', () => {
    let repository: PostgreSQLUserRepository;
    let testDb: TestDatabase;
    
    beforeEach(async () => {
        testDb = await createTestDatabase();
        repository = new PostgreSQLUserRepository(testDb);
    });
    
    it('should save and retrieve user correctly', async () => {
        // Arrange
        const user = new User({ email: 'test@example.com', name: 'Test' });
        
        // Act
        await repository.save(user);
        const retrieved = await repository.findById(user.id);
        
        // Assert
        expect(retrieved).toEqual(user);
    });
});`,
      },
      tips: [
        'Test domain logic in isolation using mocks',
        'Use integration tests for adapters with real dependencies',
        'Test semantic validation rules with example architectures',
        'Include both positive and negative test cases',
      ],
      relatedPrinciples: ['Test-Driven Development', 'Continuous Integration'],
      commonMistakes: [
        'Testing implementation details instead of behavior',
        'Not testing error conditions and edge cases',
        'Creating tests that are too coupled to implementation',
      ],
    },
  ];

  const categories = [
    {
      id: 'hexagonal',
      name: 'Hexagonal Architecture',
      icon: <Layers className="w-4 h-4" />,
      color: 'blue',
    },
    {
      id: 'ddd',
      name: 'Domain-Driven Design',
      icon: <GitBranch className="w-4 h-4" />,
      color: 'green',
    },
    {
      id: 'semantic',
      name: 'Semantic Modeling',
      icon: <Code className="w-4 h-4" />,
      color: 'purple',
    },
    {
      id: 'solid',
      name: 'SOLID Principles',
      icon: <Shield className="w-4 h-4" />,
      color: 'orange',
    },
    {
      id: 'testing',
      name: 'Testing Strategy',
      icon: <Target className="w-4 h-4" />,
      color: 'red',
    },
    {
      id: 'performance',
      name: 'Performance',
      icon: <Zap className="w-4 h-4" />,
      color: 'yellow',
    },
  ];

  const filteredPractices = bestPractices.filter(
    (practice) => practice.category === activeCategory
  );

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'essential':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'recommended':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'advanced':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-2">Best Practices Guide</h1>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          Comprehensive guidelines for building robust semantic architecture
          with hexagonal design principles
        </p>
      </div>

      <Tabs
        value={activeCategory}
        onValueChange={setActiveCategory}
        className="w-full"
      >
        <TabsList className="grid w-full grid-cols-6">
          {categories.map((category) => (
            <TabsTrigger
              key={category.id}
              value={category.id}
              className="flex items-center gap-2 text-xs"
            >
              {category.icon}
              <span className="hidden sm:inline">{category.name}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        {categories.map((category) => (
          <TabsContent key={category.id} value={category.id} className="mt-6">
            <div className="space-y-4">
              {filteredPractices.map((practice) => (
                <Card key={practice.id} className="overflow-hidden">
                  <Collapsible
                    open={expandedPractices.has(practice.id)}
                    onOpenChange={() => togglePractice(practice.id)}
                  >
                    <CollapsibleTrigger asChild>
                      <CardHeader className="cursor-pointer hover:bg-gray-50 transition-colors">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            {expandedPractices.has(practice.id) ? (
                              <ChevronDown className="w-5 h-5" />
                            ) : (
                              <ChevronRight className="w-5 h-5" />
                            )}
                            <div>
                              <CardTitle className="text-lg">
                                {practice.title}
                              </CardTitle>
                              <p className="text-sm text-muted-foreground mt-1">
                                {practice.description}
                              </p>
                            </div>
                          </div>
                          <Badge className={getLevelColor(practice.level)}>
                            {practice.level}
                          </Badge>
                        </div>
                      </CardHeader>
                    </CollapsibleTrigger>

                    <CollapsibleContent>
                      <CardContent className="pt-0">
                        <div className="space-y-6">
                          {/* Examples */}
                          {(practice.examples.good ||
                            practice.examples.bad ||
                            practice.examples.code) && (
                            <div>
                              <h4 className="font-semibold mb-3 flex items-center gap-2">
                                <Code className="w-4 h-4" />
                                Examples
                              </h4>

                              {practice.examples.bad && (
                                <div className="mb-4">
                                  <h5 className="text-sm font-medium text-red-700 mb-2 flex items-center gap-2">
                                    <XCircle className="w-4 h-4" />
                                    What NOT to do:
                                  </h5>
                                  <ul className="text-sm space-y-1 ml-6">
                                    {practice.examples.bad.map(
                                      (example, index) => (
                                        <li
                                          key={index}
                                          className="text-red-600"
                                        >
                                          • {example}
                                        </li>
                                      )
                                    )}
                                  </ul>
                                </div>
                              )}

                              {practice.examples.good && (
                                <div className="mb-4">
                                  <h5 className="text-sm font-medium text-green-700 mb-2 flex items-center gap-2">
                                    <CheckCircle className="w-4 h-4" />
                                    Best practices:
                                  </h5>
                                  <ul className="text-sm space-y-1 ml-6">
                                    {practice.examples.good.map(
                                      (example, index) => (
                                        <li
                                          key={index}
                                          className="text-green-600"
                                        >
                                          • {example}
                                        </li>
                                      )
                                    )}
                                  </ul>
                                </div>
                              )}

                              {practice.examples.code && (
                                <div>
                                  <h5 className="text-sm font-medium mb-2">
                                    Code Example:
                                  </h5>
                                  <pre className="bg-gray-100 p-4 rounded-md text-sm overflow-x-auto">
                                    <code>{practice.examples.code}</code>
                                  </pre>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Tips */}
                          <div>
                            <h4 className="font-semibold mb-3 flex items-center gap-2">
                              <Lightbulb className="w-4 h-4" />
                              Implementation Tips
                            </h4>
                            <ul className="text-sm space-y-2">
                              {practice.tips.map((tip, index) => (
                                <li
                                  key={index}
                                  className="flex items-start gap-2"
                                >
                                  <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                  <span>{tip}</span>
                                </li>
                              ))}
                            </ul>
                          </div>

                          {/* Common Mistakes */}
                          {practice.commonMistakes && (
                            <div>
                              <h4 className="font-semibold mb-3 flex items-center gap-2">
                                <AlertTriangle className="w-4 h-4" />
                                Common Mistakes to Avoid
                              </h4>
                              <ul className="text-sm space-y-2">
                                {practice.commonMistakes.map(
                                  (mistake, index) => (
                                    <li
                                      key={index}
                                      className="flex items-start gap-2"
                                    >
                                      <XCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                                      <span>{mistake}</span>
                                    </li>
                                  )
                                )}
                              </ul>
                            </div>
                          )}

                          {/* Related Principles */}
                          {practice.relatedPrinciples && (
                            <div>
                              <h4 className="font-semibold mb-3 flex items-center gap-2">
                                <BookOpen className="w-4 h-4" />
                                Related Principles
                              </h4>
                              <div className="flex flex-wrap gap-2">
                                {practice.relatedPrinciples.map(
                                  (principle, index) => (
                                    <Badge key={index} variant="outline">
                                      {principle}
                                    </Badge>
                                  )
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </CollapsibleContent>
                  </Collapsible>
                </Card>
              ))}
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
};

export default BestPracticesGuide;
