use anyhow::Result;
use std::fs;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::Path;

use ferrum_shared_models::FerrumDsl;

use super::Plugin;

/// Stub plugin for Sanity CMS integration.
pub struct CmsSanityPlugin;

impl Plugin for CmsSanityPlugin {
    fn name(&self) -> &'static str {
        "cms-sanity"
    }

    fn on_init(&self) -> Result<()> {
        ensure_env()?;
        ensure_dependencies()
    }

    fn on_compile(&self) -> Result<()> {
        ensure_env()?;
        ensure_dependencies()
    }

    fn extend_dsl(&self, dsl: &mut FerrumDsl) -> Result<()> {
        if !dsl.app.features.contains(&"cms-sanity".to_string()) {
            dsl.app.features.push("cms-sanity".to_string());
        }
        if !dsl.resources.iter().any(|r| r.name == "SanityClient") {
            use std::collections::BTreeMap;
            let mut config = BTreeMap::new();
            config.insert("project_id".to_string(), "".to_string());
            config.insert("dataset".to_string(), "production".to_string());
            dsl.resources.push(ferrum_shared_models::DslResource {
                name: "SanityClient".to_string(),
                resource_type: "cms-sanity".to_string(),
                config,
            });
        }
        Ok(())
    }
}

fn ensure_env() -> Result<()> {
    let path = Path::new(".env");
    if !path.exists() {
        fs::write(path, "SANITY_PROJECT_ID=\nSANITY_TOKEN=\n")?;
    }
    Ok(())
}

fn ensure_dependencies() -> Result<()> {
    ensure_dep("sanity", "0.1")
}

fn ensure_dep(dep: &str, version: &str) -> Result<()> {
    let path = Path::new("backend/Cargo.toml");
    if !path.exists() {
        return Ok(());
    }
    let contents = fs::read_to_string(path)?;
    if !contents.contains(dep) {
        let mut f = OpenOptions::new().append(true).open(path)?;
        writeln!(f, "{dep} = \"{version}\"")?;
    }
    Ok(())
}
