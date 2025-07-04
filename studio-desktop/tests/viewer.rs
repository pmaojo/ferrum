use studio_desktop::graph::{GraphData, Node as GraphNode};
use ferrum_shared_models::NodeType;
use studio_desktop::ui::viewer::subgraph_yaml;

#[test]
fn subgraph_yaml_collects_related_nodes() {
    let nodes = vec![
        GraphNode {
            id: "a".into(),
            node_type: NodeType::Component,
            doc: None,
            description: None,
            story: None,
            input: Vec::new(),
            output: None,
            depends_on: vec!["b".into()],
            implements: None,
            view: None,
            schema: None,
            api_name: None,
            ref_node: None,
        },
        GraphNode {
            id: "b".into(),
            node_type: NodeType::Component,
            doc: None,
            description: None,
            story: None,
            input: Vec::new(),
            output: None,
            depends_on: vec![],
            implements: None,
            view: None,
            schema: None,
            api_name: None,
            ref_node: None,
        },
        GraphNode {
            id: "c".into(),
            node_type: NodeType::Component,
            doc: None,
            description: None,
            story: None,
            input: Vec::new(),
            output: None,
            depends_on: vec![],
            implements: None,
            view: None,
            schema: None,
            api_name: None,
            ref_node: None,
        },
    ];
    let data = GraphData { nodes };
    let yaml = subgraph_yaml(&data, "a").expect("yaml");
    assert!(yaml.contains("id: a"));
    assert!(yaml.contains("id: b"));
    assert!(!yaml.contains("id: c"));
}
