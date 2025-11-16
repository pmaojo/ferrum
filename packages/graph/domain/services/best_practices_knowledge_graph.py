"""
Best Practices Knowledge Graph Service

Manages a semantic knowledge graph of software architecture best practices,
anti-patterns, and their relationships. Provides reasoning capabilities
for practice recommendations and violation detection.
"""

from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime

from ..entities.architectural_component import ArchitecturalComponent
from ..entities.validation_report import ValidationReport


class PracticeType(Enum):
    BEST_PRACTICE = "best_practice"
    ANTI_PATTERN = "anti_pattern"
    CODE_SMELL = "code_smell"
    DESIGN_PRINCIPLE = "design_principle"
    REFACTORING_TECHNIQUE = "refactoring_technique"


class PracticeContext(Enum):
    HEXAGONAL_ARCHITECTURE = "hexagonal_architecture"
    DOMAIN_DRIVEN_DESIGN = "domain_driven_design"
    MICROSERVICES = "microservices"
    TESTING = "testing"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"


class EvidenceLevel(Enum):
    EMPIRICAL = "empirical"  # Research-backed
    INDUSTRY = "industry"    # Industry consensus
    EXPERT = "expert"        # Expert opinion
    COMMUNITY = "community"  # Community practice


@dataclass
class PracticeEvidence:
    """Evidence supporting a practice"""
    source: str
    evidence_type: EvidenceLevel
    description: str
    url: Optional[str] = None
    study_details: Optional[Dict[str, Any]] = None
    confidence_score: float = 0.0


@dataclass
class PracticeRelationship:
    """Relationship between practices"""
    source_practice_id: str
    target_practice_id: str
    relationship_type: str  # "conflicts_with", "supports", "requires", "alternative_to"
    strength: float  # 0.0 to 1.0
    context: Optional[PracticeContext] = None
    description: str = ""


@dataclass
class BestPractice:
    """Represents a software development best practice"""
    id: str
    name: str
    practice_type: PracticeType
    context: Set[PracticeContext]
    description: str
    rationale: str
    when_to_apply: str
    when_not_to_apply: str
    implementation_steps: List[str]
    code_examples: Dict[str, str]  # language -> code
    detection_rules: List[str]  # OWL/SPARQL rules for detection
    metrics: Dict[str, Any]  # Measurable indicators
    evidence: List[PracticeEvidence]
    related_patterns: List[str]
    tags: Set[str] = field(default_factory=set)
    severity: str = "medium"  # For anti-patterns and code smells
    effort_to_fix: str = "medium"  # "low", "medium", "high"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    author: str = ""
    community_rating: float = 0.0
    usage_frequency: int = 0


class BestPracticesKnowledgeGraph:
    """Service for managing best practices knowledge graph"""
    
    def __init__(self):
        self.practices: Dict[str, BestPractice] = {}
        self.relationships: List[PracticeRelationship] = []
        self.context_index: Dict[PracticeContext, Set[str]] = {}
        self.type_index: Dict[PracticeType, Set[str]] = {}
        self.tag_index: Dict[str, Set[str]] = {}
        self._load_default_practices()
    
    def _load_default_practices(self):
        """Load default best practices and anti-patterns"""
        self._add_hexagonal_practices()
        self._add_ddd_practices()
        self._add_solid_practices()
        self._add_testing_practices()
        self._add_relationships()
        self._rebuild_indices()
    
    def _add_hexagonal_practices(self):
        """Add hexagonal architecture best practices"""
        
        # Best Practice: Dependency Inversion
        dependency_inversion = BestPractice(
            id="hexagonal_dependency_inversion",
            name="Dependency Inversion in Hexagonal Architecture",
            practice_type=PracticeType.BEST_PRACTICE,
            context={PracticeContext.HEXAGONAL_ARCHITECTURE},
            description="Domain layer should depend only on abstractions, not concrete implementations",
            rationale="Ensures business logic remains independent of infrastructure concerns",
            when_to_apply="Always in hexagonal architecture implementations",
            when_not_to_apply="Simple scripts or prototypes where flexibility is not needed",
            implementation_steps=[
                "Define ports (interfaces) in domain layer",
                "Implement adapters in infrastructure layer",
                "Use dependency injection to wire adapters to ports",
                "Ensure domain never imports infrastructure packages"
            ],
            code_examples={
                "go": """
// Domain layer - Port definition
type UserRepository interface {
    Save(user *User) error
    FindByID(id string) (*User, error)
}

// Domain service using port
type UserService struct {
    repo UserRepository // Depends on abstraction
}

// Infrastructure layer - Adapter implementation
type PostgresUserRepository struct {
    db *sql.DB
}

func (r *PostgresUserRepository) Save(user *User) error {
    // Implementation details
}
                """
            },
            detection_rules=[
                "DomainComponent ⊑ ¬(imports some InfrastructurePackage)",
                "SELECT ?violation WHERE { ?domain rdf:type kth:DomainComponent . ?domain kth:imports ?infra . ?infra rdf:type kth:InfrastructureComponent }"
            ],
            metrics={
                "coupling_ratio": "Number of domain->infrastructure dependencies / Total dependencies",
                "abstraction_ratio": "Number of interfaces / Total types in domain"
            },
            evidence=[
                PracticeEvidence(
                    source="Clean Architecture by Robert Martin",
                    evidence_type=EvidenceLevel.EXPERT,
                    description="Fundamental principle of clean architecture",
                    confidence_score=0.95
                ),
                PracticeEvidence(
                    source="Hexagonal Architecture by Alistair Cockburn",
                    evidence_type=EvidenceLevel.EXPERT,
                    description="Core concept of ports and adapters pattern",
                    url="https://alistair.cockburn.us/hexagonal-architecture/",
                    confidence_score=0.98
                )
            ],
            related_patterns=["port_adapter_pattern", "dependency_injection"],
            tags={"dependency_inversion", "ports", "adapters", "decoupling"},
            severity="high"
        )
        
        # Anti-Pattern: Domain Depending on Infrastructure
        domain_infra_coupling = BestPractice(
            id="hexagonal_domain_infra_coupling",
            name="Domain-Infrastructure Coupling",
            practice_type=PracticeType.ANTI_PATTERN,
            context={PracticeContext.HEXAGONAL_ARCHITECTURE},
            description="Domain layer directly depending on infrastructure components",
            rationale="Violates dependency inversion principle and makes testing difficult",
            when_to_apply="Never - this is an anti-pattern",
            when_not_to_apply="Always avoid this pattern",
            implementation_steps=[
                "Identify direct infrastructure dependencies in domain",
                "Extract interfaces for external dependencies",
                "Move concrete implementations to infrastructure layer",
                "Use dependency injection to provide implementations"
            ],
            code_examples={
                "go": """
// BAD: Domain depending on infrastructure
package domain

import "database/sql" // Direct infrastructure dependency

type UserService struct {
    db *sql.DB // Concrete dependency
}

// GOOD: Domain depending on abstraction
package domain

type UserRepository interface { // Abstract dependency
    Save(user *User) error
}

type UserService struct {
    repo UserRepository
}
                """
            },
            detection_rules=[
                "DomainComponent ⊓ (imports some InfrastructurePackage) ⊑ Violation",
                "SELECT ?violation WHERE { ?domain rdf:type kth:DomainComponent . ?domain kth:imports ?pkg . ?pkg rdf:type kth:InfrastructurePackage }"
            ],
            metrics={
                "violation_count": "Number of domain components importing infrastructure",
                "coupling_depth": "Maximum depth of infrastructure dependencies"
            },
            evidence=[
                PracticeEvidence(
                    source="Empirical study on architectural violations",
                    evidence_type=EvidenceLevel.EMPIRICAL,
                    description="Strong correlation between domain-infrastructure coupling and defect density",
                    confidence_score=0.87
                )
            ],
            related_patterns=["god_class", "spaghetti_code"],
            tags={"coupling", "dependency", "violation", "testing"},
            severity="high",
            effort_to_fix="medium"
        )
        
        self.practices[dependency_inversion.id] = dependency_inversion
        self.practices[domain_infra_coupling.id] = domain_infra_coupling
    
    def _add_ddd_practices(self):
        """Add Domain-Driven Design best practices"""
        
        # Best Practice: Aggregate Consistency
        aggregate_consistency = BestPractice(
            id="ddd_aggregate_consistency",
            name="Maintain Aggregate Consistency Boundaries",
            practice_type=PracticeType.BEST_PRACTICE,
            context={PracticeContext.DOMAIN_DRIVEN_DESIGN},
            description="Ensure all changes within an aggregate maintain business invariants",
            rationale="Prevents data corruption and maintains business rule integrity",
            when_to_apply="When modeling complex business domains with invariants",
            when_not_to_apply="Simple CRUD applications without complex business rules",
            implementation_steps=[
                "Identify business invariants that must be maintained",
                "Group related entities under single aggregate root",
                "Ensure all modifications go through aggregate root",
                "Use domain events for cross-aggregate communication"
            ],
            code_examples={
                "go": """
type Order struct {
    id       OrderID
    items    []OrderItem
    status   OrderStatus
    total    Money
}

func (o *Order) AddItem(productID ProductID, quantity int, price Money) error {
    if o.status != OrderStatusDraft {
        return errors.New("cannot modify confirmed order")
    }
    
    item := OrderItem{
        ProductID: productID,
        Quantity:  quantity,
        Price:     price,
    }
    
    o.items = append(o.items, item)
    o.recalculateTotal() // Maintain invariant
    return nil
}
                """
            },
            detection_rules=[
                "AggregateRoot ⊑ ∀modifies.OnlyThroughRoot",
                "SELECT ?violation WHERE { ?entity rdf:type kth:Entity . ?external kth:modifies ?entity . NOT EXISTS { ?external kth:goesThrough ?root . ?root rdf:type kth:AggregateRoot } }"
            ],
            metrics={
                "invariant_violations": "Number of business rule violations detected",
                "aggregate_size": "Number of entities per aggregate"
            },
            evidence=[
                PracticeEvidence(
                    source="Domain-Driven Design by Eric Evans",
                    evidence_type=EvidenceLevel.EXPERT,
                    description="Fundamental DDD concept for maintaining consistency",
                    confidence_score=0.96
                )
            ],
            related_patterns=["aggregate_pattern", "domain_events"],
            tags={"aggregate", "consistency", "invariants", "business_rules"}
        )
        
        self.practices[aggregate_consistency.id] = aggregate_consistency
    
    def _add_solid_practices(self):
        """Add SOLID principle best practices"""
        
        # Best Practice: Single Responsibility Principle
        srp_practice = BestPractice(
            id="solid_single_responsibility",
            name="Single Responsibility Principle",
            practice_type=PracticeType.DESIGN_PRINCIPLE,
            context={PracticeContext.HEXAGONAL_ARCHITECTURE, PracticeContext.MAINTAINABILITY},
            description="A class should have only one reason to change",
            rationale="Reduces coupling and increases cohesion, making code easier to maintain",
            when_to_apply="When designing classes and modules",
            when_not_to_apply="Very simple utility classes with minimal functionality",
            implementation_steps=[
                "Identify all responsibilities of a class",
                "Group related responsibilities together",
                "Extract unrelated responsibilities into separate classes",
                "Define clear interfaces between classes"
            ],
            code_examples={
                "go": """
// BAD: Multiple responsibilities
type UserManager struct{}
func (um *UserManager) CreateUser(user User) error { /* ... */ }
func (um *UserManager) SendWelcomeEmail(email string) error { /* ... */ }
func (um *UserManager) LogUserActivity(activity string) error { /* ... */ }

// GOOD: Single responsibilities
type UserService struct{}
func (us *UserService) CreateUser(user User) error { /* ... */ }

type EmailService struct{}
func (es *EmailService) SendWelcomeEmail(email string) error { /* ... */ }

type ActivityLogger struct{}
func (al *ActivityLogger) LogActivity(activity string) error { /* ... */ }
                """
            },
            detection_rules=[
                "GodClass ⊑ Class ⊓ (≥3 hasResponsibility.Responsibility)",
                "SELECT ?class WHERE { ?class rdf:type kth:Class . ?class kth:hasMethod ?m1, ?m2, ?m3 . ?m1 kth:belongsToDomain ?d1 . ?m2 kth:belongsToDomain ?d2 . ?m3 kth:belongsToDomain ?d3 . FILTER(?d1 != ?d2 && ?d2 != ?d3 && ?d1 != ?d3) }"
            ],
            metrics={
                "methods_per_class": "Average number of methods per class",
                "responsibility_count": "Number of distinct responsibilities per class"
            },
            evidence=[
                PracticeEvidence(
                    source="SOLID Principles research studies",
                    evidence_type=EvidenceLevel.EMPIRICAL,
                    description="Classes following SRP have lower defect rates",
                    confidence_score=0.82
                )
            ],
            related_patterns=["interface_segregation", "dependency_inversion"],
            tags={"solid", "srp", "responsibility", "cohesion"}
        )
        
        self.practices[srp_practice.id] = srp_practice
    
    def _add_testing_practices(self):
        """Add testing best practices"""
        
        # Best Practice: Test Pyramid
        test_pyramid = BestPractice(
            id="testing_test_pyramid",
            name="Test Pyramid Strategy",
            practice_type=PracticeType.BEST_PRACTICE,
            context={PracticeContext.TESTING},
            description="Maintain proper ratio of unit, integration, and end-to-end tests",
            rationale="Balances test coverage with execution speed and maintenance cost",
            when_to_apply="All software projects with automated testing",
            when_not_to_apply="Proof-of-concept or throwaway code",
            implementation_steps=[
                "Write many fast unit tests (70-80%)",
                "Add integration tests for component interactions (15-25%)",
                "Include few end-to-end tests for critical paths (5-10%)",
                "Monitor test execution time and flakiness"
            ],
            code_examples={
                "go": """
// Unit test - fast, isolated
func TestUserService_CreateUser(t *testing.T) {
    mockRepo := &MockUserRepository{}
    service := NewUserService(mockRepo)
    
    user := &User{Name: "John"}
    err := service.CreateUser(user)
    
    assert.NoError(t, err)
    assert.True(t, mockRepo.SaveCalled)
}

// Integration test - tests component interaction
func TestUserRepository_Integration(t *testing.T) {
    db := setupTestDB()
    repo := NewPostgresUserRepository(db)
    
    user := &User{Name: "John"}
    err := repo.Save(user)
    
    assert.NoError(t, err)
    // Verify in database
}
                """
            },
            detection_rules=[
                "TestSuite ⊑ (≥0.7 hasUnitTest.UnitTest) ⊓ (≤0.3 hasIntegrationTest.IntegrationTest)",
                "SELECT ?suite WHERE { ?suite rdf:type kth:TestSuite . ?suite kth:hasTestCount ?total . ?suite kth:hasUnitTestCount ?unit . FILTER(?unit / ?total < 0.5) }"
            ],
            metrics={
                "unit_test_ratio": "Unit tests / Total tests",
                "test_execution_time": "Average test suite execution time",
                "test_flakiness": "Percentage of flaky tests"
            },
            evidence=[
                PracticeEvidence(
                    source="Google Testing Blog",
                    evidence_type=EvidenceLevel.INDUSTRY,
                    description="Test pyramid provides optimal balance of speed and coverage",
                    url="https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html",
                    confidence_score=0.91
                )
            ],
            related_patterns=["mock_objects", "test_doubles"],
            tags={"testing", "pyramid", "unit_tests", "integration_tests"}
        )
        
        self.practices[test_pyramid.id] = test_pyramid
    
    def _add_relationships(self):
        """Add relationships between practices"""
        
        # Dependency inversion supports aggregate consistency
        self.relationships.append(PracticeRelationship(
            source_practice_id="hexagonal_dependency_inversion",
            target_practice_id="ddd_aggregate_consistency",
            relationship_type="supports",
            strength=0.8,
            context=PracticeContext.HEXAGONAL_ARCHITECTURE,
            description="Dependency inversion enables clean aggregate boundaries"
        ))
        
        # Domain-infrastructure coupling conflicts with dependency inversion
        self.relationships.append(PracticeRelationship(
            source_practice_id="hexagonal_domain_infra_coupling",
            target_practice_id="hexagonal_dependency_inversion",
            relationship_type="conflicts_with",
            strength=1.0,
            description="Direct coupling violates dependency inversion principle"
        ))
        
        # SRP supports dependency inversion
        self.relationships.append(PracticeRelationship(
            source_practice_id="solid_single_responsibility",
            target_practice_id="hexagonal_dependency_inversion",
            relationship_type="supports",
            strength=0.7,
            description="Single responsibility makes dependency inversion easier to implement"
        ))
    
    def _rebuild_indices(self):
        """Rebuild search indices"""
        self.context_index.clear()
        self.type_index.clear()
        self.tag_index.clear()
        
        for practice in self.practices.values():
            # Context index
            for context in practice.context:
                if context not in self.context_index:
                    self.context_index[context] = set()
                self.context_index[context].add(practice.id)
            
            # Type index
            if practice.practice_type not in self.type_index:
                self.type_index[practice.practice_type] = set()
            self.type_index[practice.practice_type].add(practice.id)
            
            # Tag index
            for tag in practice.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = set()
                self.tag_index[tag].add(practice.id)
    
    def get_practice(self, practice_id: str) -> Optional[BestPractice]:
        """Get practice by ID"""
        return self.practices.get(practice_id)
    
    def search_practices(
        self,
        query: str = "",
        practice_type: Optional[PracticeType] = None,
        context: Optional[PracticeContext] = None,
        tags: Optional[Set[str]] = None,
        severity: Optional[str] = None
    ) -> List[BestPractice]:
        """Search practices by various criteria"""
        results = set(self.practices.keys())
        
        # Filter by type
        if practice_type:
            results &= self.type_index.get(practice_type, set())
        
        # Filter by context
        if context:
            results &= self.context_index.get(context, set())
        
        # Filter by tags
        if tags:
            tag_results = set()
            for tag in tags:
                tag_results |= self.tag_index.get(tag, set())
            results &= tag_results
        
        # Filter by severity
        if severity:
            severity_results = {
                pid for pid, practice in self.practices.items()
                if practice.severity == severity
            }
            results &= severity_results
        
        # Text search
        if query:
            query_lower = query.lower()
            text_results = {
                pid for pid, practice in self.practices.items()
                if query_lower in practice.name.lower() or
                   query_lower in practice.description.lower()
            }
            results &= text_results
        
        return [self.practices[pid] for pid in results]
    
    def get_related_practices(
        self,
        practice_id: str,
        relationship_types: Optional[List[str]] = None
    ) -> List[Tuple[BestPractice, PracticeRelationship]]:
        """Get practices related to the given practice"""
        related = []
        
        for rel in self.relationships:
            if rel.source_practice_id == practice_id:
                if not relationship_types or rel.relationship_type in relationship_types:
                    target_practice = self.get_practice(rel.target_practice_id)
                    if target_practice:
                        related.append((target_practice, rel))
            elif rel.target_practice_id == practice_id:
                if not relationship_types or rel.relationship_type in relationship_types:
                    source_practice = self.get_practice(rel.source_practice_id)
                    if source_practice:
                        related.append((source_practice, rel))
        
        return related
    
    def get_conflicting_practices(self, practice_id: str) -> List[BestPractice]:
        """Get practices that conflict with the given practice"""
        related = self.get_related_practices(practice_id, ["conflicts_with"])
        return [practice for practice, _ in related]
    
    def get_supporting_practices(self, practice_id: str) -> List[BestPractice]:
        """Get practices that support the given practice"""
        related = self.get_related_practices(practice_id, ["supports", "requires"])
        return [practice for practice, _ in related]

    def _execute_detection_rule(self, rule: str) -> bool:
        """Execute a detection rule against the knowledge graph.

        The rule can be either a SPARQL query or an OWL axiom. In a full
        implementation this method would dispatch the rule to a SPARQL engine or
        reasoning service and return ``True`` when the rule produces any
        matches. This placeholder implementation always returns ``False`` and is
        intended to be overridden or mocked in tests.
        """
        # TODO: Integrate with actual SPARQL/OWL reasoning engine
        return False
    
    def recommend_practices(
        self,
        current_violations: List[str],
        project_context: Set[PracticeContext],
        max_recommendations: int = 5
    ) -> List[Tuple[BestPractice, float]]:
        """Recommend practices based on current violations and context"""
        recommendations = []

        for practice in self.practices.values():
            # Execute detection rules; skip practice if none fire
            if not any(self._execute_detection_rule(rule) for rule in practice.detection_rules):
                continue

            score = 0.0

            # Context match
            context_overlap = len(practice.context & project_context)
            if context_overlap > 0:
                score += context_overlap * 0.3

            # Community rating
            score += practice.community_rating * 0.2

            # Evidence quality
            evidence_score = sum(
                0.1 * (1.0 if ev.evidence_type == EvidenceLevel.EMPIRICAL else
                       0.8 if ev.evidence_type == EvidenceLevel.INDUSTRY else
                       0.6 if ev.evidence_type == EvidenceLevel.EXPERT else 0.4)
                for ev in practice.evidence
            )
            score += evidence_score

            if score > 0:
                recommendations.append((practice, score))

        # Sort by score and return top recommendations
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:max_recommendations]
    
    def add_practice(self, practice: BestPractice) -> bool:
        """Add a new practice to the knowledge graph"""
        if practice.id in self.practices:
            return False
        
        self.practices[practice.id] = practice
        self._rebuild_indices()
        return True
    
    def add_relationship(self, relationship: PracticeRelationship) -> bool:
        """Add a relationship between practices"""
        # Validate that both practices exist
        if (relationship.source_practice_id not in self.practices or
            relationship.target_practice_id not in self.practices):
            return False
        
        self.relationships.append(relationship)
        return True
    
    def get_knowledge_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph"""
        return {
            "total_practices": len(self.practices),
            "total_relationships": len(self.relationships),
            "by_type": {
                ptype.value: len(self.type_index.get(ptype, set()))
                for ptype in PracticeType
            },
            "by_context": {
                context.value: len(self.context_index.get(context, set()))
                for context in PracticeContext
            },
            "relationship_types": {
                rel_type: len([r for r in self.relationships if r.relationship_type == rel_type])
                for rel_type in set(r.relationship_type for r in self.relationships)
            }
        }