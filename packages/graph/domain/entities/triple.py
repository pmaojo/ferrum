"""
Triple Entity

Represents an RDF triple (subject, predicate, object).
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class Triple:
    """Represents an RDF triple"""
    subject: str
    predicate: str
    object: str
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_turtle(self) -> str:
        """Convert triple to Turtle format"""
        # Simple turtle representation
        if self.object.startswith("http://"):
            # Object is a URI
            return f"<{self.subject}> <{self.predicate}> <{self.object}> ."
        else:
            # Object is a literal
            return f"<{self.subject}> <{self.predicate}> \"{self.object}\" ."
    
    def to_dict(self) -> Dict[str, str]:
        """Convert triple to dictionary"""
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object
        }