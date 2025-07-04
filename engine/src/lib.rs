//! Ferrum runtime engine.
//!
//! The engine exposes functions that operate on the shared data models,
//! such as synchronizing an AST with an external graph database.

pub mod plugins;
pub mod services;

pub use plugins::{AuthPasswordPlugin, AuthPlugin, GraphQLPlugin, Plugin, PluginManager};
#[cfg(feature = "coap")]
pub use services::coap;
pub use services::graph_sync::{sync_ast_to_graph, GraphRunner};
#[cfg(feature = "mqtt")]
pub use services::mqtt;
