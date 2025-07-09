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
    /// Parse graph YAML into [`GraphData`].
    ///
    /// This expects the YAML to represent a list of [`Node`] items as
    /// produced by the Ferrum backend. Any deserialization error is returned
    /// to the caller for proper handling by the UI layer.
    pub fn from_yaml(yaml: &str) -> Result<Self, serde_yaml::Error> {
        serde_yaml::from_str::<Vec<Node>>(yaml).map(|nodes| Self { nodes })
    }
}

