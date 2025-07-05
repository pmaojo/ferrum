use anyhow::{Context, Result};
use inflector::Inflector;
use std::fs;

use ferrum_shared_models::{DslPolicy, FerrumDsl};

use crate::ProjectPaths;

pub fn generate_policy(policy: &DslPolicy, paths: &ProjectPaths) -> Result<()> {
    let dir = paths.backend.join("policies");
    fs::create_dir_all(&dir)?;
    let func = policy.name.to_snake_case();
    let content = if let Some(role) = policy.guard.strip_prefix("role:") {
        format!(
            "// Guard: role {role}\n\npub fn {func}() -> bool {{\n    super::current_roles().iter().any(|r| r == \"{role}\")\n}}\n",
            role = role.trim(),
            func = func
        )
    } else {
        format!(
            "// Guard: {guard}\n\npub fn {func}() -> bool {{\n    super::{guard}()\n}}\n",
            guard = policy.guard,
            func = func
        )
    };
    fs::write(
        dir.join(format!("{}.rs", policy.name.to_lowercase())),
        content,
    )?;

    let hook_dir = paths.frontend.join("hooks");
    fs::create_dir_all(&hook_dir)?;
    let hook_name = format!("use{}", policy.name.to_pascal_case());
    let ts_content = if let Some(role) = policy.guard.strip_prefix("role:") {
        format!(
            "import {{ useCurrentUserRoles }} from '../hooks/useCurrentUserRoles';\n\nexport function {hook_name}() {{\n  return useCurrentUserRoles().includes('{role}');\n}}\n",
            hook_name = hook_name,
            role = role.trim()
        )
    } else {
        format!(
            "import {{ useEffect, useState }} from 'react';\n\nexport function {hook_name}() {{\n  const [allowed, setAllowed] = useState(false);\n  useEffect(() => {{\n    fetch('/api/policies/{orig}')\n      .then(res => res.json())\n      .then(setAllowed)\n      .catch(() => setAllowed(false));\n  }}, []);\n  return allowed;\n}}\n",
            hook_name = hook_name,
            orig = policy.name
        )
    };
    fs::write(hook_dir.join(format!("{hook_name}.ts")), ts_content)?;
    Ok(())
}

fn generate_policy_hook(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    if dsl.policies.is_empty() {
        return Ok(());
    }
    let hook_dir = paths.frontend.join("hooks");
    fs::create_dir_all(&hook_dir)?;
    let mut imports = String::new();
    let mut cases = String::new();
    for p in &dsl.policies {
        let hook_name = format!("use{}", p.name.to_pascal_case());
        imports.push_str(&format!("import {{ {hook_name} }} from './{hook_name}';\n"));
        cases.push_str(&format!(
            "        case '{name}': return {hook_name}();\n",
            name = p.name,
            hook_name = hook_name
        ));
    }
    let ts_content = format!(
        "{imports}\nexport function usePolicy(expr: string) {{\n  const parts = expr.split('&&').map(p => p.trim());\n  return parts.every(p => {{\n    switch(p) {{\n{cases}        default:\n            return false;\n    }}\n  }});\n}}\n",
        imports = imports,
        cases = cases
    );
    fs::write(hook_dir.join("usePolicy.ts"), ts_content)?;
    Ok(())
}

fn generate_policy_mod(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    if dsl.policies.is_empty() {
        return Ok(());
    }
    let dir = paths.backend.join("policies");
    fs::create_dir_all(&dir)?;
    let mut content = String::from(
        "use std::cell::RefCell;\nuse base64::{engine::general_purpose::STANDARD, Engine as _};\nuse serde::Deserialize;\nuse serde_json;\n\nthread_local! {\n    static REQUEST_ROLES: RefCell<Vec<String>> = RefCell::new(Vec::new());\n}\n\n#[derive(Deserialize)]\nstruct Claims { roles: Vec<String> }\n\n/// Extract roles from a `Cookie` header and store them for policy evaluation.\npub fn set_request_context(header: &str) {\n    let roles = header.split(';').find_map(|p| p.trim().strip_prefix(\"jwt=\"))\n        .and_then(|jwt| {\n            let payload = jwt.split('.').nth(1)?;\n            let decoded = STANDARD.decode(payload).ok()?;\n            let json = std::str::from_utf8(&decoded).ok()?;\n            serde_json::from_str::<Claims>(json).ok().map(|c| c.roles)\n        }).unwrap_or_default();\n    REQUEST_ROLES.with(|r| *r.borrow_mut() = roles);\n}\n\n/// Return roles previously extracted with `set_request_context`.\npub fn current_roles() -> Vec<String> {\n    REQUEST_ROLES.with(|r| r.borrow().clone())\n}\n"
    );
    for p in &dsl.policies {
        let mod_name = p.name.to_lowercase();
        let func_name = p.name.to_snake_case();
        content.push_str(&format!("mod {mod_name};\n"));
        content.push_str(&format!("pub use {mod_name}::{func_name};\n"));
    }
    content.push_str("\npub fn evaluate_policy(expr: &str) -> bool {\n    expr.split(\"&&\").map(|p| p.trim()).all(|p| match p {\n");
    for p in &dsl.policies {
        let func_name = p.name.to_snake_case();
        content.push_str(&format!(
            "        \"{name}\" => {func_name}(),\n",
            name = p.name,
            func_name = func_name
        ));
    }
    content.push_str("        _ => false,\n    })\n}\n");
    fs::write(dir.join("mod.rs"), content)?;
    Ok(())
}

fn generate_policy_docs(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    if dsl.policies.is_empty() {
        return Ok(());
    }
    let dir = paths.root.join("docs");
    fs::create_dir_all(&dir)?;
    let mut md = String::from("# Policies\n\n");
    for p in &dsl.policies {
        md.push_str(&format!("* **{}** - guard: `{}`\n", p.name, p.guard));
    }
    fs::write(dir.join("policies.md"), md).context("write policies docs")?;
    Ok(())
}

fn generate_policy_layout(paths: &ProjectPaths) -> Result<()> {
    let comp_dir = paths.frontend.join("components");
    fs::create_dir_all(&comp_dir)?;
    let content = "import React from 'react';\nimport { usePolicy } from '../hooks/usePolicy';\n\ninterface Props { policy?: string; children: React.ReactNode; }\nexport const PolicyGate: React.FC<Props> = ({ policy, children }) => {\n  const allowed = policy ? usePolicy(policy) : true;\n  if (!allowed) return null;\n  return <>{children}</>;\n};\n";
    fs::write(comp_dir.join("PolicyGate.tsx"), content)?;
    Ok(())
}

fn generate_policy_admin(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    if dsl.policies.is_empty() {
        return Ok(());
    }
    let comp_dir = paths.frontend.join("components");
    fs::create_dir_all(&comp_dir)?;
    let mut entries = String::new();
    for p in &dsl.policies {
        entries.push_str(&format!(
            "        <li key=\"{name}\">{name} - guard: {guard}</li>\n",
            name = p.name,
            guard = p.guard
        ));
    }
    let content = format!("import React from 'react';\n\nexport const PoliciesAdmin: React.FC = () => (\n  <div>\n    <h2>Policies</h2>\n    <ul>\n{entries}    </ul>\n  </div>\n);\n", entries=entries);
    fs::write(comp_dir.join("PoliciesAdmin.tsx"), content)?;
    Ok(())
}

pub fn compile_policies(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    for p in &dsl.policies {
        generate_policy(p, paths)?;
    }
    generate_policy_mod(dsl, paths)?;
    generate_policy_hook(dsl, paths)?;
    generate_policy_docs(dsl, paths)?;
    generate_policy_layout(paths)?;
    generate_policy_admin(dsl, paths)?;
    Ok(())
}
