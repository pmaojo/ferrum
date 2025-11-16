"""
Architectural Pattern Library Service

Manages a comprehensive library of architectural patterns for hexagonal architecture,
DDD, and SOLID principles. Provides pattern definitions, validation rules, and
matching capabilities for code analysis.
"""

from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from ..entities.validation_report import ValidationReport
from ..entities.architectural_component import ArchitecturalComponent


class PatternCategory(Enum):
    HEXAGONAL = "hexagonal"
    DDD = "domain_driven_design"
    SOLID = "solid_principles"
    MICROSERVICES = "microservices"
    EVENT_SOURCING = "event_sourcing"
    CQRS = "command_query_responsibility_segregation"


class PatternComplexity(Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class PatternExample:
    """Example implementation of a pattern"""
    language: str
    code_snippet: str
    description: str
    file_structure: Dict[str, str]
    dependencies: List[str] = field(default_factory=list)


@dataclass
class PatternViolation:
    """Common violation of a pattern"""
    violation_type: str
    description: str
    example: str
    fix_suggestion: str
    severity: str  # "error", "warning", "info"


@dataclass
class ArchitecturalPattern:
    """Represents an architectural pattern with all its metadata"""
    id: str
    name: str
    category: PatternCategory
    complexity: PatternComplexity
    description: str
    intent: str
    structure: Dict[str, Any]
    participants: List[str]
    collaborations: List[str]
    consequences: Dict[str, List[str]]  # benefits and liabilities
    implementation_notes: str
    examples: List[PatternExample]
    common_violations: List[PatternViolation]
    related_patterns: List[str]
    owl_axioms: List[str]  # OWL axioms for formal validation
    tags: Set[str] = field(default_factory=set)
    created_at: str = ""
    updated_at: str = ""
    author: str = ""
    community_rating: float = 0.0
    usage_count: int = 0


class ArchitecturalPatternLibrary:
    """Service for managing architectural patterns"""
    
    def __init__(self):
        self.patterns: Dict[str, ArchitecturalPattern] = {}
        self.pattern_index: Dict[str, Set[str]] = {}  # tag -> pattern_ids
        self.category_index: Dict[PatternCategory, Set[str]] = {}
        self._load_default_patterns()
    
    def _load_default_patterns(self):
        """Load default architectural patterns"""
        # Hexagonal Architecture Patterns
        self._add_hexagonal_patterns()
        # DDD Patterns
        self._add_ddd_patterns()
        # SOLID Patterns
        self._add_solid_patterns()
        # Build indices
        self._rebuild_indices()
    
    def _add_hexagonal_patterns(self):
        """Add hexagonal architecture patterns"""
        
        # Port-Adapter Pattern
        port_adapter = ArchitecturalPattern(
            id="hexagonal_port_adapter",
            name="Hexagonal Port-Adapter Pattern",
            category=PatternCategory.HEXAGONAL,
            complexity=PatternComplexity.BASIC,
            description="Hexagonal architecture pattern: defines interfaces (ports) and their implementations (adapters) to isolate business logic",
            intent="Isolate the application core from external concerns through well-defined interfaces",
            structure={
                "port": "Interface defining contract",
                "adapter": "Implementation of the port interface",
                "domain": "Business logic using the port"
            },
            participants=["Port", "Adapter", "DomainService"],
            collaborations=["Domain uses Port", "Adapter implements Port"],
            consequences={
                "benefits": [
                    "Testability through mocking",
                    "Flexibility in implementation choice",
                    "Clear separation of concerns"
                ],
                "liabilities": [
                    "Additional abstraction layer",
                    "More interfaces to maintain"
                ]
            },
            implementation_notes="Always define ports in domain layer, adapters in infrastructure",
            examples=[
                PatternExample(
                    language="go",
                    code_snippet="""
// Port (in domain)
type UserRepository interface {
    Save(user *User) error
    FindByID(id string) (*User, error)
}

// Adapter (in infrastructure)
type PostgresUserRepository struct {
    db *sql.DB
}

func (r *PostgresUserRepository) Save(user *User) error {
    // Implementation
}
                    """,
                    description="Basic port-adapter implementation in Go",
                    file_structure={
                        "domain/ports/user_repository.go": "Port definition",
                        "infrastructure/adapters/postgres_user_repository.go": "Adapter implementation"
                    }
                )
            ],
            common_violations=[
                PatternViolation(
                    violation_type="domain_depends_on_adapter",
                    description="Domain layer directly depends on adapter implementation",
                    example="import \"infrastructure/postgres\"",
                    fix_suggestion="Use dependency injection with port interface",
                    severity="error"
                )
            ],
            related_patterns=["dependency_injection", "repository_pattern"],
            owl_axioms=[
                "Port ⊑ Interface",
                "Adapter ⊑ Implementation",
                "DomainService ⊑ ∀uses.Port",
                "Adapter ⊑ ∀implements.Port"
            ],
            tags={"hexagonal", "ports", "adapters", "isolation"}
        )
        
        self.patterns[port_adapter.id] = port_adapter
    
    def _add_ddd_patterns(self):
        """Add Domain-Driven Design patterns"""
        
        # Aggregate Pattern
        aggregate = ArchitecturalPattern(
            id="ddd_aggregate",
            name="Aggregate Pattern",
            category=PatternCategory.DDD,
            complexity=PatternComplexity.INTERMEDIATE,
            description="Groups related entities and value objects with consistency boundaries",
            intent="Maintain consistency and encapsulation within domain boundaries",
            structure={
                "aggregate_root": "Entry point for aggregate access",
                "entities": "Objects with identity within aggregate",
                "value_objects": "Immutable objects without identity"
            },
            participants=["AggregateRoot", "Entity", "ValueObject"],
            collaborations=[
                "External access only through AggregateRoot",
                "AggregateRoot manages internal consistency"
            ],
            consequences={
                "benefits": [
                    "Strong consistency boundaries",
                    "Encapsulation of business rules",
                    "Clear transaction boundaries"
                ],
                "liabilities": [
                    "Potential performance overhead",
                    "Complex aggregate design decisions"
                ]
            },
            implementation_notes="Keep aggregates small and focused on single business concept",
            examples=[
                PatternExample(
                    language="go",
                    code_snippet="""
// Aggregate Root
type Order struct {
    id       OrderID
    items    []OrderItem
    status   OrderStatus
    customer CustomerID
}

func (o *Order) AddItem(product ProductID, quantity int) error {
    // Business rules validation
    if o.status != OrderStatusDraft {
        return errors.New("cannot modify confirmed order")
    }
    // Add item logic
}
                    """,
                    description="Order aggregate with business rules",
                    file_structure={
                        "domain/aggregates/order.go": "Order aggregate root",
                        "domain/entities/order_item.go": "Order item entity"
                    }
                )
            ],
            common_violations=[
                PatternViolation(
                    violation_type="direct_entity_access",
                    description="External code directly accessing entities within aggregate",
                    example="order.Items[0].SetQuantity(5)",
                    fix_suggestion="Provide methods on aggregate root",
                    severity="error"
                )
            ],
            related_patterns=["repository_pattern", "domain_events"],
            owl_axioms=[
                "AggregateRoot ⊑ Entity",
                "Entity ⊑ ∀belongsTo.≤1.Aggregate",
                "ExternalAccess ⊑ ∀accesses.AggregateRoot"
            ],
            tags={"ddd", "aggregate", "consistency", "boundaries"}
        )
        
        self.patterns[aggregate.id] = aggregate
    
    def _add_solid_patterns(self):
        """Add SOLID principle patterns"""
        
        # Single Responsibility Principle
        srp = ArchitecturalPattern(
            id="solid_srp",
            name="Single Responsibility Principle",
            category=PatternCategory.SOLID,
            complexity=PatternComplexity.BASIC,
            description="A class should have only one reason to change",
            intent="Reduce coupling and increase cohesion by limiting class responsibilities",
            structure={
                "focused_class": "Class with single, well-defined responsibility",
                "separated_concerns": "Different aspects handled by different classes"
            },
            participants=["ResponsibleClass"],
            collaborations=["Classes collaborate through well-defined interfaces"],
            consequences={
                "benefits": [
                    "Easier to understand and maintain",
                    "Reduced coupling between components",
                    "Better testability"
                ],
                "liabilities": [
                    "More classes to manage",
                    "Potential over-engineering"
                ]
            },
            implementation_notes="Identify reasons for change and separate them into different classes",
            examples=[
                PatternExample(
                    language="go",
                    code_snippet="""
// Violation: Multiple responsibilities
type UserManager struct{}
func (um *UserManager) CreateUser(user User) error { /* ... */ }
func (um *UserManager) SendEmail(email string) error { /* ... */ }
func (um *UserManager) LogActivity(activity string) error { /* ... */ }

// Better: Separated responsibilities
type UserService struct{}
func (us *UserService) CreateUser(user User) error { /* ... */ }

type EmailService struct{}
func (es *EmailService) SendEmail(email string) error { /* ... */ }

type ActivityLogger struct{}
func (al *ActivityLogger) LogActivity(activity string) error { /* ... */ }
                    """,
                    description="Separating user management, email, and logging concerns",
                    file_structure={
                        "domain/services/user_service.go": "User business logic",
                        "infrastructure/email_service.go": "Email functionality",
                        "infrastructure/activity_logger.go": "Logging functionality"
                    }
                )
            ],
            common_violations=[
                PatternViolation(
                    violation_type="god_class",
                    description="Class handling multiple unrelated responsibilities",
                    example="UserManager handling users, emails, and logging",
                    fix_suggestion="Split into focused classes with single responsibilities",
                    severity="warning"
                )
            ],
            related_patterns=["dependency_injection", "interface_segregation"],
            owl_axioms=[
                "Class ⊑ ∀hasResponsibility.≤1.Responsibility",
                "GodClass ⊑ Class ⊓ ∀hasResponsibility.≥2.Responsibility"
            ],
            tags={"solid", "srp", "responsibility", "cohesion"}
        )
        
        self.patterns[srp.id] = srp
    
    def _rebuild_indices(self):
        """Rebuild search indices"""
        self.pattern_index.clear()
        self.category_index.clear()
        
        for pattern in self.patterns.values():
            # Tag index
            for tag in pattern.tags:
                if tag not in self.pattern_index:
                    self.pattern_index[tag] = set()
                self.pattern_index[tag].add(pattern.id)
            
            # Category index
            if pattern.category not in self.category_index:
                self.category_index[pattern.category] = set()
            self.category_index[pattern.category].add(pattern.id)
    
    def get_pattern(self, pattern_id: str) -> Optional[ArchitecturalPattern]:
        """Get pattern by ID"""
        return self.patterns.get(pattern_id)
    
    def search_patterns(
        self,
        query: str = "",
        category: Optional[PatternCategory] = None,
        complexity: Optional[PatternComplexity] = None,
        tags: Optional[Set[str]] = None
    ) -> List[ArchitecturalPattern]:
        """Search patterns by various criteria"""
        results = set(self.patterns.keys())
        
        # Filter by category
        if category:
            results &= self.category_index.get(category, set())
        
        # Filter by tags
        if tags:
            tag_results = set()
            for tag in tags:
                tag_results |= self.pattern_index.get(tag, set())
            results &= tag_results
        
        # Filter by complexity
        if complexity:
            complexity_results = {
                pid for pid, pattern in self.patterns.items()
                if pattern.complexity == complexity
            }
            results &= complexity_results
        
        # Text search in name, description, and tags
        if query:
            query_lower = query.lower()
            text_results = {
                pid for pid, pattern in self.patterns.items()
                if query_lower in pattern.name.lower() or
                   query_lower in pattern.description.lower() or
                   any(query_lower in t.lower() for t in pattern.tags)
            }
            results &= text_results
        
        return [self.patterns[pid] for pid in results]
    
    def get_related_patterns(self, pattern_id: str) -> List[ArchitecturalPattern]:
        """Get patterns related to the given pattern"""
        pattern = self.get_pattern(pattern_id)
        if not pattern:
            return []
        
        related = []
        for related_id in pattern.related_patterns:
            related_pattern = self.get_pattern(related_id)
            if related_pattern:
                related.append(related_pattern)
        
        return related
    
    def add_pattern(self, pattern: ArchitecturalPattern) -> bool:
        """Add a new pattern to the library"""
        if pattern.id in self.patterns:
            return False
        
        self.patterns[pattern.id] = pattern
        self._rebuild_indices()
        return True
    
    def update_pattern(self, pattern: ArchitecturalPattern) -> bool:
        """Update an existing pattern"""
        if pattern.id not in self.patterns:
            return False
        
        self.patterns[pattern.id] = pattern
        self._rebuild_indices()
        return True
    
    def get_patterns_by_category(self, category: PatternCategory) -> List[ArchitecturalPattern]:
        """Get all patterns in a category"""
        pattern_ids = self.category_index.get(category, set())
        return [self.patterns[pid] for pid in pattern_ids]
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about the pattern library"""
        stats = {
            "total_patterns": len(self.patterns),
            "by_category": {},
            "by_complexity": {},
            "most_used": [],
            "highest_rated": []
        }
        
        # Category stats
        for category in PatternCategory:
            count = len(self.category_index.get(category, set()))
            stats["by_category"][category.value] = count
        
        # Complexity stats
        for complexity in PatternComplexity:
            count = len([p for p in self.patterns.values() if p.complexity == complexity])
            stats["by_complexity"][complexity.value] = count
        
        # Most used patterns
        most_used = sorted(
            self.patterns.values(),
            key=lambda p: p.usage_count,
            reverse=True
        )[:5]
        stats["most_used"] = [{"id": p.id, "name": p.name, "usage_count": p.usage_count} for p in most_used]
        
        # Highest rated patterns
        highest_rated = sorted(
            self.patterns.values(),
            key=lambda p: p.community_rating,
            reverse=True
        )[:5]
        stats["highest_rated"] = [{"id": p.id, "name": p.name, "rating": p.community_rating} for p in highest_rated]
        
        return stats
    
    def export_patterns(self, format: str = "json") -> str:
        """Export patterns in specified format"""
        if format == "json":
            return json.dumps(
                {pid: self._pattern_to_dict(pattern) for pid, pattern in self.patterns.items()},
                indent=2
            )
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _pattern_to_dict(self, pattern: ArchitecturalPattern) -> Dict[str, Any]:
        """Convert pattern to dictionary for serialization"""
        return {
            "id": pattern.id,
            "name": pattern.name,
            "category": pattern.category.value,
            "complexity": pattern.complexity.value,
            "description": pattern.description,
            "intent": pattern.intent,
            "structure": pattern.structure,
            "participants": pattern.participants,
            "collaborations": pattern.collaborations,
            "consequences": pattern.consequences,
            "implementation_notes": pattern.implementation_notes,
            "examples": [
                {
                    "language": ex.language,
                    "code_snippet": ex.code_snippet,
                    "description": ex.description,
                    "file_structure": ex.file_structure,
                    "dependencies": ex.dependencies
                }
                for ex in pattern.examples
            ],
            "common_violations": [
                {
                    "violation_type": v.violation_type,
                    "description": v.description,
                    "example": v.example,
                    "fix_suggestion": v.fix_suggestion,
                    "severity": v.severity
                }
                for v in pattern.common_violations
            ],
            "related_patterns": pattern.related_patterns,
            "owl_axioms": pattern.owl_axioms,
            "tags": list(pattern.tags),
            "created_at": pattern.created_at,
            "updated_at": pattern.updated_at,
            "author": pattern.author,
            "community_rating": pattern.community_rating,
            "usage_count": pattern.usage_count
        }