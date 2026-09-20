use std::sync::{Arc, Mutex};

use ferrum_engine::{sync_ast_to_graph, GraphRunner};
use ferrum_shared_models::{Module, Node, NodeType};

/// Simple in-memory mock implementing [`GraphRunner`].
struct MockGraph {
    queries: Arc<Mutex<Vec<String>>>,
}

impl MockGraph {
    fn new() -> Self {
        Self { queries: Arc::new(Mutex::new(Vec::new())) }
    }
}

impl GraphRunner for MockGraph {
    fn run_query<'a>(
        &'a self,
        cypher: String,
        _params: Vec<(&'static str, String)>,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = neo4rs::Result<()>> + Send + 'a>> {
        self.queries.lock().unwrap().push(cypher);
        Box::pin(async { Ok(()) })
    }
}

#[tokio::test]
async fn sync_creates_nodes_and_edges() {
    let module = Module {
        name: "demo".into(),
        nodes: vec![
            Node {
                id: "usecase1".into(),
                node_type: NodeType::UseCase,
                doc: None,
                description: None,
                story: None,
                input: vec![],
                output: None,
                depends_on: vec![],
                implements: None,
                view: None,
                schema: None,
                api_name: None,
                ref_node: None,
            },
            Node {
                id: "adapter1".into(),
                node_type: NodeType::Adapter,
                doc: None,
                description: None,
                story: None,
                input: vec![],
                output: None,
                depends_on: vec!["usecase1".into()],
                implements: None,
                view: None,
                schema: None,
                api_name: None,
                ref_node: None,
            },
            Node {
                id: "validator1".into(),
                node_type: NodeType::Validation,
                doc: None,
                description: Some("mod.usecase1.validate".into()),
                story: None,
                input: vec![],
                output: None,
                depends_on: vec![],
                implements: None,
                view: None,
                schema: None,
                api_name: None,
                ref_node: None,
            },
        ],
    };

    let graph = MockGraph::new();
    sync_ast_to_graph(&module, &graph).await.unwrap();

    let queries = graph.queries.lock().unwrap();

    assert!(queries.contains(&"MERGE (n:Usecase { id: $id }) SET n.description = $desc, n.output = $output".to_string()));
    assert!(queries.contains(&"MERGE (n:Adapter { id: $id }) SET n.description = $desc, n.output = $output".to_string()));
    assert!(queries.contains(&"MERGE (n:Validation { id: $id }) SET n.description = $desc, n.output = $output".to_string()));
    assert!(queries.contains(&"MATCH (a {id: $from}), (b {id: $to})\nMERGE (a)-[:DEPENDS_ON]->(b)".to_string()));
    assert!(queries.contains(&"MATCH (a {id: $from}), (b {id: $to})\nMERGE (a)-[:VALIDATES]->(b)".to_string()));
}

