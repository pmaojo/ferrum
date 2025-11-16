"""
Natural Language Query Service

Provides natural language interface for architecture queries,
integrating with the AdvancedAIAgent to process user queries
and return structured responses.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from ..agents.advanced_ai_agent import (
    AdvancedAIAgent, 
    NaturalLanguageQuery, 
    QueryResponse, 
    QueryType
)
from application.ports.base import MessageBusPort, LLMPort
from application.ports.knowledge_graph_port import KnowledgeGraphPort

logger = logging.getLogger(__name__)


@dataclass
class QuerySession:
    """Represents a query session with context"""
    session_id: str
    tenant_id: str
    queries: List[NaturalLanguageQuery]
    responses: List[QueryResponse]
    context: Dict[str, Any]
    created_at: datetime
    last_activity: datetime


class NaturalLanguageQueryService:
    """Service for processing natural language architecture queries"""
    
    def __init__(
        self,
        message_bus: MessageBusPort,
        llm: LLMPort,
        knowledge_graph: KnowledgeGraphPort,
        tenant_id: str = "default"
    ):
        """Initialize the natural language query service"""
        self.message_bus = message_bus
        self.llm = llm
        self.knowledge_graph = knowledge_graph
        self.tenant_id = tenant_id
        
        # Initialize AI agent
        self.ai_agent = AdvancedAIAgent(
            message_bus=message_bus,
            llm=llm,
            knowledge_graph=knowledge_graph,
            tenant_id=tenant_id
        )
        
        # Session management
        self.active_sessions: Dict[str, QuerySession] = {}
        
        # Start the AI agent
        self.ai_agent.start()
        
        logger.info(f"NaturalLanguageQueryService initialized for tenant {tenant_id}")
    
    def process_query(
        self,
        query_text: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language query
        
        Args:
            query_text: The natural language query
            session_id: Optional session ID for context
            context: Additional context for the query
            
        Returns:
            Dictionary containing query response and metadata
        """
        try:
            # Create or get session
            if session_id:
                session = self.active_sessions.get(session_id)
                if not session:
                    session = self._create_session(session_id, context or {})
            else:
                session_id = f"session_{datetime.now().timestamp()}"
                session = self._create_session(session_id, context or {})
            
            # Create query object
            query = NaturalLanguageQuery(
                query_text=query_text,
                context=session.context,
                tenant_id=self.tenant_id
            )
            
            # Classify query type
            query.query_type = self._classify_query_type(query_text)
            
            # Process query through AI agent
            response = self.ai_agent._process_natural_language_query(query)
            
            # Update session
            session.queries.append(query)
            session.responses.append(response)
            session.last_activity = datetime.now()
            
            # Return structured response
            return {
                "session_id": session_id,
                "query": query_text,
                "query_type": query.query_type.value if query.query_type else "unknown",
                "response": response.response_text,
                "structured_data": response.structured_data,
                "confidence": response.confidence,
                "suggestions": response.suggestions,
                "related_components": [
                    {
                        "iri": comp.iri,
                        "name": comp.name,
                        "type": comp.component_type.value,
                        "module": comp.module_namespace
                    }
                    for comp in response.related_components
                ],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception(f"Error processing query: {str(e)}")
            return {
                "session_id": session_id or "error",
                "query": query_text,
                "query_type": "error",
                "response": f"I encountered an error processing your query: {str(e)}",
                "structured_data": {"error": str(e)},
                "confidence": 0.0,
                "suggestions": ["Try rephrasing your query", "Check for typos"],
                "related_components": [],
                "timestamp": datetime.now().isoformat()
            }
    
    def get_query_suggestions(self, partial_query: str) -> List[str]:
        """
        Get query suggestions based on partial input
        
        Args:
            partial_query: Partial query text
            
        Returns:
            List of suggested completions
        """
        suggestions = []
        
        # Common query patterns
        common_patterns = [
            "Find all components that depend on {component}",
            "Show me the architecture patterns in {module}",
            "What are the anti-patterns in my code?",
            "List all use cases in {module}",
            "Show relationships between {component1} and {component2}",
            "Analyze the quality of my architecture",
            "Find circular dependencies",
            "Show me all adapters that implement {port}",
            "What domain events are emitted by {usecase}?",
            "Review the code in {file}"
        ]
        
        # Filter suggestions based on partial input
        partial_lower = partial_query.lower()
        for pattern in common_patterns:
            if any(word in pattern.lower() for word in partial_lower.split()):
                suggestions.append(pattern)
        
        # Add context-specific suggestions
        if "find" in partial_lower or "show" in partial_lower:
            suggestions.extend([
                "Find components with high coupling",
                "Show me the hexagonal architecture structure",
                "Find unused ports or adapters"
            ])
        
        if "review" in partial_lower or "analyze" in partial_lower:
            suggestions.extend([
                "Review my architecture for SOLID violations",
                "Analyze dependency inversion compliance",
                "Review code for domain-driven design issues"
            ])
        
        return suggestions[:10]  # Limit to top 10 suggestions
    
    def get_session_history(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get query history for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session history or None if not found
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        return {
            "session_id": session_id,
            "tenant_id": session.tenant_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "query_count": len(session.queries),
            "queries": [
                {
                    "query_text": query.query_text,
                    "query_type": query.query_type.value if query.query_type else "unknown",
                    "timestamp": datetime.now().isoformat()  # Would be stored in real implementation
                }
                for query in session.queries
            ],
            "responses": [
                {
                    "response_text": response.response_text,
                    "confidence": response.confidence,
                    "suggestions": response.suggestions
                }
                for response in session.responses
            ]
        }
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear a query session
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was cleared, False if not found
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False
    
    def get_active_sessions(self) -> List[str]:
        """
        Get list of active session IDs
        
        Returns:
            List of active session IDs
        """
        return list(self.active_sessions.keys())
    
    def _create_session(self, session_id: str, context: Dict[str, Any]) -> QuerySession:
        """Create a new query session"""
        session = QuerySession(
            session_id=session_id,
            tenant_id=self.tenant_id,
            queries=[],
            responses=[],
            context=context,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        self.active_sessions[session_id] = session
        return session
    
    def _classify_query_type(self, query_text: str) -> QueryType:
        """Classify the type of natural language query"""
        query_lower = query_text.lower()
        
        # Component search patterns
        if any(word in query_lower for word in ["find", "search", "show", "list", "get"]):
            if any(word in query_lower for word in ["component", "module", "usecase", "adapter", "port"]):
                return QueryType.COMPONENT_SEARCH
        
        # Relationship analysis patterns
        if any(word in query_lower for word in ["depends", "uses", "calls", "relationship", "connected"]):
            return QueryType.RELATIONSHIP_ANALYSIS
        
        # Pattern detection patterns
        if any(word in query_lower for word in ["pattern", "architecture", "design", "structure"]):
            return QueryType.PATTERN_DETECTION
        
        # Code review patterns
        if any(word in query_lower for word in ["review", "improve", "suggest", "fix", "optimize"]):
            return QueryType.CODE_SUGGESTION
        
        # Anti-pattern patterns
        if any(word in query_lower for word in ["problem", "issue", "violation", "anti-pattern", "smell"]):
            return QueryType.ANTI_PATTERN_CHECK
        
        # Default to architecture review
        return QueryType.ARCHITECTURE_REVIEW
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status information"""
        return {
            "service": "natural_language_query",
            "tenant_id": self.tenant_id,
            "active_sessions": len(self.active_sessions),
            "ai_agent_status": self.ai_agent.get_status(),
            "timestamp": datetime.now().isoformat()
        }


def create_natural_language_query_service(
    message_bus: MessageBusPort,
    llm: LLMPort,
    knowledge_graph: KnowledgeGraphPort,
    tenant_id: str = "default"
) -> NaturalLanguageQueryService:
    """Factory function to create a NaturalLanguageQueryService"""
    return NaturalLanguageQueryService(
        message_bus=message_bus,
        llm=llm,
        knowledge_graph=knowledge_graph,
        tenant_id=tenant_id
    )