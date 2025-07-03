use studio_desktop::graph::{GraphData, Node};
use studio_desktop::ui::viewer::subgraph_yaml;

#[test]
fn subgraph_yaml_collects_related_nodes() {
    let nodes = vec![
        Node { name: "a".into(), node_type: None, description: None, story: None, calls: Some(vec!["b".into()]), used_by: None },
        Node { name: "b".into(), node_type: None, description: None, story: None, calls: None, used_by: Some(vec!["a".into()]) },
        Node { name: "c".into(), node_type: None, description: None, story: None, calls: None, used_by: None },
    ];
    let data = GraphData { nodes };
    let yaml = subgraph_yaml(&data, "a").expect("yaml");
    assert!(yaml.contains("name: a"));
    assert!(yaml.contains("name: b"));
    assert!(!yaml.contains("name: c"));
}
