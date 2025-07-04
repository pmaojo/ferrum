//! Graph-related services.
//!
//! This module provides utilities to synchronize the in-memory architecture
//! representation with a Neo4j graph database.

use anyhow::Result;
use ferrum_shared_models::{Module, NodeType};
use neo4rs::{query, Graph, Query};
use std::{future::Future, pin::Pin};

/// Abstraction over a graph database capable of running Cypher queries.
///
/// This allows testing [`sync_ast_to_graph`] without a real Neo4j instance.
pub trait GraphRunner {
    /// Execute a query and discard any result stream.
    fn run_query<'a>(&'a self, q: Query) -> Pin<Box<dyn Future<Output = neo4rs::Result<()>> + Send + 'a>>;
}

impl GraphRunner for Graph {
    fn run_query<'a>(&'a self, q: Query) -> Pin<Box<dyn Future<Output = neo4rs::Result<()>> + Send + 'a>> {
        Box::pin(async move { self.run(q).await.map(|_| ()) })
    }
}

/// Synchronize an AST [`Module`] with a Neo4j graph database.
///
/// Each node is created with a label based on [`NodeType`]. Edges are
/// created using the `DEPENDS_ON` relationship for any declared
/// dependency.
///
/// This function is idempotent thanks to Cypher's `MERGE` clauses.
pub async fn sync_ast_to_graph(module: &Module, graph: &impl GraphRunner) -> Result<()> {
    for node in &module.nodes {
        let label = match node.node_type {
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
        };

        // Merge node with basic properties
        graph
            .run_query(
                query(
                    format!(
                        "MERGE (n:{label} {{ id: $id }}) SET n.description = $desc, n.output = $output"
                    )
                    .as_str(),
                )
                .param("id", node.id.clone())
                .param("desc", node.description.clone())
                .param("output", node.output.clone()),
            )
            .await?;

        // Dependencies
        for dep in &node.depends_on {
            graph
                .run_query(
                    query("MATCH (a {id: $from}), (b {id: $to})\nMERGE (a)-[:DEPENDS_ON]->(b)")
                        .param("from", node.id.clone())
                        .param("to", dep.clone()),
                )
                .await?;
        }

        // Implements relationship
        if let Some(port) = &node.implements {
            graph
                .run_query(
                    query("MATCH (a {id: $from}), (b {id: $to})\nMERGE (a)-[:IMPLEMENTS]->(b)")
                        .param("from", node.id.clone())
                        .param("to", port.clone()),
                )
                .await?;
        }

        if matches!(node.node_type, NodeType::Validation) {
            if let Some(applies) = &node.description {
                let parts: Vec<&str> = applies.split('.').collect();
                if parts.len() >= 2 {
                    let usecase = parts[parts.len() - 2];
                    graph
                        .run_query(
                            query(
                                "MATCH (a {id: $from}), (b {id: $to})\nMERGE (a)-[:VALIDATES]->(b)",
                            )
                            .param("from", node.id.clone())
                            .param("to", usecase.to_string()),
                        )
                        .await?;
                }
            }
        }
    }
    Ok(())
}
