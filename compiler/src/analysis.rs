use ferrum_shared_models::{Module, NodeType};
use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::Direction;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct NodeInfo {
    pub id: String,
    pub layer: NodeType,
}

pub type ModuleGraph = DiGraph<NodeInfo, ()>;

/// Build a directed graph from modules where each node is identified by
/// `module.node` and edges represent `depends_on` relationships.
pub fn build_graph(modules: &[Module]) -> ModuleGraph {
    let mut graph = ModuleGraph::new();
    let mut map: HashMap<String, NodeIndex> = HashMap::new();

    // Add nodes
    for m in modules {
        for n in &m.nodes {
            let id = format!("{}.{}", m.name, n.id);
            let info = NodeInfo {
                id: id.clone(),
                layer: n.node_type.clone(),
            };
            let idx = graph.add_node(info);
            map.insert(id, idx);
        }
    }

    // Add edges
    for m in modules {
        for n in &m.nodes {
            let from_id = format!("{}.{}", m.name, n.id);
            if let Some(&from_idx) = map.get(&from_id) {
                for dep in &n.depends_on {
                    if let Some(target_mod) = modules
                        .iter()
                        .find(|mm| mm.nodes.iter().any(|nn| nn.id == *dep))
                    {
                        let to_id = format!("{}.{}", target_mod.name, dep);
                        if let Some(&to_idx) = map.get(&to_id) {
                            graph.add_edge(from_idx, to_idx, ());
                        }
                    }
                }
            }
        }
    }
    graph
}

/// Return strongly connected components representing cycles.
pub fn find_cycles(graph: &ModuleGraph) -> Vec<Vec<String>> {
    petgraph::algo::tarjan_scc(graph)
        .into_iter()
        .filter(|scc| scc.len() > 1)
        .map(|scc| {
            scc.into_iter()
                .map(|idx| graph[idx].id.clone())
                .collect()
        })
        .collect()
}

/// Detect bottlenecks defined as nodes with incoming degree greater than
/// `threshold`.
pub fn find_bottlenecks(graph: &ModuleGraph, threshold: usize) -> Vec<String> {
    graph
        .node_indices()
        .filter(|&idx| graph.neighbors_directed(idx, Direction::Incoming).count() > threshold)
        .map(|idx| graph[idx].id.clone())
        .collect()
}

/// Classify nodes by their architectural layer.
pub fn classify_layers(modules: &[Module]) -> HashMap<NodeType, Vec<String>> {
    let mut map: HashMap<NodeType, Vec<String>> = HashMap::new();
    for m in modules {
        for n in &m.nodes {
            map.entry(n.node_type.clone())
                .or_default()
                .push(format!("{}.{}", m.name, n.id));
        }
    }
    map
}
