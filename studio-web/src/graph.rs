//! Graph data structures and loading helpers.
//!
//! Intended to replicate the behaviour of `studio-desktop::graph` but for the web
//! environment. Implementations should be asynchronous and use [`GraphApi`] for
//! data fetching.

use ferrum_shared_models::Node;

/// In-memory representation of the current graph.
#[derive(Default, Clone)]
pub struct GraphData {
    /// All nodes parsed from the DSL.
    pub nodes: Vec<Node>,
    // TODO: store additional metadata like edges or layouts.
}

impl GraphData {
    /// Parse graph YAML into [`GraphData`]. Placeholder implementation.
    pub fn from_yaml(_yaml: &str) -> Result<Self, serde_yaml::Error> {
        // TODO: parse YAML using ferrum_shared_models structures
        Ok(Self::default())
    }
}

