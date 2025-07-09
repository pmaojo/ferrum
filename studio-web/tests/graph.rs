use studio_web::graph::GraphData;
use ferrum_shared_models::NodeType;

#[test]
fn parse_valid_graph_yaml() {
    let yaml = "- id: a\n  type: component";
    let graph = GraphData::from_yaml(yaml).expect("graph");
    assert_eq!(graph.nodes.len(), 1);
    assert_eq!(graph.nodes[0].id, "a");
    assert_eq!(graph.nodes[0].node_type, NodeType::Component);
}

#[test]
fn parse_invalid_graph_yaml_returns_err() {
    let yaml = "invalid";
    assert!(GraphData::from_yaml(yaml).is_err());
}
