use std::future::Future;
use std::pin::Pin;

use ferrum_shared_models::{Module, Node, NodeType};
use neo4rs::Query;

pub mod plugins;

// Engine functionality will be implemented here
pub fn hello_engine() -> String {
    "Hello from Ferrum Engine!".to_string()
}

/// Abstraction over a Neo4j-shaped query runner.
///
/// `ferrum sync` needs to run Cypher against a real `neo4rs::Graph`, and its
/// tests need to run the exact same code against an in-memory recorder
/// without a live database. This trait is the seam between the two: the
/// sync logic below only ever asks "run this Cypher text with these
/// params", never touches a connection directly.
///
/// The query text and params are passed separately rather than as a single
/// `neo4rs::Query`, because `Query`'s fields are private — a mock could not
/// otherwise inspect what it was asked to run. Params are plain strings:
/// every value this module ever binds (ids, descriptions, output types) is
/// one, and `neo4rs::BoltType` isn't a public export this crate could name
/// in the signature even if it wanted a richer param type.
pub trait GraphRunner {
    fn run_query<'a>(
        &'a self,
        cypher: String,
        params: Vec<(&'static str, String)>,
    ) -> Pin<Box<dyn Future<Output = neo4rs::Result<()>> + Send + 'a>>;
}

impl GraphRunner for neo4rs::Graph {
    fn run_query<'a>(
        &'a self,
        cypher: String,
        params: Vec<(&'static str, String)>,
    ) -> Pin<Box<dyn Future<Output = neo4rs::Result<()>> + Send + 'a>> {
        let query = Query::new(cypher).params(params);
        Box::pin(async move { self.run(query).await })
    }
}

/// The Neo4j node label a [`NodeType`] merges as.
fn node_label(node_type: &NodeType) -> &'static str {
    match node_type {
        NodeType::UseCase => "Usecase",
        NodeType::Adapter => "Adapter",
        NodeType::Port => "Port",
        NodeType::Entity => "Entity",
        NodeType::Component => "Component",
        NodeType::Hook => "Hook",
        NodeType::Schema => "Schema",
        NodeType::Form => "Form",
        NodeType::Validation => "Validation",
        NodeType::Upload => "Upload",
        NodeType::Iot => "Iot",
        NodeType::Policy => "Policy",
        NodeType::Resource => "Resource",
        NodeType::VectorStore => "VectorStore",
        NodeType::AiModel => "AiModel",
    }
}

/// A [`NodeType::Validation`] node's `description` is the `appliesTo` path
/// it was compiled from (see `ferrum_compiler::dsl`), e.g.
/// `"user.register.email"` for `usecase1` in module `user`. The node it
/// validates is the middle segment.
fn validation_target(description: &str) -> Option<&str> {
    description.split('.').nth(1)
}

/// Sync a compiled [`Module`]'s nodes and edges into a graph database.
///
/// Every node is `MERGE`d as its own labelled Neo4j node, `depends_on`
/// becomes `DEPENDS_ON` edges, and `Validation` nodes get a `VALIDATES`
/// edge to the node their `appliesTo` path names.
pub async fn sync_ast_to_graph<G: GraphRunner>(
    module: &Module,
    graph: &G,
) -> anyhow::Result<()> {
    for node in &module.nodes {
        merge_node(graph, node).await?;
    }
    for node in &module.nodes {
        for dep in &node.depends_on {
            merge_edge(graph, "DEPENDS_ON", &node.id, dep).await?;
        }
        if node.node_type == NodeType::Validation {
            if let Some(target) = node.description.as_deref().and_then(validation_target) {
                merge_edge(graph, "VALIDATES", &node.id, target).await?;
            }
        }
    }
    Ok(())
}

async fn merge_node<G: GraphRunner>(graph: &G, node: &Node) -> anyhow::Result<()> {
    let label = node_label(&node.node_type);
    let cypher = format!(
        "MERGE (n:{label} {{ id: $id }}) SET n.description = $desc, n.output = $output"
    );
    let params = vec![
        ("id", node.id.clone()),
        ("desc", node.description.clone().unwrap_or_default()),
        ("output", node.output.clone().unwrap_or_default()),
    ];
    graph
        .run_query(cypher, params)
        .await
        .map_err(|e| anyhow::anyhow!("failed to sync node {}: {e}", node.id))
}

async fn merge_edge<G: GraphRunner>(
    graph: &G,
    relationship: &str,
    from: &str,
    to: &str,
) -> anyhow::Result<()> {
    let cypher =
        format!("MATCH (a {{id: $from}}), (b {{id: $to}})\nMERGE (a)-[:{relationship}]->(b)");
    let params = vec![("from", from.to_string()), ("to", to.to_string())];
    graph
        .run_query(cypher, params)
        .await
        .map_err(|e| anyhow::anyhow!("failed to sync {relationship} edge {from}->{to}: {e}"))
}
