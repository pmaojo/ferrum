"""
FalkorDB Client con configuración correcta y principios SOLID.
Implementa Dependency Inversion Principle y Single Responsibility Principle.
"""
import os
import redis
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod


class GraphDatabaseClient(ABC):
    """Abstract base class para clientes de bases de datos de grafos."""
    
    @abstractmethod
    def ping(self) -> bool:
        """Verifica la conectividad del servicio."""
        pass
    
    @abstractmethod
    def execute_query(self, graph_name: str, query: str) -> Dict[str, Any]:
        """Ejecuta una consulta en el grafo especificado."""
        pass


class FalkorDBClient(GraphDatabaseClient):
    """Cliente FalkorDB con configuración robusta y inyección de dependencias."""
    
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self.host = host or os.getenv("FALKORDB_HOST", "localhost")
        self.port = int(port or os.getenv("FALKORDB_PORT", "6380"))  # Puerto correcto
        self.client = self._create_client()
    
    def _create_client(self) -> redis.Redis:
        """Factory method para crear el cliente Redis/FalkorDB."""
        try:
            client = redis.Redis(
                host=self.host, 
                port=self.port, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=10
            )
            # Verificar conexión inmediatamente
            if not client.ping():
                raise ConnectionError(f"No se pudo conectar a FalkorDB en {self.host}:{self.port}")
            return client
        except Exception as e:
            raise ConnectionError(f"Error creando cliente FalkorDB: {e}")
    
    def ping(self) -> bool:
        """Verifica que FalkorDB esté respondiendo."""
        try:
            return self.client.ping()
        except Exception:
            return False
    
    def execute_query(self, graph_name: str, query: str) -> Dict[str, Any]:
        """Ejecuta una consulta Cypher en FalkorDB."""
        try:
            result = self.client.execute_command("GRAPH.QUERY", graph_name, query)
            return self._parse_result(result)
        except Exception as e:
            raise RuntimeError(f"Error ejecutando query en grafo '{graph_name}': {e}")
    
    def list_graphs(self) -> List[str]:
        """Lista todos los grafos disponibles."""
        try:
            return self.client.execute_command("GRAPH.LIST")
        except Exception as e:
            raise RuntimeError(f"Error listando grafos: {e}")
    
    def create_optometry_graph(self) -> Dict[str, Any]:
        """Crea un grafo de prueba para optometría clínica."""
        query = """
        CREATE 
            (myopia:RefractiveError {name: 'Myopia', sphere_range: 'negative', symptoms: ['distance_blur', 'squinting']}),
            (hyperopia:RefractiveError {name: 'Hyperopia', sphere_range: 'positive', symptoms: ['eye_strain', 'headaches']}),
            (astigmatism:RefractiveError {name: 'Astigmatism', cylinder_required: true, symptoms: ['blurred_vision', 'distortion']}),
            (patient:Patient {id: 'P001', age: 25, gender: 'F'}),
            (exam:Examination {date: '2025-09-03', type: 'comprehensive'}),
            (measurement:Measurement {OD_sphere: -2.25, OD_cylinder: -0.50, OS_sphere: -2.00, OS_cylinder: -0.75})
        
        CREATE 
            (patient)-[:HAS_EXAMINATION]->(exam),
            (exam)-[:INCLUDES_MEASUREMENT]->(measurement),
            (measurement)-[:INDICATES]->(myopia)
        
        RETURN myopia, hyperopia, astigmatism, patient
        """
        return self.execute_query("optometry_clinic", query)
    
    def _parse_result(self, result) -> Dict[str, Any]:
        """Parsea el resultado de FalkorDB a un formato más usable."""
        if not result:
            return {"nodes": [], "relationships": [], "metadata": {}}
        
        try:
            # result[0]: headers, result[1]: data, result[2]: metadata
            headers = result[0] if len(result) > 0 else []
            data = result[1] if len(result) > 1 else []
            metadata = result[2] if len(result) > 2 else []
            
            return {
                "headers": headers,
                "data": data,
                "metadata": metadata,
                "success": True
            }
        except Exception as e:
            return {"error": str(e), "success": False}


def get_falkor_client() -> FalkorDBClient:
    """Factory function para obtener un cliente FalkorDB configurado."""
    return FalkorDBClient()


# Test de integración
if __name__ == "__main__":
    print("🧪 Test de integración FalkorDB")
    
    try:
        client = get_falkor_client()
        print(f"✅ Cliente creado: {client.host}:{client.port}")
        
        # Test 1: Ping
        if client.ping():
            print("✅ PING: Conexión exitosa")
        else:
            print("❌ PING: Fallo de conexión")
            exit(1)
        
        # Test 2: Listar grafos
        graphs = client.list_graphs()
        print(f"📊 Grafos disponibles: {graphs}")
        
        # Test 3: Crear grafo de optometría
        result = client.create_optometry_graph()
        if result.get("success"):
            print("✅ Grafo de optometría creado exitosamente")
            print(f"📈 Metadata: {result.get('metadata', [])}")
        else:
            print(f"❌ Error creando grafo: {result.get('error')}")
        
        print("🎉 Test de integración completado")
        
    except Exception as e:
        print(f"💥 Error en test de integración: {e}")
        exit(1)
