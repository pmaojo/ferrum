"""Graph analytics service implementation using NetworkX."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import networkx as nx

from application.exceptions import ValidationError
from application.ports import GraphAnalyticsPort, GraphRepositoryPort
from application.validators import RequestValidator


@dataclass
class GraphAnalyticsService(GraphAnalyticsPort):
    """Compute graph metrics using a repository of triples."""

    repository: GraphRepositoryPort
    validator: RequestValidator = field(default_factory=RequestValidator)

    def _load_graph(self, kg_id: str, tenant_id: str) -> nx.Graph:
        """Build a NetworkX graph from repository triples."""
        triples = self.repository.get_triples(kg_id=kg_id, tenant_id=tenant_id)
        graph = nx.DiGraph()
        for triple in triples:
            graph.add_edge(triple.subject, triple.object, predicate=triple.predicate)
        return graph

    # GraphAnalyticsPort implementation
    def analyze_structure(self, *, kg_id: str, tenant_id: str) -> Dict[str, float]:
        self.validator.validate_tenant_id(tenant_id)
        self.validator.validate_kg_id(kg_id)

        graph = self._load_graph(kg_id, tenant_id)
        undirected = graph.to_undirected()

        metrics: Dict[str, float] = {
            "node_count": float(graph.number_of_nodes()),
            "edge_count": float(graph.number_of_edges()),
            "density": float(nx.density(undirected)) if graph.number_of_nodes() else 0.0,
            "average_degree": (
                float(sum(dict(graph.degree()).values()) / graph.number_of_nodes())
                if graph.number_of_nodes()
                else 0.0
            ),
            "clustering_coefficient": float(nx.average_clustering(undirected))
            if graph.number_of_nodes()
            else 0.0,
            "transitivity": float(nx.transitivity(undirected)) if graph.number_of_nodes() else 0.0,
            "connected_components": float(nx.number_connected_components(undirected))
            if graph.number_of_nodes()
            else 0.0,
        }

        if graph.number_of_nodes() > 0 and nx.is_connected(undirected):
            metrics.update(
                {
                    "diameter": float(nx.diameter(undirected)),
                    "average_path_length": float(nx.average_shortest_path_length(undirected)),
                    "largest_component_size": float(
                        len(max(nx.connected_components(undirected), key=len))
                    ),
                    "assortativity": float(nx.degree_assortativity_coefficient(undirected)),
                }
            )
        else:
            metrics.update(
                {
                    "diameter": 0.0,
                    "average_path_length": 0.0,
                    "largest_component_size": 0.0,
                    "assortativity": 0.0,
                }
            )

        return metrics

    def calculate_centrality(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        centrality_types: List[str],
        node_ids: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, float]]:
        self.validator.validate_tenant_id(tenant_id)
        self.validator.validate_kg_id(kg_id)

        graph = self._load_graph(kg_id, tenant_id)
        subgraph = graph if node_ids is None else graph.subgraph(node_ids)

        results: Dict[str, Dict[str, float]] = {}
        for centrality_type in centrality_types:
            if centrality_type == "betweenness":
                values = nx.betweenness_centrality(subgraph)
            elif centrality_type == "closeness":
                values = nx.closeness_centrality(subgraph)
            elif centrality_type == "degree":
                values = {n: float(d) for n, d in subgraph.degree()}
            elif centrality_type == "eigenvector":
                values = nx.eigenvector_centrality(subgraph, max_iter=1000)
            elif centrality_type == "pagerank":
                values = nx.pagerank(subgraph)
            else:
                raise ValidationError(
                    message=f"Unsupported centrality type: {centrality_type}",
                    field="centrality_types",
                )

            for node, value in values.items():
                results.setdefault(node, {})[centrality_type] = float(value)

        return results

    def find_shortest_path(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        source_node_id: str,
        target_node_id: str,
        max_depth: int = 10,
        weight_property: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        self.validator.validate_tenant_id(tenant_id)
        self.validator.validate_kg_id(kg_id)

        graph = self._load_graph(kg_id, tenant_id)

        try:
            path = nx.shortest_path(
                graph,
                source=source_node_id,
                target=target_node_id,
                weight=weight_property,
            )
        except nx.NetworkXNoPath:
            return None

        if len(path) - 1 > max_depth:
            return None

        return {"nodes": path, "length": float(len(path) - 1)}

