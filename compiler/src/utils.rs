use anyhow::{Context, Result};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone)]
pub struct ProjectPaths {
    pub root: PathBuf,
    pub backend: PathBuf,
    pub frontend: PathBuf,
}

impl ProjectPaths {
    pub fn new<P: AsRef<Path>>(root: P) -> Self {
        let root = root.as_ref().to_path_buf();
        Self {
            backend: root.join("backend"),
            frontend: root.join("frontend"),
            root,
        }
    }
}

/// Write `content` to `path`, creating parent directories if necessary.
pub fn write_file<P: AsRef<Path>>(path: P, content: &str) -> Result<()> {
    let path = path.as_ref();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .with_context(|| format!("Failed to create directory: {}", parent.display()))?;
    }
    fs::write(path, content)
        .with_context(|| format!("Failed to write file: {}", path.display()))?;
    Ok(())
}

/// Capitalize the first letter of a string.
pub fn capitalize(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        None => String::new(),
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
    }
}

/// Return the snippet used when policy checks fail.
///
/// Generated sources insert this string to centralize how
/// unauthorized access should be handled at runtime.
pub fn handle_unauthorized_snippet() -> &'static str {
    "crate::handle_unauthorized();"
}
