use crate::{FerrumDsl, Module, Node, NodeType};

/// Expand battery features specified in the DSL into additional modules.
///
/// Currently supports a minimal `auth` feature which injects an `auth`
/// module containing an authentication service and user repository.
pub fn expand_features(project: &FerrumDsl, modules: &mut Vec<Module>) {
    if !project.app.features.contains(&"auth".to_string()) {
        return;
    }

    let mut feature_nodes = Vec::new();

    feature_nodes.push(Node {
        id: "userReaderPort".to_string(),
        node_type: NodeType::Port,
        description: None,
        story: None,
        input: Vec::new(),
        output: None,
        depends_on: Vec::new(),
        implements: None,
        view: None,
        schema: None,
        api_name: None,
    });

    feature_nodes.push(Node {
        id: "userRepository".to_string(),
        node_type: NodeType::Adapter,
        description: None,
        story: None,
        input: Vec::new(),
        output: None,
        depends_on: Vec::new(),
        implements: Some("userReaderPort".to_string()),
        view: None,
        schema: None,
        api_name: None,
    });

    feature_nodes.push(Node {
        id: "authService".to_string(),
        node_type: NodeType::UseCase,
        description: None,
        story: None,
        input: Vec::new(),
        output: Some("Session".to_string()),
        depends_on: vec!["userRepository".to_string()],
        implements: None,
        view: None,
        schema: None,
        api_name: None,
    });

    modules.push(Module {
        name: "auth".to_string(),
        nodes: feature_nodes,
    });
}
