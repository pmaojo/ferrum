"""
Semantic Code Completion Service

Provides intelligent code completion suggestions based on:
- Architectural context and patterns
- Domain knowledge from the knowledge graph
- LLM-powered semantic understanding
- Project-specific conventions
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from application.ports.base import LLMPort
from application.ports.knowledge_graph_port import KnowledgeGraphPort
try:
    from domain.agents.advanced_ai_agent import SemanticCompletion
except Exception:  # pragma: no cover - fallback if dependencies are missing
    @dataclass
    class SemanticCompletion:
        completion_text: str
        completion_type: str
        description: str
        architectural_context: str
        confidence: float
        imports_needed: List[str]

from domain.services.semantic_search_service import (
    SemanticSearchService,
    SemanticSearchQuery,
    SearchScope,
)

logger = logging.getLogger(__name__)


@dataclass
class CompletionContext:
    """Context for code completion"""
    file_path: str
    cursor_line: int
    cursor_column: int
    current_line: str
    preceding_lines: List[str]
    following_lines: List[str]
    project_type: str  # "kthulu", "general"
    language: str
    module_name: Optional[str] = None
    component_type: Optional[str] = None


@dataclass
class CompletionRequest:
    """Request for semantic code completion"""
    context: CompletionContext
    partial_input: str
    completion_type: str  # "method", "type", "import", "pattern", "auto"
    max_suggestions: int = 10
    tenant_id: str = "default"


@dataclass
class ArchitecturalCompletion(SemanticCompletion):
    """Extended completion with architectural context"""
    pattern_type: Optional[str] = None
    related_components: List[str] = None
    usage_examples: List[str] = None


class SemanticCodeCompletionService:
    """Service for semantic code completion"""
    
    def __init__(
        self,
        llm: LLMPort,
        knowledge_graph: Optional[KnowledgeGraphPort] = None,
        tenant_id: str = "default"
    ):
        """Initialize the semantic code completion service"""
        self.llm = llm
        self.knowledge_graph = knowledge_graph
        self.tenant_id = tenant_id
        
        # Initialize semantic search if knowledge graph is available
        self.semantic_search = None
        if knowledge_graph:
            self.semantic_search = SemanticSearchService(knowledge_graph, llm)
        
        # Cache for completion patterns
        self.completion_cache: Dict[str, List[SemanticCompletion]] = {}
        
        logger.info(f"SemanticCodeCompletionService initialized for tenant {tenant_id}")
    
    def get_completions(self, request: CompletionRequest) -> List[ArchitecturalCompletion]:
        """
        Get semantic code completions
        
        Args:
            request: Completion request with context
            
        Returns:
            List of architectural completions
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(request)
            
            # Check cache first
            if cache_key in self.completion_cache:
                cached_completions = self.completion_cache[cache_key]
                return [self._to_architectural_completion(comp) for comp in cached_completions]
            
            # Generate completions based on type
            if request.completion_type == "auto":
                completions = self._auto_detect_completions(request)
            elif request.completion_type == "method":
                completions = self._get_method_completions(request)
            elif request.completion_type == "type":
                completions = self._get_type_completions(request)
            elif request.completion_type == "import":
                completions = self._get_import_completions(request)
            elif request.completion_type == "pattern":
                completions = self._get_pattern_completions(request)
            else:
                completions = self._get_general_completions(request)
            
            # Cache results
            self.completion_cache[cache_key] = completions[:request.max_suggestions]
            
            # Convert to architectural completions
            return [self._to_architectural_completion(comp) for comp in completions[:request.max_suggestions]]
            
        except Exception as e:
            logger.exception(f"Error getting completions: {str(e)}")
            return [self._create_error_completion(str(e))]
    
    def _auto_detect_completions(self, request: CompletionRequest) -> List[SemanticCompletion]:
        """Auto-detect the type of completion needed"""
        
        context = request.context
        partial = request.partial_input.strip()
        current_line = context.current_line.strip()
        
        # Detect completion type based on context
        if current_line.startswith('import') or 'import' in current_line:
            return self._get_import_completions(request)
        elif partial.endswith('.'):
            return self._get_method_completions(request)
        elif self._is_type_context(context):
            return self._get_type_completions(request)
        elif self._is_pattern_context(context):
            return self._get_pattern_completions(request)
        else:
            return self._get_general_completions(request)
    
    def _get_method_completions(self, request: CompletionRequest) -> List[SemanticCompletion]:
        """Get method/function completions"""
        
        completions = []
        
        # Extract object/type before the dot
        partial = request.partial_input
        if '.' in partial:
            object_part = partial.rsplit('.', 1)[0]
            method_prefix = partial.rsplit('.', 1)[1] if len(partial.rsplit('.', 1)) > 1 else ""
        else:
            object_part = ""
            method_prefix = partial
        
        # Get architectural context
        arch_context = self._get_architectural_context(request.context)
        
        # Generate method suggestions using LLM
        method_prompt = self._create_method_completion_prompt(
            request.context, object_part, method_prefix, arch_context
        )
        
        try:
            llm_response = self.llm.generate(method_prompt, self.tenant_id)
            method_data = json.loads(llm_response)
            
            for method in method_data:
                completion = SemanticCompletion(
                    completion_text=method.get("method_name", ""),
                    completion_type="method",
                    description=method.get("description", ""),
                    architectural_context=method.get("architectural_context", ""),
                    confidence=method.get("confidence", 0.5),
                    imports_needed=method.get("imports_needed", [])
                )
                completions.append(completion)
        
        except Exception as e:
            logger.error(f"Error generating method completions: {str(e)}")
            completions.append(self._create_fallback_completion("method", str(e)))
        
        return completions
    
    def _get_type_completions(self, request: CompletionRequest) -> List[SemanticCompletion]:
        """Get type/interface completions"""
        
        completions = []
        
        # Get architectural components from knowledge graph
        if self.semantic_search:
            search_query = SemanticSearchQuery(
                query_text=request.partial_input,
                scope=SearchScope.ALL,
                tenant_id=request.tenant_id
            )
            
            search_results = self.semantic_search.search(search_query)
            
            for result in search_results[:5]:
                completion = SemanticCompletion(
                    completion_text=result.component.name,
                    completion_type="type",
                    description=f"{result.component.component_type.value} from {result.component.module_namespace}",
                    architectural_context=f"Part of {result.component.module_namespace} module",
                    confidence=result.relevance_score,
                    imports_needed=self._get_required_imports(result.component, request.context)
                )
                completions.append(completion)
        
        # Generate additional type suggestions using LLM
        type_prompt = self._create_type_completion_prompt(request.context, request.partial_input)
        
        try:
            llm_response = self.llm.generate(type_prompt, self.tenant_id)
            type_data = json.loads(llm_response)
            
            for type_info in type_data:
                completion = SemanticCompletion(
                    completion_text=type_info.get("type_name", ""),
                    completion_type="type",
                    description=type_info.get("description", ""),
                    architectural_context=type_info.get("architectural_context", ""),
                    confidence=type_info.get("confidence", 0.5),
                    imports_needed=type_info.get("imports_needed", [])
                )
                completions.append(completion)
        
        except Exception as e:
            logger.error(f"Error generating type completions: {str(e)}")
        
        return completions
    
    def _get_import_completions(self, request: CompletionRequest) -> List[SemanticCompletion]:
        """Get import statement completions"""
        
        completions = []
        
        # Analyze existing imports to understand project structure
        existing_imports = self._extract_existing_imports(request.context)
        
        # Generate import suggestions based on context
        if request.context.language == "go":
            completions.extend(self._get_go_import_completions(request, existing_imports))
        elif request.context.language == "python":
            completions.extend(self._get_python_import_completions(request, existing_imports))
        
        return completions
    
    def _get_pattern_completions(self, request: CompletionRequest) -> List[SemanticCompletion]:
        """Get architectural pattern completions"""
        
        completions = []
        
        # Detect what pattern might be needed
        pattern_context = self._detect_pattern_context(request.context)
        
        if pattern_context == "repository":
            completions.extend(self._get_repository_pattern_completions(request))
        elif pattern_context == "usecase":
            completions.extend(self._get_usecase_pattern_completions(request))
        elif pattern_context == "adapter":
            completions.extend(self._get_adapter_pattern_completions(request))
        elif pattern_context == "port":
            completions.extend(self._get_port_pattern_completions(request))
        else:
            completions.extend(self._get_general_pattern_completions(request))
        
        return completions
    
    def _get_general_completions(self, request: CompletionRequest) -> List[SemanticCompletion]:
        """Get general code completions"""
        
        completions = []
        
        # Use LLM for general completions
        general_prompt = self._create_general_completion_prompt(request.context, request.partial_input)
        
        try:
            llm_response = self.llm.generate(general_prompt, self.tenant_id)
            completion_data = json.loads(llm_response)
            
            for comp_info in completion_data:
                completion = SemanticCompletion(
                    completion_text=comp_info.get("completion", ""),
                    completion_type=comp_info.get("type", "general"),
                    description=comp_info.get("description", ""),
                    architectural_context=comp_info.get("architectural_context", ""),
                    confidence=comp_info.get("confidence", 0.5),
                    imports_needed=comp_info.get("imports_needed", [])
                )
                completions.append(completion)
        
        except Exception as e:
            logger.error(f"Error generating general completions: {str(e)}")
            completions.append(self._create_fallback_completion("general", str(e)))
        
        return completions
    
    def _create_method_completion_prompt(
        self,
        context: CompletionContext,
        object_part: str,
        method_prefix: str,
        arch_context: Dict[str, Any]
    ) -> str:
        """Create prompt for method completions"""
        
        return f"""
        Generate method completions for {context.language} code in a {context.project_type} project:
        
        Context:
        - File: {context.file_path}
        - Component type: {context.component_type}
        - Module: {context.module_name}
        - Object: {object_part}
        - Method prefix: {method_prefix}
        - Architecture: {arch_context}
        
        Current line: {context.current_line}
        Preceding context:
        {chr(10).join(context.preceding_lines[-5:])}
        
        Generate relevant method suggestions following these principles:
        1. Hexagonal architecture patterns
        2. Domain-driven design
        3. {context.language} best practices
        4. Interface segregation
        
        Return JSON array:
        [{{
            "method_name": "methodName(params)",
            "description": "what this method does",
            "architectural_context": "how it fits in architecture",
            "confidence": 0.0-1.0,
            "imports_needed": ["package1"]
        }}]
        
        Limit to 8 most relevant suggestions.
        """
    
    def _create_type_completion_prompt(
        self,
        context: CompletionContext,
        partial_input: str
    ) -> str:
        """Create prompt for type completions"""
        
        return f"""
        Generate type/interface completions for {context.language} code:
        
        Context:
        - File: {context.file_path}
        - Component type: {context.component_type}
        - Partial input: {partial_input}
        
        Current context:
        {chr(10).join(context.preceding_lines[-3:])}
        {context.current_line}
        
        Focus on:
        1. Domain types and entities
        2. Port interfaces
        3. Value objects
        4. Common architectural types
        
        Return JSON array of type suggestions with same format as methods.
        Limit to 6 suggestions.
        """
    
    def _create_general_completion_prompt(
        self,
        context: CompletionContext,
        partial_input: str
    ) -> str:
        """Create prompt for general completions"""
        
        return f"""
        Generate code completions for {context.language}:
        
        File: {context.file_path}
        Partial input: {partial_input}
        Current line: {context.current_line}
        
        Context:
        {chr(10).join(context.preceding_lines[-3:])}
        
        Consider:
        1. Variable names and functions
        2. Keywords and syntax
        3. Common patterns
        4. Best practices
        
        Return JSON array of completions.
        Limit to 8 suggestions.
        """
    
    def _get_go_import_completions(
        self,
        request: CompletionRequest,
        existing_imports: List[str]
    ) -> List[SemanticCompletion]:
        """Get Go-specific import completions"""
        
        completions = []
        
        # Common Go imports for hexagonal architecture
        common_imports = [
            ("context", "Standard context package"),
            ("fmt", "Formatted I/O"),
            ("errors", "Error handling"),
            ("time", "Time utilities"),
            ("encoding/json", "JSON encoding/decoding"),
            ("net/http", "HTTP client/server"),
            ("database/sql", "SQL database interface"),
            ("github.com/google/uuid", "UUID generation"),
            ("github.com/stretchr/testify/assert", "Testing assertions"),
            ("github.com/stretchr/testify/mock", "Testing mocks")
        ]
        
        # Filter based on partial input
        partial = request.partial_input.lower()
        for import_path, description in common_imports:
            if partial in import_path.lower() and import_path not in existing_imports:
                completion = SemanticCompletion(
                    completion_text=f'"{import_path}"',
                    completion_type="import",
                    description=description,
                    architectural_context="Standard Go package",
                    confidence=0.8,
                    imports_needed=[]
                )
                completions.append(completion)
        
        return completions
    
    def _get_python_import_completions(
        self,
        request: CompletionRequest,
        existing_imports: List[str]
    ) -> List[SemanticCompletion]:
        """Get Python-specific import completions"""
        
        completions = []
        
        # Common Python imports
        common_imports = [
            ("typing", "Type hints"),
            ("dataclasses", "Data classes"),
            ("abc", "Abstract base classes"),
            ("datetime", "Date and time"),
            ("json", "JSON handling"),
            ("logging", "Logging utilities"),
            ("pathlib", "Path utilities"),
            ("uuid", "UUID generation"),
            ("pytest", "Testing framework"),
            ("pydantic", "Data validation")
        ]
        
        partial = request.partial_input.lower()
        for import_name, description in common_imports:
            if partial in import_name.lower() and import_name not in existing_imports:
                completion = SemanticCompletion(
                    completion_text=import_name,
                    completion_type="import",
                    description=description,
                    architectural_context="Standard Python package",
                    confidence=0.8,
                    imports_needed=[]
                )
                completions.append(completion)
        
        return completions
    
    def _get_repository_pattern_completions(self, request: CompletionRequest) -> List[SemanticCompletion]:
        """Get repository pattern completions"""
        
        completions = []
        
        if request.context.language == "go":
            completions.extend([
                SemanticCompletion(
                    completion_text="FindByID(ctx context.Context, id string) (*Entity, error)",
                    completion_type="method",
                    description="Find entity by ID",
                    architectural_context="Repository pattern - query method",
                    confidence=0.9,
                    imports_needed=["context"]
                ),
                SemanticCompletion(
                    completion_text="Save(ctx context.Context, entity *Entity) error",
                    completion_type="method",
                    description="Save entity",
                    architectural_context="Repository pattern - persistence method",
                    confidence=0.9,
                    imports_needed=["context"]
                ),
                SemanticCompletion(
                    completion_text="Delete(ctx context.Context, id string) error",
                    completion_type="method",
                    description="Delete entity by ID",
                    architectural_context="Repository pattern - deletion method",
                    confidence=0.9,
                    imports_needed=["context"]
                )
            ])
        
        return completions
    
    def _get_usecase_pattern_completions(self, request: CompletionRequest) -> List[SemanticCompletion]:
        """Get use case pattern completions"""
        
        completions = []
        
        if request.context.language == "go":
            completions.extend([
                SemanticCompletion(
                    completion_text="Execute(ctx context.Context, input InputDTO) (*OutputDTO, error)",
                    completion_type="method",
                    description="Execute use case",
                    architectural_context="Use case pattern - main execution method",
                    confidence=0.9,
                    imports_needed=["context"]
                ),
                SemanticCompletion(
                    completion_text="Validate(input InputDTO) error",
                    completion_type="method",
                    description="Validate input",
                    architectural_context="Use case pattern - validation method",
                    confidence=0.8,
                    imports_needed=[]
                )
            ])
        
        return completions
    
    def _get_adapter_pattern_completions(self, request: CompletionRequest) -> List[SemanticCompletion]:
        """Get adapter pattern completions"""
        
        completions = []
        
        completions.extend([
            SemanticCompletion(
                completion_text="NewAdapter(config Config) Port",
                completion_type="function",
                description="Create new adapter instance",
                architectural_context="Adapter pattern - constructor",
                confidence=0.9,
                imports_needed=[]
            )
        ])
        
        return completions
    
    def _get_port_pattern_completions(self, request: CompletionRequest) -> List[SemanticCompletion]:
        """Get port pattern completions"""
        
        completions = []
        
        if request.context.language == "go":
            completions.extend([
                SemanticCompletion(
                    completion_text="type Port interface {\n\t// Define port methods\n}",
                    completion_type="interface",
                    description="Port interface definition",
                    architectural_context="Hexagonal architecture - port definition",
                    confidence=0.9,
                    imports_needed=[]
                )
            ])
        
        return completions
    
    def _get_general_pattern_completions(self, request: CompletionRequest) -> List[SemanticCompletion]:
        """Get general architectural pattern completions"""
        
        completions = []

        # Add common architectural patterns
        completions.extend([
            SemanticCompletion(
                completion_text="class Service:\n    def __init__(self, repository: Repository):\n        self.repository = repository",
                completion_type="code",
                description="Constructor-based dependency injection of Repository",
                architectural_context="Dependency injection pattern using constructor parameters in Python",
                confidence=0.8,
                imports_needed=[]
            )
        ])

        return completions
    
    def _is_type_context(self, context: CompletionContext) -> bool:
        """Check if we're in a type declaration context"""
        
        current_line = context.current_line.strip()
        
        # Go type contexts
        if context.language == "go":
            return any(keyword in current_line for keyword in ["type ", "var ", "func ", "interface"])
        
        # Python type contexts
        elif context.language == "python":
            return any(keyword in current_line for keyword in ["class ", "def ", ": "])
        
        return False
    
    def _is_pattern_context(self, context: CompletionContext) -> bool:
        """Check if we're in an architectural pattern context"""
        
        file_name = Path(context.file_path).name.lower()
        
        # Check file name patterns
        pattern_indicators = ["usecase", "adapter", "port", "repository", "service"]
        return any(indicator in file_name for indicator in pattern_indicators)
    
    def _detect_pattern_context(self, context: CompletionContext) -> str:
        """Detect what architectural pattern context we're in"""
        
        file_name = Path(context.file_path).name.lower()
        
        if "repository" in file_name:
            return "repository"
        elif "usecase" in file_name or "use_case" in file_name:
            return "usecase"
        elif "adapter" in file_name:
            return "adapter"
        elif "port" in file_name or "interface" in file_name:
            return "port"
        else:
            return "general"
    
    def _get_architectural_context(self, context: CompletionContext) -> Dict[str, Any]:
        """Get architectural context for the current file"""
        
        return {
            "component_type": context.component_type,
            "module_name": context.module_name,
            "project_type": context.project_type,
            "file_type": self._detect_pattern_context(context)
        }
    
    def _extract_existing_imports(self, context: CompletionContext) -> List[str]:
        """Extract existing imports from the file"""
        
        imports = []
        
        for line in context.preceding_lines:
            line = line.strip()
            if context.language == "go":
                if line.startswith('import'):
                    # Extract import path
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        imports.append(match.group(1))
            elif context.language == "python":
                if line.startswith('import ') or line.startswith('from '):
                    imports.append(line)
        
        return imports
    
    def _get_required_imports(self, component, context: CompletionContext) -> List[str]:
        """Get required imports for using a component"""
        
        # This would be more sophisticated in a real implementation
        # For now, return empty list
        return []
    
    def _to_architectural_completion(self, completion: SemanticCompletion) -> ArchitecturalCompletion:
        """Convert SemanticCompletion to ArchitecturalCompletion"""
        
        return ArchitecturalCompletion(
            completion_text=completion.completion_text,
            completion_type=completion.completion_type,
            description=completion.description,
            architectural_context=completion.architectural_context,
            confidence=completion.confidence,
            imports_needed=completion.imports_needed,
            pattern_type=self._detect_pattern_type(completion),
            related_components=[],
            usage_examples=[]
        )
    
    def _detect_pattern_type(self, completion: SemanticCompletion) -> Optional[str]:
        """Detect the architectural pattern type of a completion"""
        
        context = completion.architectural_context.lower()
        
        if "repository" in context:
            return "repository"
        elif "usecase" in context or "use case" in context:
            return "usecase"
        elif "adapter" in context:
            return "adapter"
        elif "port" in context:
            return "port"
        else:
            return None
    
    def _generate_cache_key(self, request: CompletionRequest) -> str:
        """Generate cache key for completion request"""
        
        return f"{request.context.file_path}:{request.context.cursor_line}:{request.partial_input}:{request.completion_type}"
    
    def _create_fallback_completion(self, completion_type: str, error_message: str) -> SemanticCompletion:
        """Create fallback completion when generation fails"""
        
        return SemanticCompletion(
            completion_text="// Completion failed",
            completion_type=completion_type,
            description=f"Completion generation failed: {error_message}",
            architectural_context="Error",
            confidence=0.1,
            imports_needed=[]
        )
    
    def _create_error_completion(self, error_message: str) -> ArchitecturalCompletion:
        """Create error completion"""
        
        return ArchitecturalCompletion(
            completion_text="// Error in completion",
            completion_type="error",
            description=f"Completion service error: {error_message}",
            architectural_context="Error",
            confidence=0.0,
            imports_needed=[],
            pattern_type=None,
            related_components=[],
            usage_examples=[]
        )
    
    def clear_cache(self) -> None:
        """Clear completion cache"""
        self.completion_cache.clear()
        logger.info("Completion cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.completion_cache),
            "cache_keys": list(self.completion_cache.keys())[:10]  # First 10 keys
        }


def create_semantic_code_completion_service(
    llm: LLMPort,
    knowledge_graph: Optional[KnowledgeGraphPort] = None,
    tenant_id: str = "default"
) -> SemanticCodeCompletionService:
    """Factory function to create a SemanticCodeCompletionService"""
    return SemanticCodeCompletionService(
        llm=llm,
        knowledge_graph=knowledge_graph,
        tenant_id=tenant_id
    )