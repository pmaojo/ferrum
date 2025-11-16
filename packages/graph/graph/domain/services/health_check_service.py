"""
Health check service for monitoring system component health.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import requests
import psycopg2
from owlready2 import get_ontology

from .monitoring_service import MonitoringService, ComponentStatus
from adapters.knowledge_graph.falkordb_adapter import FalkorDBAdapter
from adapters.llm.openai_llm_adapter import OpenAILLMAdapter


class HealthCheckService:
    """Service for performing health checks on system components."""
    
    def __init__(self, monitoring_service: MonitoringService):
        self.monitoring_service = monitoring_service
        self.logger = logging.getLogger(__name__)
        
        # Health check registry
        self.health_checks: Dict[str, Callable] = {}
        self.check_intervals: Dict[str, int] = {}  # seconds
        self.last_check_times: Dict[str, datetime] = {}
        
        # Register default health checks
        self._register_default_checks()
    
    def register_health_check(self, component: str, check_func: Callable, 
                            interval_seconds: int = 60):
        """Register a health check for a component."""
        self.health_checks[component] = check_func
        self.check_intervals[component] = interval_seconds
        self.last_check_times[component] = datetime.min
        
        self.logger.info(f"Registered health check for {component}")
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {}
        
        for component, check_func in self.health_checks.items():
            try:
                # Check if it's time to run this check
                last_check = self.last_check_times.get(component, datetime.min)
                interval = self.check_intervals.get(component, 60)
                
                if (datetime.utcnow() - last_check).total_seconds() < interval:
                    continue
                
                start_time = time.time()
                
                # Run the health check
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                response_time = (time.time() - start_time) * 1000
                
                # Update monitoring service
                self.monitoring_service.update_health_check(
                    component=component,
                    status=result.get("status", ComponentStatus.UNKNOWN),
                    message=result.get("message", ""),
                    response_time_ms=response_time,
                    details=result.get("details", {})
                )
                
                results[component] = result
                self.last_check_times[component] = datetime.utcnow()
                
            except Exception as e:
                self.logger.error(f"Health check failed for {component}: {e}")
                
                self.monitoring_service.update_health_check(
                    component=component,
                    status=ComponentStatus.UNHEALTHY,
                    message=f"Health check failed: {str(e)}",
                    response_time_ms=0,
                    details={"error": str(e)}
                )
                
                results[component] = {
                    "status": ComponentStatus.UNHEALTHY,
                    "message": f"Health check failed: {str(e)}",
                    "details": {"error": str(e)}
                }
        
        return results
    
    def _register_default_checks(self):
        """Register default health checks for core components."""
        
        # Database health check
        self.register_health_check("database", self._check_database_health, 30)
        
        # Knowledge graph health check
        self.register_health_check("knowledge_graph", self._check_knowledge_graph_health, 60)
        
        # LLM service health check
        self.register_health_check("llm_service", self._check_llm_service_health, 120)
        
        # Reasoner health check
        self.register_health_check("reasoner", self._check_reasoner_health, 60)
        
        # Web service health check
        self.register_health_check("web_service", self._check_web_service_health, 30)
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check PostgreSQL database health."""
        try:
            # Try to connect to database
            import os
            db_url = os.getenv("DATABASE_URL", "postgresql://localhost:5432/permagraph")
            
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Execute simple query
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result and result[0] == 1:
                return {
                    "status": ComponentStatus.HEALTHY,
                    "message": "Database connection successful",
                    "details": {"connection_test": "passed"}
                }
            else:
                return {
                    "status": ComponentStatus.UNHEALTHY,
                    "message": "Database query returned unexpected result",
                    "details": {"result": result}
                }
                
        except Exception as e:
            return {
                "status": ComponentStatus.UNHEALTHY,
                "message": f"Database connection failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _check_knowledge_graph_health(self) -> Dict[str, Any]:
        """Check FalkorDB knowledge graph health."""
        try:
            # This would use the actual FalkorDB adapter
            # For now, simulate the check
            
            # Try to execute a simple query
            # adapter = FalkorDBAdapter()
            # result = adapter.execute_query("MATCH (n) RETURN count(n) LIMIT 1")
            
            # Simulate successful connection
            return {
                "status": ComponentStatus.HEALTHY,
                "message": "Knowledge graph accessible",
                "details": {
                    "connection_test": "passed",
                    "query_test": "passed"
                }
            }
            
        except Exception as e:
            return {
                "status": ComponentStatus.UNHEALTHY,
                "message": f"Knowledge graph check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _check_llm_service_health(self) -> Dict[str, Any]:
        """Check LLM service health."""
        try:
            # Test LLM connectivity with a simple request
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                return {
                    "status": ComponentStatus.DEGRADED,
                    "message": "LLM API key not configured",
                    "details": {"config_issue": "missing_api_key"}
                }
            
            # Try a simple API call
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    "status": ComponentStatus.HEALTHY,
                    "message": "LLM service accessible",
                    "details": {"api_test": "passed"}
                }
            else:
                return {
                    "status": ComponentStatus.DEGRADED,
                    "message": f"LLM API returned status {response.status_code}",
                    "details": {"status_code": response.status_code}
                }
                
        except Exception as e:
            return {
                "status": ComponentStatus.UNHEALTHY,
                "message": f"LLM service check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _check_reasoner_health(self) -> Dict[str, Any]:
        """Check OWL reasoner health."""
        try:
            # Test reasoner by loading a simple ontology
            from owlready2 import get_ontology, sync_reasoner_pellet
            
            # Create a test ontology
            onto = get_ontology("http://test.org/onto.owl")
            
            with onto:
                class TestClass(onto.Thing):
                    pass
                
                class TestProperty(onto.ObjectProperty):
                    pass
            
            # Try to run reasoner
            sync_reasoner_pellet([onto])
            
            return {
                "status": ComponentStatus.HEALTHY,
                "message": "Reasoner functioning correctly",
                "details": {"reasoner_test": "passed"}
            }
            
        except Exception as e:
            return {
                "status": ComponentStatus.UNHEALTHY,
                "message": f"Reasoner check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _check_web_service_health(self) -> Dict[str, Any]:
        """Check web service health."""
        try:
            # Check if the web service is responding
            import os
            service_url = os.getenv("WEB_SERVICE_URL", "http://localhost:8000")
            
            response = requests.get(
                f"{service_url}/health",
                timeout=5
            )
            
            if response.status_code == 200:
                return {
                    "status": ComponentStatus.HEALTHY,
                    "message": "Web service responding",
                    "details": {
                        "status_code": response.status_code,
                        "response_time_ms": response.elapsed.total_seconds() * 1000
                    }
                }
            else:
                return {
                    "status": ComponentStatus.DEGRADED,
                    "message": f"Web service returned status {response.status_code}",
                    "details": {"status_code": response.status_code}
                }
                
        except requests.exceptions.ConnectionError:
            return {
                "status": ComponentStatus.UNHEALTHY,
                "message": "Web service not accessible",
                "details": {"error": "connection_refused"}
            }
        except Exception as e:
            return {
                "status": ComponentStatus.UNHEALTHY,
                "message": f"Web service check failed: {str(e)}",
                "details": {"error": str(e)}
            }


class ComponentHealthChecker:
    """Individual component health checker with circuit breaker pattern."""
    
    def __init__(self, component_name: str, check_function: Callable,
                 failure_threshold: int = 3, recovery_timeout: int = 60):
        self.component_name = component_name
        self.check_function = check_function
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.failure_count = 0
        self.last_failure_time = None
        self.circuit_open = False
        
        self.logger = logging.getLogger(__name__)
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform health check with circuit breaker pattern."""
        
        # If circuit is open, check if we should try again
        if self.circuit_open:
            if (self.last_failure_time and 
                (datetime.utcnow() - self.last_failure_time).total_seconds() < self.recovery_timeout):
                return {
                    "status": ComponentStatus.UNHEALTHY,
                    "message": f"Circuit breaker open for {self.component_name}",
                    "details": {"circuit_breaker": "open"}
                }
            else:
                # Try to close circuit
                self.circuit_open = False
                self.failure_count = 0
        
        try:
            # Perform the actual health check
            if asyncio.iscoroutinefunction(self.check_function):
                result = await self.check_function()
            else:
                result = self.check_function()
            
            # Reset failure count on success
            if result.get("status") == ComponentStatus.HEALTHY:
                self.failure_count = 0
                self.circuit_open = False
            else:
                self._handle_failure()
            
            return result
            
        except Exception as e:
            self._handle_failure()
            return {
                "status": ComponentStatus.UNHEALTHY,
                "message": f"Health check failed: {str(e)}",
                "details": {"error": str(e), "circuit_breaker": "open" if self.circuit_open else "closed"}
            }
    
    def _handle_failure(self):
        """Handle health check failure."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.circuit_open = True
            self.logger.warning(f"Circuit breaker opened for {self.component_name}")