use anyhow::Result;
use std::fs;

use ferrum_shared_models::{DslResource, FerrumDsl};

use crate::querygen::ProjectPaths;

pub fn generate_resource(res: &DslResource, paths: &ProjectPaths) -> Result<()> {
    let dir = paths.backend.join("resources");
    fs::create_dir_all(&dir)?;
    let content = format!(
        "// Resource type: {}\n// Configuration: {:?}\n",
        res.resource_type, res.config
    );
    fs::write(dir.join(format!("{}.rs", res.name.to_lowercase())), content)?;
    Ok(())
}

pub fn compile_resources(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    for r in &dsl.resources {
        generate_resource(r, paths)?;
    }
    Ok(())
}
