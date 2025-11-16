use ferrum_compiler::{build_graph, find_bottlenecks, find_cycles};
use ferrum_shared_models::{Module, Node, NodeType};

fn make_node(id: &str, deps: &[&str]) -> Node {
    Node {
        id: id.to_string(),
        node_type: NodeType::UseCase,
        doc: None,
        description: None,
        story: None,
        input: Vec::new(),
        output: None,
        depends_on: deps.iter().map(|s| s.to_string()).collect(),
        implements: None,
        view: None,
        schema: None,
        api_name: None,
        ref_node: None,
    }
}

#[test]
fn detects_cycle() {
    let module = Module {
        name: "demo".to_string(),
        nodes: vec![make_node("a", &["b"]), make_node("b", &["a"])],
    };
    let g = build_graph(&[module]);
    let cycles = find_cycles(&g);
    assert!(!cycles.is_empty());
}

#[test]
fn detects_bottleneck() {
    let module = Module {
        name: "demo".to_string(),
        nodes: vec![
            make_node("center", &[]),
            make_node("a", &["center"]),
            make_node("b", &["center"]),
            make_node("c", &["center"]),
        ],
    };
    let g = build_graph(&[module]);
    let bots = find_bottlenecks(&g, 2);
    assert_eq!(bots, vec!["demo.center".to_string()]);
}
