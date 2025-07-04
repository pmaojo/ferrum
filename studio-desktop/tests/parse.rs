use studio_desktop::graph::parse_graph_yaml;
use ferrum_shared_models::{Node, NodeType};

#[test]
fn parse_valid_graph_yaml() {
    let yaml = "- id: a\n  type: Component";
    let nodes = parse_graph_yaml(yaml).expect("nodes");
    assert_eq!(nodes.len(), 1);
    assert_eq!(nodes[0].id, "a");
    assert_eq!(nodes[0].node_type, NodeType::Component);
}

#[test]
fn parse_invalid_graph_yaml_returns_err() {
    let yaml = "invalid";
    assert!(parse_graph_yaml(yaml).is_err());
}
