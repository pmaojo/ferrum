use std::collections::HashSet;
use thiserror::Error;

use crate::Module;

/// Errors that can occur when validating a [`Module`].
#[derive(Debug, Error)]
pub enum ValidationError {
    /// Encountered two nodes with the same identifier.
    #[error("duplicate node id: {id}")]
    DuplicateNodeId { id: String },

    /// A node declares a dependency on another node that does not exist.
    #[error("node '{node}' depends on unknown node '{dep}'")]
    UnknownDependency { node: String, dep: String },

    /// A node implements a port that is not defined.
    #[error("node '{node}' implements unknown port '{port}'")]
    UnknownPort { node: String, port: String },
}

/// Validate a parsed [`Module`].
///
/// This checks for duplicate node IDs and ensures that all
/// dependencies and implemented ports reference existing nodes.
/// Returns an error describing the first problem encountered.
/// Result type returned by [`validate_module`].
pub type ValidationResult<T> = std::result::Result<T, ValidationError>;

/// Validate a parsed [`Module`].
///
/// This checks for duplicate node IDs and ensures that all dependencies
/// and implemented ports reference existing nodes. Detailed error types
/// are returned for easier diagnostics.
pub fn validate_module(module: &Module) -> ValidationResult<()> {
    let mut ids = HashSet::new();
    for node in &module.nodes {
        if !ids.insert(&node.id) {
            return Err(ValidationError::DuplicateNodeId {
                id: node.id.clone(),
            });
        }
    }

    for node in &module.nodes {
        for dep in &node.depends_on {
            if !ids.contains(dep) {
                return Err(ValidationError::UnknownDependency {
                    node: node.id.clone(),
                    dep: dep.clone(),
                });
            }
        }

        if let Some(port) = &node.implements {
            if !ids.contains(port) {
                return Err(ValidationError::UnknownPort {
                    node: node.id.clone(),
                    port: port.clone(),
                });
            }
        }
    }

    Ok(())
}
