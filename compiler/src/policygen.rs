use anyhow::Result;
use std::fs;

use ferrum_shared_models::{DslPolicy, FerrumDsl};

use crate::querygen::ProjectPaths;

pub fn generate_policy(policy: &DslPolicy, paths: &ProjectPaths) -> Result<()> {
    let dir = paths.backend.join("policies");
    fs::create_dir_all(&dir)?;
    let content = format!(
        "// Guard: {}\n\npub fn {}() -> bool {{\n    // TODO implement\n    true\n}}\n",
        policy.guard, policy.name
    );
    fs::write(
        dir.join(format!("{}.rs", policy.name.to_lowercase())),
        content,
    )?;
    Ok(())
}

pub fn compile_policies(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    for p in &dsl.policies {
        generate_policy(p, paths)?;
    }
    Ok(())
}
