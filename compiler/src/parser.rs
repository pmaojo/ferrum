use anyhow::{Context, Result};
use std::fs;
use std::path::Path;

use ferrum_shared_models::{FerrumDsl, Module};

/// Parse a `grafo.yaml` file into a [`Module`] structure.
///
/// The function reads the YAML from disk and converts it into the shared
/// model representation used across the project.

pub fn parse_yaml<P: AsRef<Path>>(path: P) -> Result<Module> {
    let content = fs::read_to_string(&path)
        .with_context(|| format!("Failed to read file: {}", path.as_ref().display()))?;

    let module: Module = serde_yaml::from_str(&content)
        .with_context(|| format!("Failed to parse YAML from: {}", path.as_ref().display()))?;

    Ok(module)
}

/// Parse a `grafo.yaml` file written in the new DSL format into a [`FerrumDsl`] structure.
pub fn parse_dsl_yaml<P: AsRef<Path>>(path: P) -> Result<FerrumDsl> {
    let content = fs::read_to_string(&path)
        .with_context(|| format!("Failed to read file: {}", path.as_ref().display()))?;

    let dsl: FerrumDsl = serde_yaml::from_str(&content)
        .with_context(|| format!("Failed to parse YAML from: {}", path.as_ref().display()))?;

    Ok(dsl)
}
