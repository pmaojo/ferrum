//! Ferrum runtime engine.
//!
//! The engine exposes functions that operate on the shared data models,
//! such as synchronizing an AST with an external graph database.

pub mod services;

pub use services::graph_sync::sync_ast_to_graph;
