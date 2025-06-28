use anyhow::{Context, Result};
use std::fs;
use std::path::Path;

use ferrum_shared_models::Module;

pub fn parse_yaml<P: AsRef<Path>>(path: P) -> Result<Module> {
    let content = fs::read_to_string(&path)
        .with_context(|| format!("Failed to read file: {}", path.as_ref().display()))?;

    let module: Module = serde_yaml::from_str(&content)
        .with_context(|| format!("Failed to parse YAML from: {}", path.as_ref().display()))?;

    Ok(module)
}
