"""
Tests for Advanced AI Agent

Tests the advanced AI capabilities including natural language queries,
code review suggestions, semantic completion, and anti-pattern detection.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any

from domain.agents.advanced_ai_agent import (
    AdvancedAIAgent,
    NaturalLanguageQuery,
    QueryResponse,
    QueryType,
    CodeReviewSuggestion,
    SemanticCompletion
)
from domain.entities.architectural_component import ArchitecturalComponent, ComponentType
from application.ports.base import MessageBusPort, LLMPort
from application.ports.knowledge_graph_port import KnowledgeGraphPort


class TestAdvancedAIAgent:
    """Test suite for AdvancedAIAgent"""
    
    @pytest.fixture
    def mock_message_bus(self):
        """Mock message bus"""
        return Mock(spec=MessageBusPort)
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM service"""
        return Mock(spec=LLMPort)
    
    @pytest.fixture
    def mock_knowledge_graph(self):
        """Mock knowledge graph"""
        return Mock(spec=KnowledgeGraphPort)
    
    @pytest.fixture
    def agent(self, mock_message_bus, mock_llm, mock_knowledge_graph):
        """Create AdvancedAIAgent instance"""
        return AdvancedAIAgent(
            message_bus=mock_message_bus,
            llm=mock_llm,
            knowledge_graph=mock_knowledge_graph,
            tenant_id="test_tenant"
        )
    
    @pytest.fixture
    def sample_component(self):
        """Sample architectural component"""
        return ArchitecturalComponent(
            iri="http://kthulu.io/ontology#UserService",
            component_type=ComponentType.USECASE,
            name="UserService",
            module_namespace="user",
            properties={},
            relationships=[]
        )
    
    def test_agent_initialization(self, agent, mock_message_bus):
        """Test agent initialization"""
        assert agent.tenant_id == "test_tenant"
        assert agent.is_running is False
        assert agent.query_count == 0
        assert agent.review_count == 0
        assert agent.completion_count == 0
        
        # Verify subscriptions
        expected_topics = [
            "ai.natural_language_query",
            "ai.code_review_request", 
            "ai.semantic_completion_request",
            "ai.anti_pattern_detection",
            "agent.coordination"
        ]
        
        assert mock_message_bus.subscribe.call_count == len(expected_topics)
    
    def test_start_stop_agent(self, agent, mock_message_bus):
        """Test agent start/stop lifecycle"""
        # Start agent
        agent.start()
        assert agent.is_running is True
        
        # Verify start message published
        mock_message_bus.publish.assert_called_with(
            topic="agent.status",
            message={
                "agent_type": "advanced_ai",
                "status": "started",
                "tenant_id": "test_tenant",
                "timestamp": pytest.approx(datetime.now().isoformat(), abs=1)
            },
            tenant_id="test_tenant"
        )
        
        # Stop agent
        agent.stop()
        assert agent.is_running is False
    
    def test_get_status(self, agent):
        """Test agent status reporting"""
        agent.query_count = 5
        agent.review_count = 3
        agent.completion_count = 10
        
        status = agent.get_status()
        
        assert status == {
            "agent_type": "advanced_ai",
            "is_running": False,
            "tenant_id": "test_tenant",
            "query_count": 5,
            "review_count": 3,
            "completion_count": 10
        }
    
    def test_classify_query_component_search(self, agent):
        """Test query classification for component search"""
        queries = [
            "find all components",
            "search for UserService",
            "show me all adapters",
            "list modules in auth"
        ]
        
        for query in queries:
            query_type = agent._classify_query(query)
            assert query_type == QueryType.COMPONENT_SEARCH
    
    def test_classify_query_relationship_analysis(self, agent):
        """Test query classification for relationship analysis"""
        queries = [
            "what depends on UserService",
            "show relationships between modules",
            "which components use AuthPort",
            "find connections to database"
        ]
        
        for query in queries:
            query_type = agent._classify_query(query)
            assert query_type == QueryType.RELATIONSHIP_ANALYSIS
    
    def test_classify_query_pattern_detection(self, agent):
        """Test query classification for pattern detection"""
        queries = [
            "analyze architecture patterns",
            "show design patterns",
            "what patterns are implemented",
            "check hexagonal architecture"
        ]
        
        for query in queries:
            query_type = agent._classify_query(query)
            assert query_type == QueryType.PATTERN_DETECTION
    
    def test_classify_query_anti_pattern_check(self, agent):
        """Test query classification for anti-pattern detection"""
        queries = [
            "find problems in code",
            "check for anti-patterns",
            "what issues exist",
            "detect code smells"
        ]
        
        for query in queries:
            query_type = agent._classify_query(query)
            assert query_type == QueryType.ANTI_PATTERN_CHECK
    
    @patch('domain.agents.advanced_ai_agent.agent.SemanticSearchService')
    def test_handle_component_search_query(self, mock_search_service, agent, sample_component):
        """Test handling component search queries"""
        # Setup mock search service
        mock_search_instance = Mock()
        mock_search_service.return_value = mock_search_instance
        
        mock_search_result = Mock()
        mock_search_result.component = sample_component
        mock_search_result.relevance_score = 0.95
        mock_search_result.match_type = "exact"
        
        mock_search_instance.search.return_value = [mock_search_result]
        
        # Create query
        query = NaturalLanguageQuery(
            query_text="find UserService",
            query_type=QueryType.COMPONENT_SEARCH,
            tenant_id="test_tenant"
        )
        
        # Process query
        response = agent._handle_component_search_query(query)
        
        # Verify response
        assert isinstance(response, QueryResponse)
        assert response.confidence == 0.9
        assert "Found 1 components" in response.response_text
        assert "UserService" in response.response_text
        assert len(response.related_components) == 1
        assert response.related_components[0] == sample_component
    
    @patch('domain.agents.advanced_ai_agent.agent.ArchitecturalPatternService')
    def test_handle_pattern_detection_query(self, mock_pattern_service, agent):
        """Test handling pattern detection queries"""
        # Setup mock pattern service
        mock_pattern_instance = Mock()
        mock_pattern_service.return_value = mock_pattern_instance
        
        mock_analysis = Mock()
        mock_analysis.detected_patterns = []
        mock_analysis.anti_patterns = []
        mock_analysis.architecture_quality_score = 85.0
        mock_analysis.recommendations = ["Implement CQRS pattern"]
        
        mock_pattern_instance.analyze_patterns.return_value = mock_analysis
        
        # Create query
        query = NaturalLanguageQuery(
            query_text="analyze architecture patterns",
            query_type=QueryType.PATTERN_DETECTION,
            tenant_id="test_tenant"
        )
        
        # Process query
        response = agent._handle_pattern_detection_query(query)
        
        # Verify response
        assert isinstance(response, QueryResponse)
        assert response.confidence == 0.9
        assert "Quality Score: 85.0/100" in response.response_text
        assert "Implement CQRS pattern" in response.suggestions
    
    def test_handle_natural_language_query_message(self, agent, mock_message_bus):
        """Test handling natural language query messages"""
        agent.start()
        
        # Mock the query processing
        with patch.object(agent, '_process_natural_language_query') as mock_process:
            mock_response = QueryResponse(
                query=Mock(),
                response_text="Test response",
                structured_data={},
                confidence=0.8,
                suggestions=["Test suggestion"],
                related_components=[]
            )
            mock_process.return_value = mock_response
            
            # Simulate message
            message = {
                "query": "test query",
                "context": {"source": "test"}
            }
            
            agent._handle_natural_language_query(message)
            
            # Verify response published
            mock_message_bus.publish.assert_called()
            call_args = mock_message_bus.publish.call_args
            assert call_args[1]["topic"] == "ai.natural_language_response"
            assert call_args[1]["message"]["response"] == "Test response"
    
    def test_generate_code_review_suggestions(self, agent, mock_llm):
        """Test generating code review suggestions"""
        # Mock LLM response
        mock_llm_response = '''[
            {
                "line_number": 15,
                "suggestion_type": "architecture",
                "title": "Direct database dependency",
                "description": "Use case directly imports database package",
                "suggested_fix": "Create repository interface",
                "confidence": 0.9,
                "architectural_impact": "high"
            }
        ]'''
        mock_llm.generate.return_value = mock_llm_response
        
        # Generate suggestions
        suggestions = agent._generate_code_review_suggestions(
            "test.go",
            "package main\nimport \"database/sql\"",
            {"project_type": "kthulu"}
        )
        
        # Verify suggestions
        assert len(suggestions) == 1
        suggestion = suggestions[0]
        assert isinstance(suggestion, CodeReviewSuggestion)
        assert suggestion.line_number == 15
        assert suggestion.suggestion_type == "architecture"
        assert suggestion.title == "Direct database dependency"
        assert suggestion.confidence == 0.9
        assert suggestion.architectural_impact == "high"
    
    def test_generate_semantic_completions(self, agent, mock_llm):
        """Test generating semantic completions"""
        # Mock LLM response
        mock_llm_response = '''[
            {
                "completion_text": "Execute(ctx context.Context, input Input) error",
                "completion_type": "method",
                "description": "Execute use case",
                "architectural_context": "Use case pattern",
                "confidence": 0.9,
                "imports_needed": ["context"]
            }
        ]'''
        mock_llm.generate.return_value = mock_llm_response
        
        # Generate completions
        completions = agent._generate_semantic_completions(
            "test.go",
            {"line": 10, "column": 5},
            "func Execute",
            "Exec"
        )
        
        # Verify completions
        assert len(completions) == 1
        completion = completions[0]
        assert isinstance(completion, SemanticCompletion)
        assert completion.completion_text == "Execute(ctx context.Context, input Input) error"
        assert completion.completion_type == "method"
        assert completion.confidence == 0.9
        assert "context" in completion.imports_needed
    
    def test_handle_code_review_request(self, agent, mock_message_bus, mock_llm):
        """Test handling code review requests"""
        agent.start()
        
        # Mock LLM response
        mock_llm.generate.return_value = '''[
            {
                "line_number": 10,
                "suggestion_type": "quality",
                "title": "Add error handling",
                "description": "Function should handle errors",
                "suggested_fix": "Add error check",
                "confidence": 0.8,
                "architectural_impact": "medium"
            }
        ]'''
        
        # Simulate message
        message = {
            "file_path": "test.go",
            "code_content": "package main\nfunc test() {}",
            "context": {"project_type": "kthulu"}
        }
        
        agent._handle_code_review_request(message)
        
        # Verify response published
        mock_message_bus.publish.assert_called()
        call_args = mock_message_bus.publish.call_args
        assert call_args[1]["topic"] == "ai.code_review_response"
        assert len(call_args[1]["message"]["suggestions"]) == 1
        
        # Verify counter incremented
        assert agent.review_count == 1
    
    def test_handle_semantic_completion_request(self, agent, mock_message_bus, mock_llm):
        """Test handling semantic completion requests"""
        agent.start()
        
        # Mock LLM response
        mock_llm.generate.return_value = '''[
            {
                "completion_text": "NewUserService",
                "completion_type": "function",
                "description": "Constructor for UserService",
                "architectural_context": "Service factory",
                "confidence": 0.85,
                "imports_needed": []
            }
        ]'''
        
        # Simulate message
        message = {
            "file_path": "user_service.go",
            "cursor_position": {"line": 10, "column": 5},
            "code_context": "package user\n",
            "partial_input": "New"
        }
        
        agent._handle_semantic_completion_request(message)
        
        # Verify response published
        mock_message_bus.publish.assert_called()
        call_args = mock_message_bus.publish.call_args
        assert call_args[1]["topic"] == "ai.semantic_completion_response"
        assert len(call_args[1]["message"]["completions"]) == 1
        
        # Verify counter incremented
        assert agent.completion_count == 1
    
    @patch('domain.agents.advanced_ai_agent.agent.ArchitecturalPatternService')
    def test_handle_anti_pattern_detection(self, mock_pattern_service, agent, mock_message_bus):
        """Test handling anti-pattern detection"""
        agent.start()
        
        # Setup mock pattern service
        mock_pattern_instance = Mock()
        mock_pattern_service.return_value = mock_pattern_instance
        
        mock_anti_pattern = Mock()
        mock_anti_pattern.pattern_type.value = "god_object"
        mock_anti_pattern.confidence.value = "high"
        mock_anti_pattern.description = "Component is too large"
        mock_anti_pattern.components = [Mock(name="UserService")]
        mock_anti_pattern.evidence = ["Too many methods"]
        mock_anti_pattern.recommendations = ["Break into smaller components"]
        
        mock_analysis = Mock()
        mock_analysis.anti_patterns = [mock_anti_pattern]
        mock_pattern_instance.analyze_patterns.return_value = mock_analysis
        
        # Simulate message
        message = {"scan_type": "full"}
        
        agent._handle_anti_pattern_detection(message)
        
        # Verify response published
        mock_message_bus.publish.assert_called()
        call_args = mock_message_bus.publish.call_args
        assert call_args[1]["topic"] == "ai.anti_pattern_report"
        assert len(call_args[1]["message"]["anti_patterns"]) == 1
    
    def test_calculate_severity(self, agent):
        """Test anti-pattern severity calculation"""
        from domain.services.architectural_pattern_service import PatternType
        
        # Mock anti-pattern objects
        high_severity_pattern = Mock()
        high_severity_pattern.pattern_type = PatternType.GOD_OBJECT
        
        medium_severity_pattern = Mock()
        medium_severity_pattern.pattern_type = PatternType.ANEMIC_DOMAIN_MODEL
        
        low_severity_pattern = Mock()
        low_severity_pattern.pattern_type = PatternType.FEATURE_ENVY
        
        # Test severity calculation
        assert agent._calculate_severity(high_severity_pattern) == "high"
        assert agent._calculate_severity(medium_severity_pattern) == "medium"
        assert agent._calculate_severity(low_severity_pattern) == "low"
    
    def test_error_handling_in_query_processing(self, agent, mock_llm):
        """Test error handling in query processing"""
        # Mock LLM to raise exception
        mock_llm.generate.side_effect = Exception("LLM service unavailable")
        
        query = NaturalLanguageQuery(
            query_text="test query",
            query_type=QueryType.ARCHITECTURE_REVIEW,
            tenant_id="test_tenant"
        )
        
        # Process query - should not raise exception
        response = agent._handle_general_architecture_query(query)
        
        # Verify error response
        assert isinstance(response, QueryResponse)
        assert response.confidence == 0.3
        assert "having trouble" in response.response_text.lower()
    
    def test_error_handling_in_code_review(self, agent, mock_llm):
        """Test error handling in code review"""
        # Mock LLM to raise exception
        mock_llm.generate.side_effect = Exception("Analysis failed")
        
        # Generate suggestions - should not raise exception
        suggestions = agent._generate_code_review_suggestions(
            "test.go",
            "invalid code",
            {}
        )
        
        # Verify fallback suggestion
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_type == "error"
        assert "Analysis failed" in suggestions[0].description
    
    def test_agent_coordination_handling(self, agent):
        """Test agent coordination message handling"""
        # Mock pattern service for anti-pattern detection
        with patch.object(agent, '_handle_anti_pattern_detection') as mock_handler:
            message = {
                "action": "architecture_analysis_request",
                "tenant_id": "test_tenant"
            }
            
            agent._handle_agent_coordination(message)
            
            # Verify anti-pattern detection was triggered
            mock_handler.assert_called_once_with(message)
    
    def test_comprehensive_analysis(self, agent):
        """Test comprehensive AI analysis"""
        with patch.object(agent, '_process_natural_language_query') as mock_query, \
             patch.object(agent.pattern_service, 'analyze_patterns') as mock_patterns:
            
            # Setup mocks
            mock_response = Mock()
            mock_response.response_text = "Analysis complete"
            mock_response.confidence = 0.9
            mock_response.suggestions = ["Improve architecture"]
            mock_query.return_value = mock_response
            
            mock_analysis = Mock()
            mock_analysis.architecture_quality_score = 85.0
            mock_analysis.detected_patterns = []
            mock_analysis.anti_patterns = []
            mock_patterns.return_value = mock_analysis
            
            # Perform analysis
            result = agent._perform_comprehensive_analysis("analyze my architecture")
            
            # Verify result
            assert "query_response" in result
            assert "pattern_analysis" in result
            assert result["query_response"]["confidence"] == 0.9
            assert result["pattern_analysis"]["quality_score"] == 85.0


class TestAdvancedAIAgentIntegration:
    """Integration tests for AdvancedAIAgent"""
    
    @pytest.fixture
    def integration_agent(self):
        """Create agent with real-like mocks for integration testing"""
        message_bus = Mock(spec=MessageBusPort)
        llm = Mock(spec=LLMPort)
        knowledge_graph = Mock(spec=KnowledgeGraphPort)
        
        return AdvancedAIAgent(
            message_bus=message_bus,
            llm=llm,
            knowledge_graph=knowledge_graph,
            tenant_id="integration_test"
        )
    
    def test_full_natural_language_workflow(self, integration_agent):
        """Test complete natural language query workflow"""
        integration_agent.start()
        
        # Mock semantic search results
        with patch.object(integration_agent.semantic_search, 'search') as mock_search:
            mock_result = Mock()
            mock_result.component = Mock()
            mock_result.component.name = "UserService"
            mock_result.component.component_type = ComponentType.USECASE
            mock_result.component.module_namespace = "user"
            mock_result.component.iri = "http://test.com/UserService"
            mock_result.relevance_score = 0.95
            mock_result.match_type = "exact"
            mock_search.return_value = [mock_result]
            
            # Process query
            message = {
                "query": "find UserService component",
                "context": {"source": "test"}
            }
            
            integration_agent._handle_natural_language_query(message)
            
            # Verify message bus was called
            integration_agent.message_bus.publish.assert_called()
            
            # Verify query count incremented
            assert integration_agent.query_count == 1
    
    def test_full_code_review_workflow(self, integration_agent):
        """Test complete code review workflow"""
        integration_agent.start()
        
        # Mock LLM response for code review
        integration_agent.llm.generate.return_value = '''[
            {
                "line_number": 15,
                "suggestion_type": "architecture",
                "title": "Dependency inversion violation",
                "description": "Direct dependency on infrastructure",
                "suggested_fix": "Use dependency injection",
                "confidence": 0.95,
                "architectural_impact": "high"
            }
        ]'''
        
        # Process code review request
        message = {
            "file_path": "internal/user/usecase/create_user.go",
            "code_content": "package usecase\nimport \"database/sql\"\nfunc CreateUser() {}",
            "context": {
                "project_type": "kthulu",
                "architecture_style": "hexagonal"
            }
        }
        
        integration_agent._handle_code_review_request(message)
        
        # Verify response published
        integration_agent.message_bus.publish.assert_called()
        call_args = integration_agent.message_bus.publish.call_args
        assert call_args[1]["topic"] == "ai.code_review_response"
        
        # Verify review count incremented
        assert integration_agent.review_count == 1
    
    def test_agent_lifecycle_with_coordinator(self, integration_agent):
        """Test agent lifecycle with coordinator integration"""
        # Mock agent coordinator
        mock_coordinator = Mock()
        integration_agent.agent_coordinator = mock_coordinator
        
        # Start agent
        integration_agent.start()
        assert integration_agent.is_running
        
        # Test workflow handling
        workflow_message = {
            "workflow_id": "test_workflow",
            "workflow_type": "advanced_ai_analysis",
            "query": "analyze architecture"
        }
        
        with patch.object(integration_agent, '_perform_comprehensive_analysis') as mock_analysis:
            mock_analysis.return_value = {"result": "analysis complete"}
            
            integration_agent._handle_coordinator_workflow(workflow_message)
            
            # Verify coordinator was updated
            mock_coordinator.update_workflow_status.assert_called()
        
        # Stop agent
        integration_agent.stop()
        assert not integration_agent.is_running


if __name__ == "__main__":
    pytest.main([__file__])