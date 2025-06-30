//! Graph-related services.
//!
//! This module provides utilities to synchronize the in-memory architecture
//! representation with a Neo4j graph database.

use anyhow::Result;
use ferrum_shared_models::{Module, NodeType};
use neo4rs::{query, Graph};

/// Synchronize an AST [`Module`] with a Neo4j graph database.
///
/// Each node is created with a label based on [`NodeType`]. Edges are
/// created using the `DEPENDS_ON` relationship for any declared
/// dependency.
///
/// This function is idempotent thanks to Cypher's `MERGE` clauses.
pub async fn sync_ast_to_graph(module: &Module, graph: &Graph) -> Result<()> {
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
            NodeType::Policy => "Policy",
            NodeType::Resource => "Resource",
        };

        // Merge node with basic properties
        graph
            .run(
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
                .run(
                    query("MATCH (a {id: $from}), (b {id: $to})\nMERGE (a)-[:DEPENDS_ON]->(b)")
                        .param("from", node.id.clone())
                        .param("to", dep.clone()),
                )
                .await?;
        }

        // Implements relationship
        if let Some(port) = &node.implements {
            graph
                .run(
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
                        .run(
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
