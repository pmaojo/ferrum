use anyhow::{bail, Result};
use std::collections::HashSet;

use crate::Module;

/// Validate a parsed [`Module`].
///
/// This checks for duplicate node IDs and ensures that all
/// dependencies and implemented ports reference existing nodes.
/// Returns an error describing the first problem encountered.
pub fn validate_module(module: &Module) -> Result<()> {
    let mut ids = HashSet::new();
    for node in &module.nodes {
        if !ids.insert(&node.id) {
            bail!("duplicate node id: {}", node.id);
        }
    }

    for node in &module.nodes {
        for dep in &node.depends_on {
            if !ids.contains(dep) {
                bail!("node '{}' depends on unknown node '{}'", node.id, dep);
            }
        }

        if let Some(port) = &node.implements {
            if !ids.contains(port) {
                bail!("node '{}' implements unknown port '{}'", node.id, port);
            }
        }
    }

    Ok(())
}
