use anyhow::Result;
use serde::Deserialize;
use std::path::Path;

#[derive(Debug, Deserialize)]
pub struct PluginMetadata {
    pub name: String,
    pub version: Option<String>,
    /// Relative path to the compiled dynamic library
    pub library: String,
}

impl PluginMetadata {
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let contents = std::fs::read_to_string(path)?;
        let meta: PluginMetadata = toml::from_str(&contents)?;
        Ok(meta)
    }
}
