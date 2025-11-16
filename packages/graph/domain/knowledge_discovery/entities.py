from dataclasses import dataclass
from typing import List

@dataclass
class Pattern:
    """Frequent pattern discovered in triples."""
    predicate: str
    support: int

@dataclass
class Anomaly:
    """Anomaly detected during validation."""
    description: str

@dataclass
class Hypothesis:
    """Proposed explanatory relationship."""
    statement: str

@dataclass
class ValidationResult:
    """Result of validating a hypothesis or discovery."""
    hypothesis: Hypothesis
    confidence: float
