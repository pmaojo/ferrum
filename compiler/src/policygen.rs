use anyhow::Result;
use inflector::Inflector;
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

    let hook_dir = paths.frontend.join("hooks");
    fs::create_dir_all(&hook_dir)?;
    let hook_name = format!("use{}", policy.name.to_pascal_case());
    let ts_content = format!(
        "import {{ useEffect, useState }} from 'react';\n\nexport function {hook_name}() {{\n  const [allowed, setAllowed] = useState(false);\n  useEffect(() => {{\n    fetch('/api/policies/{orig}')\n      .then(res => res.json())\n      .then(setAllowed)\n      .catch(() => setAllowed(false));\n  }}, []);\n  return allowed;\n}}\n",
        hook_name = hook_name,
        orig = policy.name
    );
    fs::write(hook_dir.join(format!("{hook_name}.ts")), ts_content)?;
    Ok(())
}

pub fn compile_policies(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    for p in &dsl.policies {
        generate_policy(p, paths)?;
    }
    Ok(())
}
