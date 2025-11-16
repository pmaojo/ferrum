"""
Validation Report Entity

Represents the result of ontology validation operations.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ViolationSeverity(Enum):
    """Severity levels for validation violations"""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class RepairSuggestion:
    """Represents a suggested repair action for a violation"""
    action: str
    description: str
    confidence: float  # 0.0 to 1.0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RuleViolation:
    """Represents a single rule violation"""
    rule_id: str
    violated_constraint: str
    violating_components: List[str]
    severity: str
    description: str
    repair_suggestion: RepairSuggestion
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    # Backward compatibility properties
    @property
    def rule_name(self) -> str:
        return self.rule_id
    
    @property
    def violation_type(self) -> str:
        return self.rule_id
    
    @property
    def component_iri(self) -> str:
        return self.violating_components[0] if self.violating_components else ""
    
    @property
    def suggested_fix(self) -> str:
        return self.repair_suggestion.action


@dataclass
class ValidationReport:
    """Complete validation report for an ontology"""
    tenant_id: str
    is_consistent: bool
    violated_rules: List[RuleViolation]
    unsat_classes: List[str]
    repair_suggestions: List[str]
    explanation: Optional[str]
    timestamp: Optional[datetime] = None
    ontology_version_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def error_count(self) -> int:
        """Count of error-level violations"""
        return len([v for v in self.violated_rules if v.severity == ViolationSeverity.ERROR.value])
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level violations"""
        return len([v for v in self.violated_rules if v.severity == ViolationSeverity.WARNING.value])
    
    @property
    def total_violations(self) -> int:
        """Total number of violations"""
        return len(self.violated_rules)