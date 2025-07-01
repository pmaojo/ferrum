use crate::{FerrumDsl, Module, Node, NodeType};
use ferrum_shared_models::{DslAppPage, DslJob, DslRoute};

/// Expand battery features specified in the DSL into additional modules.
///
/// Currently supports a minimal `auth` feature which injects an `auth`
/// module containing an authentication service and user repository.
pub fn expand_features(project: &mut FerrumDsl, modules: &mut Vec<Module>) {
    if project.app.features.contains(&"cron".to_string()) {
        if !project.jobs.iter().any(|j| j.name == "example_job") {
            project.jobs.push(DslJob {
                name: "example_job".to_string(),
                schedule: "0 0 * * *".to_string(),
                handler: "example_job".to_string(),
                policy: None,
            });
        }
    }

    if project
        .app
        .features
        .iter()
        .any(|f| f == "realtime_sse" || f == "realtime-sse")
    {
        if !project.routes.iter().any(|r| r.path == "/events") {
            project.routes.push(DslRoute {
                name: "sse".to_string(),
                path: "/events".to_string(),
                to: "sseHandler".to_string(),
                auth_required: false,
                policy: None,
            });
            project.pages.push(DslAppPage {
                name: "sseHandler".to_string(),
                component: "sseHandler.rs".to_string(),
            });
        }

        if !modules.iter().any(|m| m.name == "realtime_sse") {
            modules.push(Module {
                name: "realtime_sse".to_string(),
                nodes: vec![Node {
                    id: "sseHandler".to_string(),
                    node_type: NodeType::UseCase,
                    doc: None,
                    description: None,
                    story: None,
                    input: Vec::new(),
                    output: None,
                    depends_on: Vec::new(),
                    implements: None,
                    view: None,
                    schema: None,
                    api_name: None,
                    ref_node: None,
                }],
            });
        }
    }

    if project.app.features.contains(&"uploads".to_string()) && project.uploads.is_empty() {
        if !modules.iter().any(|m| m.name == "uploads") {
            modules.push(Module {
                name: "uploads".to_string(),
                nodes: vec![Node {
                    id: "upload".to_string(),
                    node_type: NodeType::Upload,
                    doc: None,
                    description: Some("/upload".to_string()),
                    story: None,
                    input: Vec::new(),
                    output: None,
                    depends_on: Vec::new(),
                    implements: None,
                    view: None,
                    schema: None,
                    api_name: None,
                    ref_node: None,
                }],
            });
        }
    }

    if project.app.features.contains(&"auth".to_string()) {
        let mut feature_nodes = Vec::new();

        feature_nodes.push(Node {
            id: "userReaderPort".to_string(),
            node_type: NodeType::Port,
            doc: None,
            description: None,
            story: None,
            input: Vec::new(),
            output: None,
            depends_on: Vec::new(),
            implements: None,
            view: None,
            schema: None,
            api_name: None,
            ref_node: None,
        });

        feature_nodes.push(Node {
            id: "userRepository".to_string(),
            node_type: NodeType::Adapter,
            doc: None,
            description: None,
            story: None,
            input: Vec::new(),
            output: None,
            depends_on: Vec::new(),
            implements: Some("userReaderPort".to_string()),
            view: None,
            schema: None,
            api_name: None,
            ref_node: None,
        });

        feature_nodes.push(Node {
            id: "authService".to_string(),
            node_type: NodeType::UseCase,
            doc: None,
            description: None,
            story: None,
            input: Vec::new(),
            output: Some("Session".to_string()),
            depends_on: vec!["userRepository".to_string()],
            implements: None,
            view: None,
            schema: None,
            api_name: None,
            ref_node: None,
        });

        modules.push(Module {
            name: "auth".to_string(),
            nodes: feature_nodes,
        });
    }
}
