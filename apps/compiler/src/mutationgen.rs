use anyhow::Result;
use inflector::Inflector;
use std::fs;

use ferrum_shared_models::DslMutation;
use ferrum_shared_models::FerrumDsl;

use crate::{utils::handle_unauthorized_snippet, ProjectPaths};

/// Generate source files for a DSL mutation entry.
pub fn generate_mutation(mutation: &DslMutation, paths: &ProjectPaths) -> Result<()> {
    let func_name = mutation.name.to_snake_case();
    let hook_name = mutation.name.to_pascal_case();
    let backend_dir = paths.backend.join("mutations");
    let frontend_dir = paths.frontend.join("hooks");
    fs::create_dir_all(&backend_dir)?;
    fs::create_dir_all(&frontend_dir)?;

    let mut imports = String::new();
    for ent in &mutation.entities {
        imports.push_str(&format!(
            "use crate::domain::{}::{};\n",
            ent.to_snake_case(),
            ent
        ));
    }
    let ret_ty = mutation
        .entities
        .first()
        .cloned()
        .unwrap_or_else(|| "serde_json::Value".into());
    let policy_check = mutation
        .policy
        .as_ref()
        .map(|p| {
            format!(
                "    if !crate::policies::evaluate_policy(\"{p}\") {{\n        {}\n    }}\n",
                handle_unauthorized_snippet(),
                p = p
            )
        })
        .unwrap_or_default();

    let rust_content = format!(
        "{imports}use axum::{{Json, extract::State}};\nuse std::sync::Arc;\nuse crate::AppState;\n\npub async fn {func_name}(State(_state): State<Arc<AppState>>, Json(_input): Json<{ret_ty}>) -> Json<{ret_ty}> {{\n{policy_check}    // ⛳️ AI_FILL[mutation_logic] --context=mutation:{orig}\n    Json(_input)\n}}\n",
        imports = imports,
        func_name = func_name,
        ret_ty = ret_ty,
        policy_check = policy_check,
        orig = mutation.name,
    );
    fs::write(backend_dir.join(format!("{}.rs", func_name)), rust_content)?;

    let ts_import = mutation
        .entities
        .first()
        .map(|e| format!("import {{ {e} }} from '../types';\n"))
        .unwrap_or_default();
    let ts_ret = mutation
        .entities
        .first()
        .cloned()
        .unwrap_or_else(|| "any".into());
    let auth_line = if mutation.auth_required {
        "const token = localStorage.getItem('token');\n    const headers: any = token ? { 'Authorization': `Bearer ${token}` } : {};\n".to_string()
    } else {
        "const headers: Record<string, string> = {};\n".to_string()
    };
    let ts_content = format!(
        "import {{ useState }} from 'react';\n{ts_import}export function use{hook_name}() {{\n  const [loading, setLoading] = useState(false);\n  const [error, setError] = useState<Error | null>(null);\n\n  const mutate = async (input: {ts_ret}) => {{\n    setLoading(true);\n    setError(null);\n    try {{\n{auth_line}      const res = await fetch('/api/mutations/{orig}', {{\n        method: 'POST',\n        headers: {{ 'Content-Type': 'application/json', ...headers }},\n        body: JSON.stringify(input),\n      }});\n      if (!res.ok) throw new Error(`Mutation failed: ${{res.status}}`);\n      return await res.json() as Promise<{ts_ret}>;\n    }} catch (err) {{\n      const nextError = err instanceof Error ? err : new Error('Mutation failed');\n      setError(nextError);\n      throw nextError;\n    }} finally {{\n      setLoading(false);\n    }}\n  }};\n\n  return {{ mutate, loading, error }};\n}}\n",
        ts_import = ts_import,
        hook_name = hook_name,
        ts_ret = ts_ret,
        auth_line = auth_line,
        orig = mutation.name
    );
    fs::write(frontend_dir.join(format!("use{hook_name}.ts")), ts_content)?;

    Ok(())
}

/// Compile mutations from the DSL into source files.
pub fn compile_mutations(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    for m in &dsl.mutations {
        generate_mutation(m, paths)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    use std::fs;

    #[test]
    fn generate_mutation_creates_files() {
        let dir = tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        let mutation = DslMutation {
            name: "createUser".into(),
            handler: "./backend/mutations/create_user.rs".into(),
            entities: vec!["User".into()],
            auth_required: true,
            policy: None,
        };
        generate_mutation(&mutation, &paths).unwrap();
        assert!(dir.path().join("backend/mutations/create_user.rs").exists());
        let hook = fs::read_to_string(dir.path().join("frontend/hooks/useCreateUser.ts")).unwrap();
        assert!(hook.contains("const mutate = async"));
        assert!(hook.contains("return { mutate, loading, error }"));
    }

    #[test]
    fn policy_check_uses_helper() {
        let dir = tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        let mutation = DslMutation {
            name: "createAdmin".into(),
            handler: "./backend/mutations/create_admin.rs".into(),
            entities: vec!["User".into()],
            auth_required: false,
            policy: Some("AdminOnly".into()),
        };
        generate_mutation(&mutation, &paths).unwrap();
        let content = fs::read_to_string(dir.path().join("backend/mutations/create_admin.rs")).unwrap();
        assert!(content.contains("handle_unauthorized()"));
    }
}
