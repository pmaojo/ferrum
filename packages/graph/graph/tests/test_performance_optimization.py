"""
Tests for Performance Optimization Components

This module tests the incremental reasoning service, SPARQL query cache,
and background processing system.
"""

import pytest
import asyncio
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from domain.services.incremental_reasoning_service import (
    IncrementalReasoningService,
    IncrementalContext,
    ReasoningCache
)
from domain.services.sparql_query_cache import (
    SPARQLQueryCache,
    QueryCacheEntry,
    CacheStats,
    PredefinedQueryCache
)
from domain.services.background_processor import (
    BackgroundProcessor,
    BackgroundTask,
    TaskStatus,
    TaskPriority,
    TaskProgressCallback,
    submit_ontology_validation,
    submit_sparql_query,
    submit_graph_analysis
)
from domain.entities.graph_delta import (
    GraphDelta,
    ComponentChange,
    RelationshipChange,
    ChangeType,
)
from domain.entities.validation_report import ValidationReport
from domain.ontology.kthulu_ontology_loader import (
    ArchitecturalComponent,
    ArchitecturalRelationship,
    ComponentType,
)


class TestIncrementalReasoningService:
    """Tests for the incremental reasoning service"""

    @pytest.fixture
    def mock_ontology_port(self):
        port = Mock()
        port.get_module_triples.return_value = [
            ("module:auth", "rdf:type", "kth:Module"),
            ("module:auth", "kth:definesUseCase", "usecase:login"),
        ]
        return port

    @pytest.fixture
    def mock_reasoning_port(self):
        port = Mock()
        port.validate_incremental.return_value = ValidationReport(
            tenant_id="t1",
            is_consistent=True,
            violated_rules=[],
            unsat_classes=[],
            repair_suggestions=[],
            explanation="Validation successful",
            timestamp=datetime.now(),
        )
        return port

    @pytest.fixture
    def reasoning_service(self, mock_ontology_port, mock_reasoning_port):
        return IncrementalReasoningService(mock_ontology_port, mock_reasoning_port)

    def _make_component(self, module: str, name: str = "Comp") -> ArchitecturalComponent:
        return ArchitecturalComponent(
            iri=f"http://example.com/#{module}_{name}",
            component_type=ComponentType.MODULE,
            name=name,
            namespace=module,
        )

    def test_compute_reasoning_scope(self, reasoning_service):
        reasoning_service.dependency_graph = {
            "auth": {"user", "session"},
            "user": {"profile"},
            "order": {"payment"},
        }

        comp = self._make_component("auth")
        delta = GraphDelta(
            source_version="v1",
            target_version="v2",
            component_changes=[ComponentChange(change_type=ChangeType.MODIFIED, component=comp)],
            relationship_changes=[],
            timestamp=datetime.now(),
        )

        scope = reasoning_service.compute_reasoning_scope(delta)
        assert scope == {"auth", "user", "session"}

    def test_validate_incremental_cache_hit(self, reasoning_service, mock_reasoning_port):
        reasoning_service.module_hashes = {"auth": "hash123"}
        reasoning_service.reasoning_cache = {
            "hash123": ReasoningCache(
                ontology_hash="hash123",
                validation_report=ValidationReport(
                    tenant_id="t1",
                    is_consistent=True,
                    violated_rules=[],
                    unsat_classes=[],
                    repair_suggestions=[],
                    explanation="Cached result",
                    timestamp=datetime.now(),
                ),
                timestamp=datetime.now(),
                affected_modules={"auth"},
            )
        }

        delta = GraphDelta(
            source_version="v1",
            target_version="v2",
            component_changes=[],
            relationship_changes=[],
            timestamp=datetime.now(),
        )

        with patch.object(
            IncrementalReasoningService, "_compute_module_hash", return_value="hash123"
        ):
            result = reasoning_service.validate_incremental(delta)

        assert result.explanation == "Cached result"
        mock_reasoning_port.validate_incremental.assert_not_called()

    def test_validate_incremental_scope_and_cache_miss(
        self, reasoning_service, mock_reasoning_port
    ):
        reasoning_service.dependency_graph = {"auth": {"user"}, "user": set()}

        comp = self._make_component("auth")
        delta = GraphDelta(
            source_version="v1",
            target_version="v2",
            component_changes=[ComponentChange(change_type=ChangeType.MODIFIED, component=comp)],
            relationship_changes=[],
            timestamp=datetime.now(),
        )

        with patch.object(
            IncrementalReasoningService, "_compute_module_hash", return_value="newhash"
        ):
            result = reasoning_service.validate_incremental(delta)

        mock_reasoning_port.validate_incremental.assert_called_once_with({"auth", "user"})
        assert reasoning_service.module_hashes["auth"] == "newhash"
        assert result.explanation == "Validation successful"

    def test_update_dependency_graph(self, reasoning_service):
        dependencies = {
            "auth": {"user", "session"},
            "order": {"payment", "inventory"},
        }
        reasoning_service.update_dependency_graph(dependencies)
        assert reasoning_service.dependency_graph == dependencies

    def test_cache_stats(self, reasoning_service):
        reasoning_service.reasoning_cache = {"hash1": Mock(), "hash2": Mock()}
        reasoning_service.module_hashes = {"mod1": "hash1", "mod2": "hash2"}
        reasoning_service.dependency_graph = {"mod1": {"mod2"}}

        stats = reasoning_service.get_cache_stats()
        assert stats['cache_entries'] == 2
        assert stats['cached_modules'] == 2
        assert stats['dependency_edges'] == 1


class TestSPARQLQueryCache:
    """Test SPARQL query cache"""
    
    @pytest.fixture
    def mock_executor(self):
        executor = Mock()
        executor.execute_query.return_value = [
            {"module": "auth", "usecase": "login"},
            {"module": "user", "usecase": "register"}
        ]
        return executor
    
    @pytest.fixture
    def query_cache(self, mock_executor):
        return SPARQLQueryCache(
            executor=mock_executor,
            max_cache_size=10,
            default_ttl_minutes=5
        )
    
    def test_cache_hit(self, query_cache, mock_executor):
        """Test cache hit scenario"""
        query = "SELECT ?module ?usecase WHERE { ?module kth:definesUseCase ?usecase }"
        
        # First execution - cache miss
        result1 = query_cache.execute_query(query)
        assert mock_executor.execute_query.call_count == 1
        
        # Second execution - cache hit
        result2 = query_cache.execute_query(query)
        assert mock_executor.execute_query.call_count == 1  # No additional call
        assert result1 == result2
    
    def test_cache_miss_after_ttl(self, query_cache, mock_executor):
        """Test cache miss after TTL expiration"""
        query = "SELECT ?module WHERE { ?module rdf:type kth:Module }"
        
        # Execute query
        query_cache.execute_query(query)
        assert mock_executor.execute_query.call_count == 1
        
        # Simulate TTL expiration
        query_hash = query_cache._compute_query_hash(query)
        if query_hash in query_cache.cache:
            entry = query_cache.cache[query_hash]
            entry.timestamp = datetime.now() - timedelta(minutes=10)
        
        # Execute again - should be cache miss
        query_cache.execute_query(query)
        assert mock_executor.execute_query.call_count == 2
    
    def test_non_cacheable_query(self, query_cache, mock_executor):
        """Test that non-cacheable queries are not cached"""
        query = "SELECT ?time WHERE { BIND(NOW() as ?time) }"
        
        # Execute twice
        query_cache.execute_query(query)
        query_cache.execute_query(query)
        
        # Should execute both times (not cached)
        assert mock_executor.execute_query.call_count == 2
    
    def test_lru_eviction(self, query_cache, mock_executor):
        """Test LRU eviction when cache is full"""
        # Fill cache to capacity
        for i in range(15):  # More than max_cache_size (10)
            query = f"SELECT ?x WHERE {{ ?x rdf:type kth:Module{i} }}"
            query_cache.execute_query(query)
        
        # Cache should not exceed max size
        assert len(query_cache.cache) <= query_cache.max_cache_size
    
    def test_cache_stats(self, query_cache, mock_executor):
        """Test cache statistics"""
        query1 = "SELECT ?module WHERE { ?module rdf:type kth:Module }"
        query2 = "SELECT ?usecase WHERE { ?usecase rdf:type kth:UseCase }"
        
        # Execute queries
        query_cache.execute_query(query1)  # Miss
        query_cache.execute_query(query1)  # Hit
        query_cache.execute_query(query2)  # Miss
        
        stats = query_cache.get_cache_stats()
        assert stats.total_queries == 3
        assert stats.cache_hits == 1
        assert stats.cache_misses == 2
        assert stats.average_hit_ratio == 1/3
    
    def test_invalidate_pattern(self, query_cache, mock_executor):
        """Test pattern-based cache invalidation"""
        query1 = "SELECT ?module WHERE { ?module rdf:type kth:Module }"
        query2 = "SELECT ?usecase WHERE { ?usecase rdf:type kth:UseCase }"
        
        # Execute and cache queries
        query_cache.execute_query(query1)
        query_cache.execute_query(query2)
        
        # Invalidate queries containing "module"
        query_cache.invalidate_pattern("module")
        
        # Query1 should be removed, query2 should remain
        assert len(query_cache.cache) == 1
    
    def test_predefined_query_cache(self, mock_executor):
        """Test predefined query cache"""
        base_cache = SPARQLQueryCache(mock_executor)
        predefined_cache = PredefinedQueryCache(base_cache)
        
        # Execute predefined query
        result = predefined_cache.execute_predefined('module_dependencies')
        
        # Should have executed the predefined query
        assert mock_executor.execute_query.called
        assert result is not None
    
    def test_query_optimization_suggestion(self, query_cache):
        """Test cache size optimization suggestion"""
        # Add some cache entries with different hit patterns
        for i in range(5):
            entry = QueryCacheEntry(
                query_hash=f"hash{i}",
                query=f"query{i}",
                results=[],
                timestamp=datetime.now(),
                hit_count=i * 2  # Varying hit counts
            )
            query_cache.cache[f"hash{i}"] = entry
        
        suggested_size = query_cache.optimize_cache_size()
        assert isinstance(suggested_size, int)
        assert suggested_size >= 100  # Minimum suggested size


class MockProgressCallback(TaskProgressCallback):
    """Mock progress callback for testing"""
    
    def __init__(self):
        self.progress_calls = []
        self.status_calls = []
    
    def on_progress(self, task_id: str, progress: float, message: str = ""):
        self.progress_calls.append((task_id, progress, message))
    
    def on_status_change(self, task_id: str, status: TaskStatus):
        self.status_calls.append((task_id, status))


class TestBackgroundProcessor:
    """Test background processor"""
    
    @pytest.fixture
    def processor(self):
        processor = BackgroundProcessor(
            max_thread_workers=2,
            max_process_workers=1,
            enable_persistence=False
        )
        processor.start()
        yield processor
        processor.stop()
    
    def test_submit_and_execute_task(self, processor):
        """Test submitting and executing a simple task"""
        def simple_task(x, y):
            return x + y
        
        task_id = processor.submit_task(
            name="Addition Task",
            function=simple_task,
            args=(2, 3),
            priority=TaskPriority.NORMAL
        )
        
        # Wait for task completion
        timeout = time.time() + 5
        while time.time() < timeout:
            result = processor.get_task_status(task_id)
            if result and result.status == TaskStatus.COMPLETED:
                break
            time.sleep(0.1)
        
        result = processor.get_task_status(task_id)
        assert result is not None
        assert result.status == TaskStatus.COMPLETED
        assert result.result == 5
    
    def test_task_priority_ordering(self, processor):
        """Test that high priority tasks execute before low priority tasks"""
        results = []
        
        def priority_task(priority_name):
            results.append(priority_name)
            return priority_name
        
        # Submit tasks in reverse priority order
        low_task = processor.submit_task(
            name="Low Priority",
            function=priority_task,
            args=("low",),
            priority=TaskPriority.LOW
        )
        
        high_task = processor.submit_task(
            name="High Priority",
            function=priority_task,
            args=("high",),
            priority=TaskPriority.HIGH
        )
        
        # Wait for completion
        timeout = time.time() + 5
        while time.time() < timeout:
            low_result = processor.get_task_status(low_task)
            high_result = processor.get_task_status(high_task)
            if (low_result and low_result.status == TaskStatus.COMPLETED and
                high_result and high_result.status == TaskStatus.COMPLETED):
                break
            time.sleep(0.1)
        
        # High priority task should execute first
        assert results[0] == "high"
        assert results[1] == "low"
    
    def test_task_dependencies(self, processor):
        """Test task dependency resolution"""
        results = []
        
        def dependent_task(name):
            results.append(name)
            return name
        
        # Submit tasks with dependencies
        task1 = processor.submit_task(
            name="Task 1",
            function=dependent_task,
            args=("task1",)
        )
        
        task2 = processor.submit_task(
            name="Task 2",
            function=dependent_task,
            args=("task2",),
            dependencies=[task1]
        )
        
        # Wait for completion
        timeout = time.time() + 5
        while time.time() < timeout:
            result1 = processor.get_task_status(task1)
            result2 = processor.get_task_status(task2)
            if (result1 and result1.status == TaskStatus.COMPLETED and
                result2 and result2.status == TaskStatus.COMPLETED):
                break
            time.sleep(0.1)
        
        # Task1 should complete before task2
        assert results[0] == "task1"
        assert results[1] == "task2"
    
    def test_task_failure_and_retry(self, processor):
        """Test task failure and retry logic"""
        call_count = 0
        
        def failing_task():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Task failed")
            return "success"
        
        task_id = processor.submit_task(
            name="Failing Task",
            function=failing_task
        )
        
        # Wait for completion (with retries)
        timeout = time.time() + 10
        while time.time() < timeout:
            result = processor.get_task_status(task_id)
            if result and result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break
            time.sleep(0.1)
        
        result = processor.get_task_status(task_id)
        assert result is not None
        assert result.status == TaskStatus.COMPLETED
        assert result.result == "success"
        assert call_count == 3  # Should have retried
    
    def test_task_cancellation(self, processor):
        """Test task cancellation"""
        def long_running_task():
            time.sleep(2)
            return "completed"
        
        task_id = processor.submit_task(
            name="Long Running Task",
            function=long_running_task
        )
        
        # Cancel task immediately
        cancelled = processor.cancel_task(task_id)
        assert cancelled
        
        # Check status
        result = processor.get_task_status(task_id)
        assert result is not None
        assert result.status == TaskStatus.CANCELLED
    
    def test_progress_callbacks(self, processor):
        """Test progress callbacks"""
        callback = MockProgressCallback()
        
        def task_with_progress():
            return "done"
        
        task_id = processor.submit_task(
            name="Progress Task",
            function=task_with_progress
        )
        
        processor.add_progress_callback(callback)
        
        # Wait for completion
        timeout = time.time() + 5
        while time.time() < timeout:
            result = processor.get_task_status(task_id)
            if result and result.status == TaskStatus.COMPLETED:
                break
            time.sleep(0.1)
        
        # Should have received status change callbacks
        assert len(callback.status_calls) > 0
        assert any(status == TaskStatus.RUNNING for _, status in callback.status_calls)
        assert any(status == TaskStatus.COMPLETED for _, status in callback.status_calls)
    
    def test_queue_status(self, processor):
        """Test queue status reporting"""
        def simple_task():
            return "done"
        
        # Submit multiple tasks
        task_ids = []
        for i in range(3):
            task_id = processor.submit_task(
                name=f"Task {i}",
                function=simple_task
            )
            task_ids.append(task_id)
        
        # Check queue status
        status = processor.get_queue_status()
        assert status['total_tasks'] >= 3
        assert isinstance(status['pending_tasks'], int)
        assert isinstance(status['running_tasks'], int)
    
    def test_convenience_functions(self, processor):
        """Test convenience functions for common tasks"""
        # Test ontology validation submission
        with patch('domain.services.validation_rules_engine.ValidationRulesEngine'):
            task_id = submit_ontology_validation(processor, {"test": "data"})
            assert task_id is not None
            assert task_id in processor.tasks
        
        # Test SPARQL query submission
        with patch('domain.services.query_service.QueryService'):
            task_id = submit_sparql_query(processor, "SELECT * WHERE { ?s ?p ?o }")
            assert task_id is not None
            assert task_id in processor.tasks
        
        # Test graph analysis submission
        task_id = submit_graph_analysis(processor, {"nodes": [], "edges": []})
        assert task_id is not None
        assert task_id in processor.tasks


@pytest.mark.integration
class TestPerformanceIntegration:
    """Integration tests for performance optimization"""
    
    def test_incremental_reasoning_with_cache(self):
        """Test incremental reasoning with SPARQL cache integration"""
        # This would test the full integration between incremental reasoning
        # and SPARQL query caching in a real scenario
        pass
    
    def test_background_processing_with_reasoning(self):
        """Test background processing of reasoning tasks"""
        # This would test submitting reasoning tasks to background processor
        # and verifying they complete correctly
        pass
    
    def test_performance_under_load(self):
        """Test system performance under high load"""
        # This would test the system with many concurrent tasks and large graphs
        # to verify performance optimizations work correctly
        pass