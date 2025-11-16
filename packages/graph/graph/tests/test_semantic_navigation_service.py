"""
Tests for Semantic Navigation Service

Tests the integration of semantic search, dependency path visualization,
impact analysis, and architectural pattern detection.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from domain.services.semantic_navigation_service import (
    SemanticNavigationService,
    NavigationContext,
    SemanticNavigationResult
)
from domain.services.semantic_search_service import SemanticSearchQuery, SearchResult
from domain.entities.architectural_component import ArchitecturalComponent, ComponentType


class TestSemanticNavigationService:
    
    @pytest.fixture
    def mock_knowledge_graph(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm(self):
        return Mock()
    
    @pytest.fixture
    def navigation_service(self, mock_knowledge_graph, mock_llm):
        return SemanticNavigationService(mock_knowledge_graph, mock_llm)
    
    @pytest.fixture
    def sample_component(self):
        return ArchitecturalComponent(
            iri="http://kthulu.io/ontology#UserModule",
            component_type=ComponentType.MODULE,
            name="UserModule",
            module_namespace="user",
            properties={},
            relationships=[]
        )
    
    def test_navigate_semantic_architecture_basic(self, navigation_service, mock_knowledge_graph):
        """Test basic semantic navigation functionality"""
        # Mock search results
        mock_knowledge_graph.execute_sparql_query.return_value = [
            {
                "component": "http://kthulu.io/ontology#UserModule",
                "type": "http://kthulu.io/ontology#Module",
                "name": "UserModule",
                "module": "user"
            }
        ]
        
        result = navigation_service.navigate_semantic_architecture(
            query="user management",
            tenant_id="test_tenant",
            context_id="test_context"
        )
        
        assert isinstance(result, SemanticNavigationResult)
        assert result.metadata["query"] == "user management"
        assert result.metadata["tenant_id"] == "test_tenant"
        assert "timestamp" in result.metadata
    
    def test_explore_component_neighborhood(self, navigation_service, sample_component):
        """Test component neighborhood exploration"""
        with patch.object(navigation_service.dependency_service, 'get_component_dependencies') as mock_deps:
            mock_deps.return_value = {
                "incoming": [],
                "outgoing": []
            }
            
            with patch.object(navigation_service.dependency_service, 'calculate_impact_score') as mock_impact:
                mock_impact.return_value = {
                    "impact_score": 5.0,
                    "direct_incoming": 2,
                    "direct_outgoing": 3
                }
                
                result = navigation_service.explore_component_neighborhood(
                    component_iri=sample_component.iri,
                    tenant_id="test_tenant"
                )
                
                assert "dependencies" in result
                assert "impact_score" in result
                assert "recommendations" in result
    
    def test_find_architectural_hotspots(self, navigation_service):
        """Test architectural hotspots detection"""
        with patch.object(navigation_service.dependency_service, 'analyze_dependency_graph') as mock_graph:
            mock_graph.return_value = Mock(nodes=[])
            
            result = navigation_service.find_architectural_hotspots(
                tenant_id="test_tenant",
                hotspot_type="complexity"
            )
            
            assert "complexity_hotspots" in result
            assert "coupling_hotspots" in result
            assert "pattern_hotspots" in result
            assert "anti_pattern_hotspots" in result
    
    def test_navigation_context_management(self, navigation_service):
        """Test navigation context creation and management"""
        context_id = "test_context"
        
        # First access should create new context
        context1 = navigation_service._get_navigation_context(context_id)
        assert isinstance(context1, NavigationContext)
        assert context1.search_history == []
        assert context1.visited_components == set()
        
        # Second access should return same context
        context2 = navigation_service._get_navigation_context(context_id)
        assert context1 is context2
    
    def test_search_history_management(self, navigation_service, mock_knowledge_graph):
        """Test search history tracking and limits"""
        mock_knowledge_graph.execute_sparql_query.return_value = []
        
        context_id = "test_context"
        
        # Perform multiple searches
        for i in range(55):  # More than the 50 limit
            navigation_service.navigate_semantic_architecture(
                query=f"search_{i}",
                tenant_id="test_tenant",
                context_id=context_id
            )
        
        context = navigation_service._get_navigation_context(context_id)
        
        # Should be limited to 50 entries
        assert len(context.search_history) == 50
        # Should contain most recent searches
        assert "search_54" in context.search_history
        assert "search_0" not in context.search_history
    
    def test_get_navigation_recommendations(self, navigation_service, sample_component):
        """Test navigation recommendations generation"""
        with patch.object(navigation_service, '_get_component_by_iri') as mock_get_comp:
            mock_get_comp.return_value = sample_component
            
            with patch.object(navigation_service.dependency_service, 'get_component_dependencies') as mock_deps:
                mock_deps.return_value = {
                    "incoming": [sample_component],
                    "outgoing": [sample_component]
                }
                
                recommendations = navigation_service.get_navigation_recommendations(
                    current_component_iri=sample_component.iri,
                    tenant_id="test_tenant"
                )
                
                assert isinstance(recommendations, list)
                assert len(recommendations) > 0
                assert any("depend" in rec.lower() for rec in recommendations)
    
    def test_semantic_search_integration(self, navigation_service):
        """Test integration with semantic search service"""
        with patch.object(navigation_service.search_service, 'search') as mock_search:
            mock_search.return_value = [
                SearchResult(
                    component=ArchitecturalComponent(
                        iri="test_iri",
                        component_type=ComponentType.MODULE,
                        name="TestModule",
                        module_namespace="test",
                        properties={},
                        relationships=[]
                    ),
                    relevance_score=0.9,
                    match_type="exact",
                    match_details={},
                    related_components=[]
                )
            ]
            
            result = navigation_service.navigate_semantic_architecture(
                query="test query",
                tenant_id="test_tenant"
            )
            
            assert len(result.search_results) == 1
            assert result.search_results[0].component.name == "TestModule"
    
    def test_dependency_path_integration(self, navigation_service, sample_component):
        """Test integration with dependency path service"""
        with patch.object(navigation_service.search_service, 'search') as mock_search:
            mock_search.return_value = [
                SearchResult(
                    component=sample_component,
                    relevance_score=0.9,
                    match_type="exact",
                    match_details={},
                    related_components=[]
                )
            ]
            
            with patch.object(navigation_service.dependency_service, 'find_dependency_paths') as mock_paths:
                mock_paths.return_value = []
                
                # Set current component in context
                context = navigation_service._get_navigation_context("default")
                context.current_component = sample_component
                
                result = navigation_service.navigate_semantic_architecture(
                    query="test query",
                    tenant_id="test_tenant"
                )
                
                # Should have called dependency path finding
                mock_paths.assert_called()
    
    def test_pattern_detection_integration(self, navigation_service):
        """Test integration with pattern detection service"""
        with patch.object(navigation_service.pattern_service, 'analyze_patterns') as mock_patterns:
            mock_patterns.return_value = Mock(
                detected_patterns=[],
                anti_patterns=[]
            )
            
            result = navigation_service.navigate_semantic_architecture(
                query="test query",
                tenant_id="test_tenant",
                include_patterns=True
            )
            
            # Should have called pattern analysis
            mock_patterns.assert_called_once_with("test_tenant")
    
    def test_impact_analysis_integration(self, navigation_service, sample_component):
        """Test integration with impact analysis service"""
        with patch.object(navigation_service.search_service, 'search') as mock_search:
            mock_search.return_value = [
                SearchResult(
                    component=sample_component,
                    relevance_score=0.9,
                    match_type="exact",
                    match_details={},
                    related_components=[]
                )
            ]
            
            with patch.object(navigation_service.impact_service, 'analyze_change_impact') as mock_impact:
                mock_impact.return_value = Mock(
                    risk_assessment={"overall_risk": "LOW"},
                    estimated_total_effort=5.0,
                    confidence_score=0.8
                )
                
                result = navigation_service.navigate_semantic_architecture(
                    query="test query",
                    tenant_id="test_tenant",
                    include_impact=True
                )
                
                # Should have called impact analysis
                mock_impact.assert_called()
                assert result.impact_analysis is not None
    
    def test_component_by_iri_retrieval(self, navigation_service, mock_knowledge_graph):
        """Test component retrieval by IRI"""
        mock_knowledge_graph.execute_sparql_query.return_value = [
            {
                "type": "http://kthulu.io/ontology#Module",
                "name": "TestModule",
                "module": "test"
            }
        ]
        
        component = navigation_service._get_component_by_iri(
            "http://kthulu.io/ontology#TestModule",
            "test_tenant"
        )
        
        assert component is not None
        assert component.name == "TestModule"
        assert component.component_type == ComponentType.MODULE
    
    def test_component_by_iri_not_found(self, navigation_service, mock_knowledge_graph):
        """Test component retrieval when component not found"""
        mock_knowledge_graph.execute_sparql_query.return_value = []
        
        component = navigation_service._get_component_by_iri(
            "http://kthulu.io/ontology#NonExistent",
            "test_tenant"
        )
        
        assert component is None
    
    def test_navigation_recommendations_generation(self, navigation_service):
        """Test navigation recommendations generation logic"""
        search_results = [
            SearchResult(
                component=ArchitecturalComponent(
                    iri="test_iri",
                    component_type=ComponentType.MODULE,
                    name="TestModule",
                    module_namespace="test",
                    properties={},
                    relationships=[]
                ),
                relevance_score=0.9,
                match_type="exact",
                match_details={},
                related_components=[]
            )
        ]
        
        context = NavigationContext(
            current_component=None,
            search_history=[],
            visited_components=set(),
            navigation_path=[],
            filters={},
            preferences={}
        )
        
        recommendations = navigation_service._generate_navigation_recommendations(
            search_results=search_results,
            dependency_paths=[],
            detected_patterns=[],
            context=context
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any("Found" in rec for rec in recommendations)
    
    def test_navigation_suggestions_generation(self, navigation_service):
        """Test navigation suggestions generation logic"""
        search_results = [
            SearchResult(
                component=ArchitecturalComponent(
                    iri="test_iri",
                    component_type=ComponentType.USECASE,
                    name="TestUseCase",
                    module_namespace="test",
                    properties={},
                    relationships=[]
                ),
                relevance_score=0.9,
                match_type="exact",
                match_details={},
                related_components=[]
            )
        ]
        
        context = NavigationContext(
            current_component=None,
            search_history=["previous search"],
            visited_components=set(),
            navigation_path=[],
            filters={},
            preferences={}
        )
        
        suggestions = navigation_service._generate_navigation_suggestions(
            search_results=search_results,
            context=context,
            tenant_id="test_tenant"
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert any("TestUseCase" in sug for sug in suggestions)


if __name__ == "__main__":
    pytest.main([__file__])